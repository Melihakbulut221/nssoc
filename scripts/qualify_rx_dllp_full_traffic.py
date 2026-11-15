"""Existing eight-seed traffic/reference tests plus semantic ready mutation."""
import pathlib,subprocess,json,hashlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=pathlib.Path('out-traffic');out.mkdir(exist_ok=True)
rtl=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v');source=rtl.read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
needle='output_index==dllp_last_compare'
assert source.count(needle)==1
result={'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'signoff':False,'cases':[]}
try:
 for fault in [False,True]:
  name='mutant'if fault else'positive';dest=out/name
  rtl.write_text(source.replace(needle,'output_index!=dllp_last_compare')if fault else source)
  with(out/(name+'.log')).open('w')as stream:r=subprocess.run(['bash','scripts/check_pcie_rx_read_ahead.sh',str(dest),'300000','SOC_PCIE_RX_READ2','SOC_PCIE_RESET_COPIES','SOC_PCIE_RX_COMMIT_COPIES','SOC_PCIE_RX_CURSOR_LOCAL_RESET','SOC_PCIE_RX_LOCAL_LANE_NEXT','SOC_PCIE_RX_DLLP_LAST_COMPARE'],stdout=stream,stderr=subprocess.STDOUT,timeout=9000)
  logs=sorted(dest.glob('dw*.log'));assert len(logs)==8
  for log in logs:
   text=log.read_text();passed='RESULT PASS'in text
   rejected=any(t in text for t in ['MISMATCH','COPY MISMATCH']) and not passed
   result['cases'].append({'case':log.stem,'mutation':fault,'passed':passed,'mutation_rejected':rejected,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
   (out/'result.json').write_text(json.dumps(result,indent=2))
   assert rejected if fault else passed,text[-3000:]
  assert r.returncode!=0 if fault else r.returncode==0
 result['status']='EIGHT_TRAFFIC_PASSES_AND_EIGHT_MUTATION_REJECTIONS_NOT_SIGNOFF'
finally:
 rtl.write_text(source);(out/'result.json').write_text(json.dumps(result,indent=2))
