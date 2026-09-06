import json,tempfile,unittest
from brew2port.core import *
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
