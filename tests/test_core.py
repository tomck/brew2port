import json,tempfile,unittest
from brew2port.core import *
from brew2port.macports import select_asset
class TestCore(unittest.TestCase):
 def test_normalized_and_override(self):
  ports=[{'name':'muse_code'},{'name':'wget'}]
  self.assertEqual(candidates({'name':'muse-code','kind':'formula'},ports)[0]['port'],'muse_code')
  self.assertEqual(candidates({'name':'foo','kind':'formula'},ports,{'foo':None}),[])
 def test_plan(self): self.assertEqual(make_plan([{'name':'wget','kind':'formula'}],[{'name':'wget'}])[0]['candidates'][0]['confidence'],1.0)
 def test_install_defaults_to_dry_run(self):
  result=install([{'homebrew':'wget','candidates':[{'port':'wget','confidence':1.0}]}]); self.assertEqual(result[0]['status'],'dry-run')
 def test_load_json(self):
  with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
   json.dump([{'name':'x'}],f); f.flush(); self.assertEqual(load_ports(f.name)[0]['name'],'x')
 def test_fetch_paginated_api(self):
  class Response:
   def __init__(self,data): self.data=json.dumps(data).encode()
   def __enter__(self): return self
   def __exit__(self,*args): pass
   def read(self): return self.data
  pages=[Response({'results':[{'name':'wget'}],'next':'page2'}),Response({'results':[{'name':'muse_code'}],'next':None})]
  def opener(request): return pages.pop(0)
  self.assertEqual([p['name'] for p in fetch_macports_ports(opener=opener)],['wget','muse_code'])
 def test_select_macos_asset(self):
  asset=select_asset(('15.7',15,'x86_64'),[{'name':'MacPorts-2.12.3-15-Sequoia.pkg'}])
  self.assertEqual(asset['name'],'MacPorts-2.12.3-15-Sequoia.pkg')
