import argparse,json,urllib.request,logging
from .core import *
from .macports import setup_macports
def main():
 p=argparse.ArgumentParser(prog='brew2port'); s=p.add_subparsers(dest='cmd')
 a=s.add_parser('inventory'); a.add_argument('-o','--output');
 a=s.add_parser('build-index'); a.add_argument('-o','--output',required=True); a.add_argument('--url',default='https://ports.macports.org/api/v1/ports/')
 a=s.add_parser('setup-macports'); a.add_argument('--version'); a.add_argument('--dry-run',action='store_true'); a.add_argument('--skip-update',action='store_true'); a.add_argument('--yes',action='store_true')
 a=s.add_parser('plan'); a.add_argument('--inventory',required=True); a.add_argument('--ports'); a.add_argument('--ports-url',default='https://ports.macports.org/api/v1/ports/'); a.add_argument('--cache',default='~/.cache/brew2port/macports-ports.json'); a.add_argument('--refresh-ports',action='store_true'); a.add_argument('--overrides'); a.add_argument('-o','--output'); a.add_argument('--format',choices=['json','text'],default='json')
 a=s.add_parser('migrate'); a.add_argument('--plan',required=True); a.add_argument('--install',action='store_true'); a.add_argument('--yes',action='store_true'); a.add_argument('-o','--output')
 a=s.add_parser('verify'); a.add_argument('--plan',required=True)
 x=p.parse_args()
 if x.cmd is None:
  print("""brew2port — Homebrew to MacPorts migration assistant

Safe workflow:

  1. Inventory explicitly installed Homebrew packages:
       brew2port inventory --output brew-inventory.json

  2. brew2port downloads and caches the current MacPorts catalog automatically.
     Use --ports FILE with plan for an offline/local snapshot.

  3. If MacPorts is not installed, bootstrap it explicitly:
       brew2port setup-macports

  4. Generate and review a migration plan:
       brew2port plan --inventory brew-inventory.json \\
         --overrides overrides.json \\
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
  items=json.load(open(x.inventory)); ov=json.load(open(x.overrides)) if x.overrides else {}; ports=load_ports(x.ports) if x.ports else cached_macports_ports(x.cache,x.refresh_ports,x.ports_url); data=make_plan(items,ports,ov); out=json.dumps(data,indent=2) if x.format=='json' else '\n'.join(f"{r['homebrew']} -> "+(', '.join(f"{c['port']} ({c['confidence']})" for c in r['candidates']) or 'NO MATCH') for r in data)
 elif x.cmd=='migrate':
  data=install(json.load(open(x.plan)),x.yes if x.install else False); out=json.dumps(data,indent=2)
  if not x.install: out += "\n\nDry run complete. No packages were changed.\n\nTo perform the reviewed installation:\n  brew2port migrate --plan " + x.plan + " --install\n"
 else:
  data=json.load(open(x.plan)); out=json.dumps(verify_plan(data),indent=2)
 if getattr(x,'output',None): open(x.output,'w').write(out+'\n')
 else: print(out)
