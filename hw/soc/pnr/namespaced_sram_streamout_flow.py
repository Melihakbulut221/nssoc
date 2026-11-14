# SPDX-License-Identifier: Apache-2.0
"""Stream exact prior routed DEF with proven namespaced SRAM GDS only."""
import hashlib,json
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import KLayout
ROOT=Path(__file__).resolve().parents[3]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
class GuardedNamespacedStreamOut(KLayout.StreamOut):
 id='NSSOC.NamespacedSRAMStreamOut'
 def run(self,state_in,**kwargs):
  proof=json.loads((ROOT/'hw/soc/out/namespaced-streamout/preflight.json').read_text())
  for path,row in proof['input_views'].items():assert sha(path)==row['sha256']
  for top,row in proof['macro_gds_changes'].items():
   actual=list(map(str,self.config['MACROS'][top].gds));assert actual==row['replacement_gds'] and sha(actual[0])==row['replacement_sha256']
  views,metrics=super().run(state_in,**kwargs)
  assert views,'Streamout skipped unexpectedly'
  for path,row in proof['input_views'].items():assert sha(path)==row['sha256'],'Original route view changed'
  outputs={str(k):{'path':str(p),'sha256':sha(p),'bytes':Path(p).stat().st_size} for k,p in views.items()}
  (ROOT/'hw/soc/out/namespaced-streamout/result.json').write_text(json.dumps({'status':'STREAMOUT_COMPLETE_INPUT_VIEWS_UNCHANGED','outputs':outputs,'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':proof['scope']},indent=2))
  return views,metrics
@Flow.factory.register()
class NamespacedSRAMStreamOut(Interfaces):
 Steps=[GuardedNamespacedStreamOut]
 gating_config_vars={}
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
