import os,json,hashlib,collections
from cloud_core_only_postgrt import ROOT,completed,archive,sha
OUT=ROOT/'hw/soc/out/core-only-electrical-classification'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 run=completed(44453782430,'6a3f7a4e8979032e9a8ea1d86393f6dbdb1d6d8a');assert run['run_attempt']==1
 z,m=archive(run,'core-only-combined-electrical-inventory-44453782430');assert m['id']==14497116804 and m['digest']=='sha256:4c5112a9c9b6c0c740993861872e923c42b224f7b70e115103f1bdda1f386681'
 r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha']and r['sources_unchanged']
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 x=json.loads(z.read('inventory.json'));assert x['source_odb_sha256']=='81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee'and x['source_unchanged']and x['unique_nets']==353
 summary=collections.Counter();plans={}
 for name,v in x['nets'].items():
  for t in v['terms']:t['antenna']=t['master']=='sg13g2_antennanp'
  v['antenna_loads']=sum(t['antenna']and t['direction']=='INPUT'for t in v['terms']);v['functional_input_loads']=v['input_loads']-v['antenna_loads']
  kinds={t['kind']for t in v['violations']};actions=[]
  if 'max fanout'in kinds:
   summary['fanout_nets']+=1;summary['functional_fanout_over8']+=v['functional_input_loads']>8;summary['only_with_diodes_over8']+=v['functional_input_loads']<=8;summary['clock_fanout_nets']+=v['type']=='CLOCK';actions.append('Review antenna-aware branching or fewer qualified diode placements; do not waive fanout or remove protection without routed antenna proof.')
  if 'max slew'in kinds:summary['slew_nets']+=1;actions.append('Check upstream slew and wire load; use function-equivalent driver sizing or load isolation, then re-extract.')
  if 'max capacitance'in kinds:
   summary['cap_nets']+=1
   if any(t['master'].startswith('RM_')for t in v['drivers']):summary['sram_cap_nets']+=1;actions.append('Short local macro-output stub plus nearby buffer; keep SRAM max-cap bound and validate full timing.')
  plans[name]=actions
 assert dict(summary)==dict(slew_nets=100,fanout_nets=210,functional_fanout_over8=0,only_with_diodes_over8=210,clock_fanout_nets=2,cap_nets=60,sram_cap_nets=9),summary
 assert sum(v['antenna_loads']for v in x['nets'].values())==837
 x['classification_corrected_from_native_master']='sg13g2_antennanp';x['summary']=dict(summary);x['repair_considerations']=plans
 (OUT/'inventory.json').write_text(json.dumps(x,indent=2)+'\n')
 result=dict(source_head=os.environ['GITHUB_SHA'],source_artifact=m,accepted=False,summary=dict(summary),scope='Exact native connectivity reused; correct earlier diode-name classification. No new ODB mutation, routing, timing, constraint waiver or production approval.',outputs={'inventory.json':sha(OUT/'inventory.json')})
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
