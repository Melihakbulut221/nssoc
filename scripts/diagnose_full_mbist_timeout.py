# SPDX-License-Identifier: Apache-2.0
import pathlib,zipfile,hashlib,json,re
p=pathlib.Path('reports.zip');assert hashlib.sha256(p.read_bytes()).hexdigest()=='241c3d7ed1855724022f219077f3d78b116b1b93781633f83d3d89d1f1ffc6a7'
z=zipfile.ZipFile(p);r={'source_run':43516903518,'accepted':False,'inventory':[{'name':i.filename,'bytes':i.file_size} for i in z.infolist()],'logs':{},'json_summaries':{}}
for n in z.namelist():
 if n.endswith('.log'):
  text=z.read(n).decode(errors='replace');lines=text.splitlines()
  hits=[line[:1000] for line in lines if re.search(r'(?:\[TB\]|\[MBIST\]|MBIST.*(?:busy|done|fail)|FATAL|TIMEOUT|timed out|TimeoutExpired)',line,re.I)]
  r['logs'][n]={'total_lines':len(lines),'selected_count':len(hits),'first_15':hits[:15],'last_30':hits[-30:]}
 if n.endswith('.json'):
  try:d=json.loads(z.read(n))
  except Exception:continue
  if isinstance(d,dict):
   allowed=['status','passed','returncode','elapsed_s','error','mbist_boot_passed','pcie_idle_boot_passed','SOC_SRAM_MBIST','SOC_ETH_MBIST','checks','gates','steps','results']
   summary={k:d[k] for k in allowed if k in d}
   # Keep only bounded top-level scalar outcomes; nested native metadata stays cloud.
   r['json_summaries'][n]={'keys':list(d),'scalars':{k:v for k,v in summary.items() if isinstance(v,(str,int,float,bool)) or v is None}}
r['gate_run_log']=z.read('corrpre-pcie-mbist-native-boot/gates/run-0.log').decode(errors='replace')
assert len(r['gate_run_log'])<25000
r['gate_result']=json.loads(z.read('corrpre-pcie-mbist-native-boot/gates/result.json'))
pathlib.Path('out').mkdir();pathlib.Path('out/boot-diagnostic.json').write_text(json.dumps(r,indent=2));print('Filtered derived summaries only; no acceptance')
