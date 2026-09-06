import argparse,json,urllib.request,logging
from .core import *
def main():
 p=argparse.ArgumentParser(prog='brew2port'); s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('inventory'); a.add_argument('-o','--output');
 a=s.add_parser('build-index'); a.add_argument('-o','--output',required=True); a.add_argument('--formula-url',default='https://formulae.brew.sh/api/formula.json'); a.add_argument('--cask-url',default='https://formulae.brew.sh/api/cask.json')
 a=s.add_parser('plan'); a.add_argument('--inventory',required=True); a.add_argument('--ports',required=True); a.add_argument('--overrides'); a.add_argument('-o','--output'); a.add_argument('--format',choices=['json','text'],default='json')
 a=s.add_parser('migrate'); a.add_argument('--plan',required=True); a.add_argument('--install',action='store_true'); a.add_argument('--yes',action='store_true'); a.add_argument('-o','--output')
 a=s.add_parser('verify'); a.add_argument('--plan',required=True)
 x=p.parse_args()
 if x.cmd=='inventory': data=inventory_from_brew(); out=json.dumps(data,indent=2)
 elif x.cmd=='build-index':
  def get(url): return json.load(urllib.request.urlopen(url))
  data={'homebrew_formulae':get(x.formula_url),'homebrew_casks':get(x.cask_url)}; out=json.dumps(data,indent=2)
 elif x.cmd=='plan':
  items=json.load(open(x.inventory)); ov=json.load(open(x.overrides)) if x.overrides else {}; data=make_plan(items,load_ports(x.ports),ov); out=json.dumps(data,indent=2) if x.format=='json' else '\n'.join(f"{r['homebrew']} -> "+(', '.join(f"{c['port']} ({c['confidence']})" for c in r['candidates']) or 'NO MATCH') for r in data)
 elif x.cmd=='migrate': data=install(json.load(open(x.plan)),x.yes if x.install else False); out=json.dumps(data,indent=2)
 else:
  data=json.load(open(x.plan)); out=json.dumps(verify_plan(data),indent=2)
 if getattr(x,'output',None): open(x.output,'w').write(out+'\n')
 else: print(out)
