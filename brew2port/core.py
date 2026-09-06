import csv, json, re, subprocess, difflib, urllib.request
from urllib.parse import urljoin
from pathlib import Path
import shutil

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

def make_plan(items,ports,overrides=None):
    return [{'kind':i['kind'],'homebrew':i['name'],'candidates':candidates(i,ports,overrides)} for i in items]

def install(plan, yes=False, run=subprocess.run, log=None):
    results=[]
    for row in plan:
        cs=row['candidates']; chosen=cs[0] if cs and cs[0]['confidence']>=.8 and (len(cs)==1 or cs[0]['confidence']-cs[1]['confidence']>=.08) else None
        if not chosen: results.append({**row,'status':'needs-review'}); continue
        cmd=['sudo','port','install',chosen['port']]
        if not yes: results.append({**row,'status':'dry-run','command':cmd}); continue
        r=run(cmd); results.append({**row,'status':'installed' if r.returncode==0 else 'failed','command':cmd})
    return results

def verify_plan(plan, run=subprocess.run):
    out=[]
    for row in plan:
        port=row.get('port') or (row.get('candidates') or [{}])[0].get('port')
        if not port: out.append({'homebrew':row['homebrew'],'port':None,'verified':False,'reason':'no mapping'}); continue
        r=run(['port','installed',port],capture_output=True,text=True)
        out.append({'homebrew':row['homebrew'],'port':port,'verified':r.returncode==0 and port in r.stdout})
    return out
