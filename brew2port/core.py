import csv, json, re, subprocess, difflib, urllib.request, sys
from urllib.parse import urljoin
from pathlib import Path
import shutil
from macpkg_migrate_core import Identity, Candidate, dry_run as shared_dry_run, install_allowed, plan_record
from .macports import target_exists

def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())

def inventory_from_brew(run=subprocess.run):
    p=run(['brew','info','--json=v2','--installed'],capture_output=True,text=True,check=True)
    data=json.loads(p.stdout); out=[]
    for f in data.get('formulae',[]):
        installed=f.get('installed',[]); requested=any(x.get('installed_on_request') for x in installed)
        if requested: out.append({'kind':'formula','name':f.get('name') or f.get('full_name'),'full_name':f.get('full_name')})
    for c in data.get('casks',[]): out.append({'kind':'cask','name':c.get('token') or c.get('name'),'full_name':c.get('full_name')})
    return out

def load_ports(path):
    text=Path(path).read_text();
    try:
        x=json.loads(text); return x if isinstance(x,list) else x.get('ports',[])
    except json.JSONDecodeError: pass
    rows=[]; lines=[x for x in text.splitlines() if x.strip()]
    if lines and ('\t' in lines[0] or ',' in lines[0]):
        dialect=csv.Sniffer().sniff(lines[0]); rows=list(csv.DictReader(lines,dialect=dialect))
    else:
        for line in lines:
            name=line.split()[0]; rows.append({'name':name,'description':line[len(name):].strip()})
    return rows

def fetch_macports_ports(url='https://ports.macports.org/api/v1/ports/', opener=urllib.request.urlopen, progress=None):
    """Fetch the public MacPorts port catalog, following API pagination."""
    rows=[]; next_url=url; pages=0
    while next_url:
        pages += 1
        if pages > 5000: raise RuntimeError('MacPorts API pagination exceeded safety limit')
        if progress: progress(f'Fetching MacPorts catalog page {pages}...')
        request=urllib.request.Request(next_url,headers={'User-Agent':'brew2port/'+__import__('brew2port').__version__})
        with opener(request) as response: payload=json.loads(response.read().decode())
        if isinstance(payload,list): page=payload; next_url=None
        else:
            page=payload.get('results',payload.get('ports',[]))
            next_url=urljoin(next_url,payload.get('next')) if payload.get('next') else None
        for port in page:
            if isinstance(port,dict):
                if isinstance(port.get('port'),dict): port={**port['port'],**port}
                name=port.get('name') or port.get('portname') or port.get('port')
                if name: rows.append({**port,'name':name})
    return rows

def cached_macports_ports(cache_path, refresh=False, url='https://ports.macports.org/api/v1/ports/', progress=None):
    path=Path(cache_path).expanduser()
    if path.exists() and not refresh:
        if progress: progress(f'Using cached MacPorts catalog: {path}')
        return load_ports(path)
    if progress: progress('No usable cached MacPorts catalog found; downloading a fresh copy...')
    rows=fetch_macports_ports(url,progress=progress)
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(rows,indent=2)+'\n')
    if progress: progress(f'Cached {len(rows)} MacPorts ports at {path}')
    return rows

def local_macports_ports(run=subprocess.run):
    """Read port names from MacPorts' already-maintained local PortIndex."""
    port=shutil.which('port') or ('/opt/local/bin/port' if Path('/opt/local/bin/port').exists() else None)
    if not port:
        raise RuntimeError('MacPorts is not installed')
    result=run([port,'-q','echo','all'],capture_output=True,text=True)
    if result.returncode != 0: raise RuntimeError('Unable to read the local MacPorts PortIndex')
    names=[]
    for line in result.stdout.splitlines():
        name=line.strip()
        if name and re.fullmatch(r'[A-Za-z0-9+_.-]+',name): names.append(name)
    if not names: raise RuntimeError('MacPorts returned an empty local PortIndex')
    return [{'name':name} for name in sorted(set(names))]

