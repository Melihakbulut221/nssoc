"""Independent closed TX03 result anchors and measured next-target census."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,re,xml.etree.ElementTree as ET
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parents[1];P=Path(__file__).resolve().parent
D=Path('/dev/shm/nssoc-tx-path-v4-repair03-drt-01');X=Path('/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
review=json.loads((P/'review.json').read_text())
for p,v in review['inputs_rehashed'].items():assert pin(p)==v,p
results=[]
for directory in [D,X]:
 j=json.loads((directory/'result.json').read_text());assert j['status'].startswith('COMPLETE_')and j['returncode']==0
 for p,v in j['inputs'].items():assert pin(p)==v
 for p,v in j['outputs'].items():assert pin(directory/p)==v
 results.append(dict(path=str(directory/'result.json'),**pin(directory/'result.json')))
assert (D/'router-drc.rpt').stat().st_size==0
assert re.findall(r'Number of violations = (\d+)',(D/'native.log').read_text())[-1]=='0'
assert (D/'routed.v').read_bytes()==Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-03/repaired.v').read_bytes()
def parse_slacks(path):
 text=Path(path).read_text();markers=list(re.finditer(r'^EXTRACTED_NOMINAL_RC_(slow|typical|fast)_(max|min)$',text,re.M));assert len(markers)==6
 values=defaultdict(lambda:defaultdict(list))
 for i,mark in enumerate(markers):
  body=text[mark.end():markers[i+1].start()if i+1<len(markers)else len(text)]
  paths=re.split(r'(?m)^Startpoint:',body)[1:];assert len(paths)==6
  for case in paths:
   slacks=re.findall(r'^\s*(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)\s*$',case,re.M);assert len(slacks)==1
   number=float(slacks[0][0]);assert (number<0)==(slacks[0][1]=='VIOLATED')
   kind=('recovery'if'recovery check'in case else'setup')if mark[2]=='max'else('removal'if'removal check'in case else'hold')
   values[mark[1]][kind].append(number)
 assert all(len(rows)==3 for groups in values.values()for rows in groups.values())
 return {c:{k:min(v)for k,v in groups.items()}for c,groups in values.items()}
actual=parse_slacks(X/'native.log');prior=parse_slacks('/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02/native.log')
assert actual==review['nominal_rc_cell_corner_slack_ns'];assert prior==review['nominal_prior_and_improvement']['prior']
delta={c:{k:round(actual[c][k]-prior[c][k],6)for k in actual[c]}for c in actual}
assert delta==review['nominal_prior_and_improvement']['delta_ns']
chain=B/'repair03-continuation02/result.json';j=json.loads(chain.read_text());assert j['status']=='COMPLETE_TX03_FINITE_ROUTE_RC_REVIEW_PUBLICATION'and all(row['returncode']==0 for row in j['stages'])
paths=review['SS_three_worst_setup_paths'];log=(X/'native.log').read_text()
assert len(paths)==3 and all('Startpoint:'+row['raw_path']in log for row in paths)
raw=(D/'routed.v').read_text();cells={}
for typ,name,body in re.findall(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',raw,re.S):
 assert name not in cells
 cells[name]=(typ,{p:re.sub(r'\s+','',v)for p,v in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)})
lib=next(Path(p)for p in review['inputs_rehashed']if p.endswith('sg13g2_stdcell_slow_1p08V_125C.lib'))
def groups(text,kind):
 for match in re.finditer(r'\b'+kind+r'\s*\(\s*([^()]+)\s*\)\s*\{',text):
  begin=match.end();i=begin;depth=1
  while depth:
   if text[i]=='{':depth+=1
   elif text[i]=='}':depth-=1
   i+=1
  yield match[1].strip().strip('"'),text[begin:i-1]
library=dict(groups(lib.read_text(),'cell'));directions={}
for typ in {t for t,_ in cells.values()}:
 directions[typ]={n:re.search(r'\bdirection\s*:\s*"?(input|output)"?\s*;',body)[1]for n,body in groups(library[typ],'pin')}
targets=[]
selected=['_52799_','_45901_','_45902_','place13039','place12268','place12617','_46234_','_47594_','_46708_']
for name in selected:
 typ,connections=cells[name];out=next(p for p in connections if directions[typ][p]=='output');net=connections[out]
 loads=[dict(instance=n,master=t,pin=p)for n,(t,cons)in cells.items()for p,w in cons.items()if w==net and directions[t][p]=='input']
 lines=[]
 for path in paths:
  for line in path['raw_path'].splitlines():
   m=re.match(r'^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[\^v]\s+(\S+)/(\w+)\s+\((\w+)\)$',line)
   if m and m[6]==name:
    assert m[7]==out and m[8]==typ and int(m[1])==len(loads)
    row=dict(fanout=int(m[1]),cap_pf=float(m[2]),slew_ns=float(m[3]),delay_ns=float(m[4]),arrival_ns=float(m[5]),raw_line=line)
    if row not in lines:lines.append(row)
 assert lines
 targets.append(dict(instance=name,master=typ,output=out,net=net,loads=loads,actual_slow_lines=lines))
def signatures(typ):
 body=library[typ]
 pins={n:dict(direction=re.search(r'\bdirection\s*:\s*"?(input|output)"?\s*;',part)[1],function=(m[1]if(m:=re.search(r'\bfunction\s*:\s*"([^"]+)"',part))else None))for n,part in groups(body,'pin')}
 ff=[re.findall(r'\b(next_state|clocked_on|clear|preset|clear_preset_var1|clear_preset_var2)\s*:\s*"?([^;]+);',part)for n,part in groups(body,'ff')]
 return dict(pins=pins,ff=ff)
alternatives=[]
for old,new in [('sg13g2_dfrbpq_1','sg13g2_dfrbpq_2'),('sg13g2_buf_1','sg13g2_buf_4'),('sg13g2_buf_1','sg13g2_buf_8'),('sg13g2_a21oi_1','sg13g2_a21oi_2')]:
 assert signatures(old)==signatures(new)
 alternatives.append(dict(old=old,new=new,logic_signature=signatures(old)))
assert [n for n in library if n.startswith('sg13g2_xnor2_')]==['sg13g2_xnor2_1']
port_dir=Path('/dev/shm/nssoc-tx-path-v4-repair03-physical-replay-01');xmls=list(port_dir.rglob('results.xml'));casecount=0
for p in xmls:
 cases=ET.parse(p).findall('.//testcase');casecount+=len(cases);assert all(all(c.find(t)is None for t in ['failure','error','skipped'])for c in cases)
assert casecount==3
r=dict(status='PASS_INDEPENDENT_SAVED_TX03_NUMERICAL_AND_SOURCE_ANCHORS_TIMING_REJECTED',method=pin(Path(__file__)),review=pin(P/'review.json'),terminal_results=results,continuation=pin(chain),inputs_rehashed_count=len(review['inputs_rehashed']),slacks_ns=actual,prior_TX02_slacks_ns=prior,delta_ns=delta,router_DRC=0,same_routed_netlist=True,port_XML_actual_cases=3,
 shared_three_path_prefix=dict(instances=['_52799_','_45901_','_45902_'],total_reported_delay_ns=round(.636612+.672247+.802993,6),launch_clock_ns=.904130,worst_capture_clock_ns=.905608,worst_clock_skew_ns=.001478),
 measured_targets=targets,liberty_alternatives=alternatives,
 proposed_next_bounded_comparison='KeepTX02 andTX03 as separate measured baselines. First read more endpoint paths, including priorTX02 critical endpoints, before selecting a candidate. Compare same-constraint GRT variants with shared _52799_ DFRBPQ1→2 versus output load isolation; two shared XNOR1 gates have no native higher drive and need exact-load buffering/partitioning rather than an imaginary upsize. Existing weak buffers place13039/place12268 and branchplace12617 offer actual buf4/8 alternatives; compare input-cap impact because upstream XNORs are already loaded. Secondary A21OI1 gates have a21oi2. Require all-group/endpoint regression checks and the existing proof/ports/freshDRT/RC gates before adoption.',
 interpretation='SSsetup regressed211.598ps while SShold improved42.296ps. All three newly reported worst setup paths share a2.111852ns launchFF/XNOR/XNOR prefix; the previous seven TX03 isolation targets differ. Worst launch/capture clock skew is only1.478ps, so measured data load/slew is the immediate repair hypothesis. More path coverage is required before claiming causality or gain; source/ECO plus rerouting may move the worst path. No full native STA, extraction, proof or transport replay was run here.',
 physical_acceptance=False,qualified_rc=False,scope='Independent read/hash/parse of closed finite evidence only. Unqualified nominal sameRC under3cell corners; no fullchip, PHY or manufacturing acceptance.')
out=P/'independent-result-peer-rx.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out))))
