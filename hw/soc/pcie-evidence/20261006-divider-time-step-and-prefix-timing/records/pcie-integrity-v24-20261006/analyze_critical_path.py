# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native critical-path topology attribution; not a timing or equivalence proof."""
from pathlib import Path
import re,json,hashlib,collections,functools
B=Path(__file__).resolve().parent
net=Path('/dev/shm/nssoc-integrity-v24-balanced-sta-01/rx/repaired.v')
raw=net.read_text();pins={};types={}
for typ,name,body in re.findall(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',raw,re.S):
 assert name not in pins
 types[name]=typ;pins[name]={p:re.sub(r'\s+','',v).lstrip('\\') for p,v in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)}
# All SG13 native cells use these output names. Cell directions are independently
# checked against the original Yosys JSON for each type below, with added buffers.
m=json.loads(Path('/dev/shm/nssoc-integrity-v24-balanced-import-01/mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v24']
dirs={}
for c in m['cells'].values():
 if c['type'] in dirs:assert dirs[c['type']]==c['port_directions']
 dirs[c['type']]=c['port_directions']
lib=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')
def groups(text, kind):
 for match in re.finditer(r'\b'+kind+r'\s*\(\s*([^()]+)\s*\)\s*\{',text):
  start=match.end();i=start;depth=1
  while depth:
   if text[i]=='{':depth+=1
   if text[i]=='}':depth-=1
   i+=1
  yield match.group(1).strip().strip('"'),text[start:i-1]
for typ,body in groups(lib.read_text(),'cell'):
 if typ not in set(types.values()):continue
 found={name:re.search(r'\bdirection\s*:\s*"?(input|output)"?\s*;',part).group(1) for name,part in groups(body,'pin')}
 if typ in dirs:assert dirs[typ]==found,(typ,dirs[typ],found)
 dirs[typ]=found
assert set(types.values())<=set(dirs)
drivers={};consumers=collections.defaultdict(list)
for name,connections in pins.items():
 assert set(connections)==set(dirs[types[name]]),(name,types[name],connections)
 for port,wire in connections.items():
  if dirs[types[name]][port]=='output':
   assert wire not in drivers;drivers[wire]=name
  else:consumers[wire].append((name,port))
alias={}
for a,b in re.findall(r'\bassign\s+(.*?)\s*=\s*(.*?);',raw,re.S):
 a,b=[re.sub(r'\s+','',s).lstrip('\\') for s in [a,b]]
 if not any(t in a+b for t in '{},'):alias[a]=b
@functools.lru_cache(None)
def support(wire):
 if wire in alias:return support(alias[wire])
 name=drivers.get(wire)
 if name is None or 'df' in types[name]:return frozenset([wire])
 out=set()
 for port,w in pins[name].items():
  if dirs[types[name]][port]=='input':out.update(support(w))
 return frozenset(out)
current_aliases={}
current=m['netnames']['framer.current_block']['bits']
for name,record in m['netnames'].items():
 for offset,bit in enumerate(record['bits']):
  if bit in current:
   index=offset+record.get('offset',0)
   wire=name+(f'[{index}]' if len(record['bits'])>1 or not record.get('hide_name',0) else '')
   current_aliases[wire]=current.index(bit)
rows=[]
pattern=r'^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[\^v]\s+(\S+)/(\w+)\s+\((sg13g2_\w+)\)$'
for line in (B/'slow-critical-path.txt').read_text().splitlines():
 match=re.match(pattern,line)
 if not match:continue
 fan,cap,slew,delay,at,name,port,typ=match.groups()
 if name not in pins or port in ['CLK','RESET_B']:continue
 wire=pins[name][port];leaves=support(wire)
 bits=sorted({current_aliases[w] for w in leaves if w in current_aliases})
 words=sorted({(bit%128)//8 for bit in bits});assert all(j<4 for j in words)
 rows.append({'cell':name,'type':typ,'output':wire,'fanout':int(fan),'delay_ns':float(delay),'arrival_ns':float(at),'structural_current_word_support':words,'current_block_bits':bits,'other_leaf_bases':sorted({re.sub(r'\[.*','',w) for w in leaves if w not in current_aliases})})
report=(B/'slow-critical-path.txt').read_text()
start=re.search(r'^Startpoint: (\S+)',report).group(1)
endpoint=re.search(r'(?m)^Endpoint: (\S+)',report).group(1)
assert rows[0]['cell']==start and rows[-1]['output']==pins[endpoint]['D']
# Every consecutive reported path output is a direct input net of its successor.
for a,b in zip(rows,rows[1:]):assert a['output'] in pins[b['cell']].values(),(a,b)
bytype=collections.defaultdict(lambda:{'count':0,'delay_ns':0.})
for x in rows:
 family='buffer' if '_buf_' in x['type'] else 'mux' if '_mux' in x['type'] else 'xor_xnor' if '_xor' in x['type'] or '_xnor' in x['type'] else 'launch_ff' if '_df' in x['type'] else 'other_boolean'
 bytype[family]['count']+=1;bytype[family]['delay_ns']+=x['delay_ns']
changes=[];last=None
for x in rows:
 if x['structural_current_word_support']!=last:
  changes.append({k:x[k] for k in ['cell','arrival_ns','structural_current_word_support']});last=x['structural_current_word_support']
assert abs(sum(x['delay_ns'] for x in rows)-rows[-1]['arrival_ns'])<2e-5
p=lambda v:{'bytes':v.stat().st_size,'sha256':hashlib.sha256(v.read_bytes()).hexdigest()}
d={'status':'NATIVE_CRITICAL_PATH_TOPOLOGY_AND_REPORTED_DELAY_ATTRIBUTION','inputs':{str(v):p(v) for v in [Path(__file__),net,lib,Path('/dev/shm/nssoc-integrity-v24-balanced-import-01/mapped.json'),B/'slow-critical-path.txt']},'rows':rows,'delay_by_cell_family':dict(bytype),'word_support_growth':changes,'scope':'Exact native reported path and connectivity; structural support overapproximates Boolean dependence and cannot assign optimized gates uniquely to source parser steps. Preplacement ideal-clock report only, no physical extracted timing.','startpoint_q_wire':pins[start]['Q'],'endpoint_q_wire':pins[endpoint]['Q'],'conclusion':'Measured residual native cone after parallelconstant-slot read selection. Endpoint and word-support growth are reported without inferring a unique source statement or physical signoff.', 'startpoint':start,'endpoint':endpoint}
(B/'critical-path-attribution.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'delay_by_cell_family':dict(bytype),'word_support_growth':changes},indent=2))