def update_macports(run=subprocess.run):
    """Refresh MacPorts base and its local ports tree."""
    port=shutil.which('port') or ('/opt/local/bin/port' if Path('/opt/local/bin/port').exists() else None)
    if not port: raise RuntimeError('MacPorts is not installed; run brew2port setup-macports first')
    result=run(['sudo',port,'selfupdate'])
    if result.returncode != 0: raise RuntimeError(f'MacPorts selfupdate failed with exit code {result.returncode}')
    return {'status':'updated','command':['sudo',port,'selfupdate']}

def candidates(item, ports, overrides=None):
    overrides=overrides or {}; name=item['name']
    if name in overrides: return [dict(overrides[name],port=overrides[name].get('port'))] if overrides[name] else []
    scored=[]
    for p in ports:
        pn=p.get('name') or p.get('port'); aliases=' '.join(str(p.get(k,'')) for k in ('aliases','provides','replaces','conflicts'))
        score=0; reason='heuristic'
        if pn==name: score,reason=1.0,'exact name'
        elif norm(pn)==norm(name): score,reason=.96,'normalized name'
        elif norm(name) in [norm(a) for a in re.split(r'[,\s]+',aliases) if a]: score,reason=.92,'alias/provides/replaces'
        else: score=difflib.SequenceMatcher(None,norm(name),norm(pn)).ratio()
        if score>=.55: scored.append({'port':pn,'confidence':round(score,3),'reason':reason})
    return sorted(scored,key=lambda x:x['confidence'],reverse=True)[:5]

def make_plan(items,ports,overrides=None,definitions=None,progress=None):
    definitions=definitions or {}
    rows=[]
    for item in items:
        key=(item['kind'],item['name'])
        use_catalog=key in definitions and (definitions[key].get('candidates') or definitions[key].get('negative_relation'))
        choices=definitions[key]['candidates'] if use_catalog else candidates(item,ports,overrides)
        row={'kind':item['kind'],'source_manager':'homebrew','source_package':item['name'],'target_manager':'macports','homebrew':item['name'],'candidates':choices}
        if key in definitions:
            shared=definitions[key].get('shared_record')
            row['catalog_status']=definitions[key].get('catalog_status','needs-review'); row['catalog_version']=definitions[key].get('catalog_version') or definitions.get('catalog_version')
            if shared:
                row.update({'source':shared['source'],'recommendation':shared['recommendation'],'action':shared['action'],'install_authorized':shared['install_authorized']})
            if definitions[key].get('negative_relation'):
                row['negative_relation']=True
        rows.append(row)
        if progress:
            progress(len(rows),len(items),item['name'])
    return rows

def write_preview_csv(plan, path):
    with open(path,'w',newline='') as output:
        writer=csv.writer(output)
        writer.writerow(['kind','homebrew','recommended_port','confidence','reason','alternatives','review_status'])
        for row in plan:
            choices=row.get('candidates',[])
            recommended=choices[0] if choices else {}
            target=recommended.get('target',{})
            port=recommended.get('port') or target.get('native_name','')
            confidence=recommended.get('confidence','')
            reason=recommended.get('reason') or recommended.get('matching_method','')
            if row.get('recommendation'):
                confident=bool(row.get('install_authorized') and install_allowed(row))
            else:
                confident=bool(choices and choices[0].get('relation_type') not in {'no-equivalent','conflicts'} and choices[0].get('confidence',0)>=.8 and (len(choices)==1 or choices[0].get('confidence',0)-choices[1].get('confidence',0)>=.08))
            alternatives='; '.join(c.get('port') or c.get('target',{}).get('native_name','') for c in choices[1:])
            writer.writerow([row.get('kind',''),row.get('homebrew',''),port,confidence,reason,alternatives,'recommended' if confident else 'needs-review'])

def _candidate_port(candidate):
    return candidate.get('port') or candidate.get('target',{}).get('native_name') or candidate.get('name')

def _catalog_candidate(row):
    recommendation=row.get('recommendation') or {}
    if recommendation and recommendation.get('relation_type') not in {'no-equivalent','conflicts'}:
        return recommendation
    choices=row.get('candidates',[])
    return choices[0] if choices else None

