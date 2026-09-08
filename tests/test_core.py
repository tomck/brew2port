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
 def test_local_macports_ports(self):
  import brew2port.core as core
  old=core.shutil.which; core.shutil.which=lambda name:'/opt/local/bin/port' if name=='port' else old(name)
  try:
   def run(*args,**kwargs): return type('R',(),{'returncode':0,'stdout':'wget\nfoo-bar\n'})()
   self.assertEqual([p['name'] for p in local_macports_ports(run)],['foo-bar','wget'])
  finally: core.shutil.which=old
 def test_update_macports(self):
  import brew2port.core as core
  old=core.shutil.which; core.shutil.which=lambda name:'/opt/local/bin/port'
  try:
   result=update_macports(lambda *args,**kwargs:type('R',(),{'returncode':0})())
   self.assertEqual(result['status'],'updated')
  finally: core.shutil.which=old
 def test_preview_csv(self):
  with tempfile.NamedTemporaryFile(mode='w+',suffix='.csv') as f:
   write_preview_csv([{'kind':'formula','homebrew':'muse-code','candidates':[{'port':'muse_code','confidence':.96,'reason':'normalized name'}]}],f.name)
   f.seek(0); self.assertIn('muse_code',f.read())

 def test_shared_review_candidate_is_not_installable(self):
  plan=[{'homebrew':'ansible@12','source':{'manager':'homebrew','package_type':'formula','native_name':'ansible@12'},'catalog_version':'catalog-test','candidates':[{'target':{'manager':'macports','package_type':'port','native_name':'py313-ansible'},'relation_type':'equivalent','confidence':.78,'review_status':'needs-review','matching_method':'version-family','evidence':[{'kind':'version-family'}],'source_catalog_versions':{}}],'recommendation':None,'install_authorized':False}]
  result=install(plan,yes=True,run=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('install must not run')))
  self.assertEqual(result[0]['status'],'needs-review')

 def test_install_rejects_missing_local_target(self):
  plan=[{'homebrew':'wget','candidates':[{'port':'wget','confidence':1.0}]}]
  calls=[]
  def run(*args,**kwargs): calls.append(args[0]); return type('R',(),{'returncode':99,'stdout':'','stderr':''})()
  result=install(plan,yes=True,run=run,target_check=lambda port,run: False)
  self.assertEqual(result[0]['status'],'target-missing')
  self.assertEqual(calls,[])

 def test_trusted_install_verifies_before_unlinking(self):
  plan=[{'homebrew':'wget','candidates':[{'port':'wget','relation_type':'equivalent','confidence':1.0,'matching_method':'curated','evidence':[{'kind':'curated'}]}]}]
  calls=[]
  def run(args,**kwargs):
   calls.append(args)
   return type('R',(),{'returncode':0,'stdout':'wget 1.0\n','stderr':''})()
  result=install(plan,yes=True,mode='trusted',run=run,target_check=lambda port,run: True)
  self.assertEqual(result[0]['status'],'installed-and-unlinked')
  self.assertEqual(calls,[['sudo','port','install','wget'],['port','installed','wget'],['brew','unlink','wget']])

 def test_near_hit_mode_allows_version_family_but_exact_mode_does_not(self):
  plan=[{'homebrew':'python@3.14','candidates':[{'target':{'native_name':'python314'},'relation_type':'equivalent','confidence':.78,'matching_method':'version-family'}]}]
  self.assertEqual(install(plan,mode='near-hit')[0]['status'],'dry-run')
  self.assertEqual(install(plan,mode='exact')[0]['status'],'needs-review')

 def test_interactive_choice_two_keeps_homebrew_linked(self):
  plan=[{'homebrew':'wget','candidates':[{'port':'wget','confidence':1.0,'reason':'exact name'}]}]
  calls=[]
  def run(args,**kwargs):
   calls.append(args); return type('R',(),{'returncode':0,'stdout':'wget 1.0\n','stderr':''})()
  result=install(plan,yes=True,mode='interactive',input_fn=lambda prompt:'2',run=run,target_check=lambda port,run: True)
  self.assertEqual(result[0]['status'],'installed')
  self.assertEqual(calls,[['sudo','port','install','wget'],['port','installed','wget']])

 def test_dry_run_has_no_side_effects(self):
  plan=[{'homebrew':'wget','candidates':[{'port':'wget','confidence':1.0,'matching_method':'curated'}]}]
  calls=[]
  result=install(plan,mode='trusted',run=lambda *args,**kwargs: calls.append(args))
  self.assertEqual(result[0]['status'],'dry-run')
  self.assertEqual(calls,[])

 def test_automatic_negative_relation_is_not_installable(self):
  plan=[{'homebrew':'macs-fan-control','recommendation':{'target':{'manager':'macports','package_type':'port','native_name':'qmail-spamcontrol'},'relation_type':'no-equivalent','review_status':'automatic','confidence':1.0},'install_authorized':True,'candidates':[]}]
  result=install(plan,yes=True,run=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('install must not run')))
  self.assertEqual(result[0]['status'],'needs-review')

 def test_make_plan_reports_progress(self):
  updates=[]
  make_plan([{'name':'wget','kind':'formula'}],[{'name':'wget'}],progress=lambda n,total,name: updates.append((n,total,name)))
  self.assertEqual(updates,[(1,1,'wget')])

 def test_negative_catalog_relation_blocks_fallback_matching(self):
  definitions={('cask','macs-fan-control'):{'candidates':[],'negative_relation':True,'catalog_status':'no-equivalent','catalog_version':'catalog-test','shared_record':{'source':{'manager':'homebrew','package_type':'cask','native_name':'macs-fan-control'},'recommendation':None,'action':'review','install_authorized':False}}}
  result=make_plan([{'kind':'cask','name':'macs-fan-control'}],[{'name':'qmail-spamcontrol'}],definitions=definitions)
  self.assertEqual(result[0]['candidates'],[])
  self.assertEqual(result[0]['catalog_status'],'no-equivalent')
