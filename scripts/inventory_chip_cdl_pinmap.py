# SPDX-License-Identifier: Apache-2.0
"""Read independent routed Verilog and full CDL interfaces; never black-box LVS."""
import pathlib,json,hashlib,re,subprocess,collections,sys
P=pathlib.Path;out=P('hw/soc/out/namespaced-streamout');state=json.loads((out/'state.json').read_text());config=json.loads((out/'config.json').read_text())
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
key='pnl' if state.get('pnl') else 'nl';source=state[key];assert isinstance(source,str) and P(source).is_file()
source_hash=sha(source);native=out/'pinmap-native';native.mkdir();json_path=native/'logical-netlist.json'
assert not any(c in source for c in ['"','\n',';'])
command=['yosys','-Q','-T','-p',f'read_verilog "{source}"; write_json "{json_path.resolve()}"']
with (native/'yosys.log').open('w') as log:
 proc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600)
assert proc.returncode==0 and sha(source)==source_hash
netlist=json.loads(json_path.read_text());top=config['DESIGN_NAME'];assert top in netlist['modules'];module=netlist['modules'][top]
std=list(P('hw/soc/tools/ciel-corrpre').rglob('sg13g2_stdcell.cdl'));assert len(std)==1,('Standard-cell CDL path ambiguous',list(map(str,std)))
sources=[std[0],P('hw/soc/out/namespaced-sram-library/sram-engineering.cdl')];headers={};hashes={}
for f in sources:
 hashes[str(f)]=sha(f);records=[]
 for line in f.read_text().splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  if line.startswith('+'):assert records;records[-1]+=' '+line[1:]
  else:records.append(line)
 for line in records:
  tokens=line.split()
  if tokens[0].upper()!='.SUBCKT':continue
  name=tokens[1].upper();assert name not in headers and all('=' not in pin for pin in tokens[2:]);headers[name]=tokens[2:]
counts=collections.Counter();rows={};unknown={};issues={}
for instance,cell in module['cells'].items():
 name=cell['type'].upper();counts[name]+=1;connections=cell['connections']
 if name not in headers:
  unknown.setdefault(name,[])
  if len(unknown[name])<5:unknown[name].append(instance)
  continue
 mapping=[];used=set();errors=[]
 for formal in headers[name]:
  match=re.fullmatch(r'(.*?)<([0-9]+)>',formal) or re.fullmatch(r'(.*?)\[([0-9]+)\]',formal)
  port=match[1] if match else formal;index=int(match[2]) if match else None
  alias=None
  if port not in connections and port.upper() in ['VDD!','VSS!','VDDARRAY!'] and port[:-1] in connections:
   alias=port;port=port[:-1]
  if port not in connections:
   errors.append({'formal':formal,'reason':'missing named connection'});continue
  bits=connections[port];used.add(port)
  if index is None:
   if len(bits)!=1:errors.append({'formal':formal,'reason':'scalar width differs','actual':len(bits)});continue
   position=0
  else:
   bus_indices=[]
   for pin in headers[name]:
    m=re.fullmatch(re.escape(match[1])+r'(?:<([0-9]+)>|\[([0-9]+)\])',pin)
    if m:bus_indices.append(int(m[1] or m[2]))
   assert len(bus_indices)==len(set(bus_indices))
   if min(bus_indices)!=0 or sorted(bus_indices)!=list(range(max(bus_indices)+1)) or len(bits)!=len(bus_indices):
    errors.append({'formal':formal,'reason':'bus index/width needs explicit mapping','indices':sorted(bus_indices),'actual_width':len(bits)});continue
   position=index
  mapping.append({'formal':formal,'verilog_port':port,'bit_position':position,'explicit_supply_alias':alias})
 extras=sorted(set(connections)-used)
 if extras:errors.append({'reason':'extra connections absent from CDL header','ports':extras})
 if errors:
  issues.setdefault(name,{'examples':[],'errors':errors})
  if len(issues[name]['examples'])<5:issues[name]['examples'].append(instance)
 signature={'formal_pin_count':len(headers[name]),'mapping':mapping,'connection_widths':{p:len(b) for p,b in sorted(connections.items())}}
 if name in rows:assert rows[name]==signature,('Instance interface mismatch',name,instance)
 else:rows[name]=signature
r={'status':'INDEPENDENT_VERILOG_CDL_PINMAP_INVENTORY','source_view':key,'source_netlist_sha256':source_hash,'source_netlist_path':source,'source_route_run':43579643337,'yosys_returncode':proc.returncode,'source_unchanged':sha(source)==source_hash,'cdl_hashes':hashes,'top':top,'top_port_count':len(module['ports']),'cell_count':sum(counts.values()),'cell_type_counts':dict(counts),'interfaces':rows,'unknown_cell_types':unknown,'interface_issues':issues,'all_named_pin_interfaces_resolved':not unknown and not issues,'supply_configuration':{k:config.get(k) for k in ['VDD_NETS','GND_NETS','VDD_PIN','GND_PIN']},'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Independent logical Verilog parsed without synthesis/optimization. Full standard-cell and namespaced SRAM CDL formal interfaces inventoried. Does not emit schematic, assign missing supplies or prove final port ordering/LVS.'}
(out/'pinmap-inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ['status','source_view','cell_count','unknown_cell_types','interface_issues','all_named_pin_interfaces_resolved']}))