def _eligible(row, mode):
    candidate=_catalog_candidate(row)
    if not candidate or candidate.get('relation_type') in {'no-equivalent','conflicts'}: return None
    confidence=float(candidate.get('confidence',0))
    if mode=='automatic':
        return candidate if row.get('catalog_status','automatic')=='automatic' and confidence>=.8 and (len(row.get('candidates',[]))==1 or confidence-float(row['candidates'][1].get('confidence',0))>=.08) else None
    if mode=='trusted':
        evidence=row.get('evidence') or candidate.get('evidence') or []
        methods={'trusted','curated'}
        trusted= candidate.get('matching_method') in methods or any(e.get('kind') in methods for e in evidence if isinstance(e,dict))
        return candidate if confidence==1.0 and trusted else None
    if mode=='near-hit': return candidate if confidence>=.78 and candidate.get('relation_type') else None
    if mode=='exact':
        return candidate if _candidate_port_name(row)==_candidate_port(candidate) else None
    return candidate

def _candidate_port_name(row):
    return row.get('source_package') or row.get('homebrew','')

def _verify_port(port, run):
    result=run(['port','installed',port],capture_output=True,text=True,check=False)
    return result.returncode==0 and port in result.stdout

def install(plan, yes=False, run=subprocess.run, log=None, target_check=target_exists,
            mode='automatic', input_fn=input, unlink=True):
    """Install selected mappings, verify them, and optionally unlink Homebrew.

    Modes are trusted, near-hit, exact, and interactive. Without ``yes`` this
    remains a pure dry run. Homebrew is never uninstalled or overwritten.
    """
    if mode not in {'automatic','trusted','near-hit','exact','interactive'}:
        raise ValueError('mode must be trusted, near-hit, exact, or interactive')
    results=[]; remaining=[]
    for row in plan:
        chosen=_eligible(row,mode) if mode!='interactive' else None
        unlink_choice=unlink
        if mode=='interactive':
            choices=row.get('candidates',[])
            if not choices:
                results.append({**row,'status':'needs-review'}); continue
            print(f"{row['homebrew']}: choose 1=install and unlink, 2=install and keep linked, 3=skip",file=sys.stderr)
            for number,candidate in enumerate(choices,1): print(f"  {number}: {_candidate_port(candidate)} ({candidate.get('confidence','?')})",file=sys.stderr)
            answer=input_fn('Choice [1/2/3, default 1]: ').strip() or '1'
            if answer=='3': results.append({**row,'status':'intentionally-retained'}); continue
            if answer not in {'1','2'}: results.append({**row,'status':'needs-review','reason':'invalid interactive choice'}); continue
            chosen=choices[0]; unlink_choice=answer=='1'
        if not chosen:
            remaining.append(row); results.append({**row,'status':'needs-review'}); continue
        port=_candidate_port(chosen); cmd=['sudo','port','install',port]
        result={**row,'status':'dry-run' if not yes else 'pending','command':cmd}
        if not yes:
            if unlink_choice: result['follow_up']=['port installed '+port,'brew unlink '+row['homebrew']]
            results.append(result); continue
        if not target_check(port,run=run):
            results.append({**result,'status':'target-missing','reason':'MacPorts target is absent from the local PortIndex'}); continue
        installed=run(cmd)
        if installed.returncode != 0:
            results.append({**result,'status':'failed'}); continue
        if not _verify_port(port,run):
            results.append({**result,'status':'verification-failed','reason':'MacPorts did not report the port as installed'}); continue
        if unlink_choice:
            unlinked=run(['brew','unlink',row['homebrew']])
            result['status']='installed-and-unlinked' if unlinked.returncode==0 else 'installed-unlink-failed'
            result['unlink_command']=['brew','unlink',row['homebrew']]
        else: result['status']='installed'
        results.append(result)
    return results

def verify_plan(plan, run=subprocess.run):
    out=[]
    for row in plan:
        recommendation=row.get('recommendation') or {}
        port=row.get('port') or recommendation.get('target',{}).get('native_name') or (row.get('candidates') or [{}])[0].get('port') or (row.get('candidates') or [{}])[0].get('target',{}).get('native_name')
        if not port: out.append({'homebrew':row['homebrew'],'port':None,'verified':False,'reason':'no mapping'}); continue
        r=run(['port','installed',port],capture_output=True,text=True)
        out.append({'homebrew':row['homebrew'],'port':port,'verified':r.returncode==0 and port in r.stdout})
    return out
