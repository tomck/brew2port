import argparse,json,urllib.request,logging,sys,subprocess,shutil
from .core import *
from .macports import setup_macports
def main():
 p=argparse.ArgumentParser(prog='brew2port'); s=p.add_subparsers(dest='cmd')
 a=s.add_parser('inventory'); a.add_argument('-o','--output');
 a=s.add_parser('build-index'); a.add_argument('-o','--output',required=True); a.add_argument('--url',default='https://ports.macports.org/api/v1/ports/')
 a=s.add_parser('setup-macports'); a.add_argument('--version'); a.add_argument('--dry-run',action='store_true'); a.add_argument('--skip-update',action='store_true'); a.add_argument('--yes',action='store_true')
 a=s.add_parser('plan'); a.add_argument('--inventory',required=True); a.add_argument('--ports'); a.add_argument('--ports-url',default='https://ports.macports.org/api/v1/ports/'); a.add_argument('--cache',default='~/.cache/brew2port/macports-ports.json'); a.add_argument('--refresh-ports',action='store_true'); a.add_argument('--update-macports',action='store_true'); a.add_argument('--overrides'); a.add_argument('-o','--output'); a.add_argument('--format',choices=['json','text'],default='json')
 a=s.add_parser('migrate'); a.add_argument('--plan',required=True); a.add_argument('--install',action='store_true'); a.add_argument('--yes',action='store_true'); a.add_argument('-o','--output')
 a=s.add_parser('verify'); a.add_argument('--plan',required=True)
 x=p.parse_args()
 if x.cmd is None:
  print("""brew2port — Homebrew to MacPorts migration assistant

Safe workflow:

  1. Inventory explicitly installed Homebrew packages:
       brew2port inventory --output brew-inventory.json

  2. brew2port uses MacPorts' local PortIndex automatically when `port` is installed.
     Otherwise it downloads and caches the public catalog.
     Use --update-macports to refresh the local PortIndex first, or --ports FILE
     with plan for an offline/local snapshot.

  3. If MacPorts is not installed, bootstrap it explicitly:
       brew2port setup-macports

  4. Generate and review a migration plan:
       brew2port plan --inventory brew-inventory.json \\
         --output migration-plan.json

  5. Preview the migration (dry run):
       brew2port migrate --plan migration-plan.json

  6. Install only after reviewing the preview:
       brew2port migrate --plan migration-plan.json --install

Homebrew packages are never removed automatically.
""")
  return
 if x.cmd=='inventory': data=inventory_from_brew(); out=json.dumps(data,indent=2)
 elif x.cmd=='build-index':
  data=fetch_macports_ports(x.url); out=json.dumps(data,indent=2)
 elif x.cmd=='setup-macports':
  data=setup_macports(x.version,x.dry_run,x.skip_update,x.yes); out=json.dumps(data,indent=2)
 elif x.cmd=='plan':
  print('Loading Homebrew inventory...',file=sys.stderr)
  items=json.load(open(x.inventory))
  if x.overrides:
   try: ov=json.load(open(x.overrides))
   except FileNotFoundError: p.error(f"overrides file not found: {x.overrides} (omit --overrides or use an absolute path)")
  else: ov={}
  if x.ports:
   print(f'Loading local MacPorts catalog: {x.ports}',file=sys.stderr); ports=load_ports(x.ports)
  elif shutil.which('port'):
   if x.update_macports:
    print('Updating the local MacPorts PortIndex with port selfupdate...',file=sys.stderr)
    subprocess.run(['sudo','port','selfupdate'],check=True)
   else:
    print("Using MacPorts' local PortIndex (use --update-macports to refresh it).",file=sys.stderr)
   ports=local_macports_ports()
  else:
   ports=cached_macports_ports(x.cache,x.refresh_ports,x.ports_url,progress=lambda message: print(message,file=sys.stderr))
  print(f'Matching {len(items)} Homebrew packages against {len(ports)} MacPorts ports...',file=sys.stderr)
  data=make_plan(items,ports,ov)
  print(f'Generated migration plan for {len(data)} packages.',file=sys.stderr)
  out=json.dumps(data,indent=2) if x.format=='json' else '\n'.join(f"{r['homebrew']} -> "+(', '.join(f"{c['port']} ({c['confidence']})" for c in r['candidates']) or 'NO MATCH') for r in data)
 elif x.cmd=='migrate':
  data=install(json.load(open(x.plan)),x.yes if x.install else False); out=json.dumps(data,indent=2)
  if not x.install: out += "\n\nDry run complete. No packages were changed.\n\nTo perform the reviewed installation:\n  brew2port migrate --plan " + x.plan + " --install\n"
 else:
  data=json.load(open(x.plan)); out=json.dumps(verify_plan(data),indent=2)
 if getattr(x,'output',None): open(x.output,'w').write(out+'\n')
 else: print(out)
