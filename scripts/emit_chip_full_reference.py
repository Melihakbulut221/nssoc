# SPDX-License-Identifier: Apache-2.0
"""Emit full hierarchical transistor reference from independent powered Verilog."""
import pathlib,json,hashlib,re,collections
P=pathlib.Path;out=P('hw/soc/out/namespaced-streamout');native=out/'pinmap-native'
inv=json.loads((out/'pinmap-inventory.json').read_text());q=json.loads((out/'open-output-qualification.json').read_text())
mod=json.loads((native/'logical-netlist.json').read_text())['modules'][inv['top']]
assert q['qualified_open_outputs']==1140 and not q['rejected'] and not inv['unknown_cell_types']
def digest(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
assert digest(inv['source_netlist_path'])==inv['source_netlist_sha256']
libs={};headers={};bodies={}
def cards(text):
 result=[]
 for l in text.splitlines():
  l=l.strip()
  if not l or l.startswith('*'):continue
  if l.startswith('+'):assert result;result[-1]+=' '+l[1:]
  else:result.append(l)
 return result
for path,h in inv['cdl_hashes'].items():
 assert digest(path)==h
 text=P(path).read_text();libs[path]=text;active=None
 for line in cards(text):
  t=line.split();op=t[0].upper()
  if op=='.SUBCKT':
   active=t[1].upper();assert active not in headers;headers[active]=t[2:];bodies[active]=[]
  elif op=='.ENDS':assert active is not None;active=None
  else:
   assert active is not None and not op.startswith('.'),('unsupported library directive',line)
   bodies[active].append(t)
 assert active is None
ports=[];names={}
for name,port in mod['ports'].items():
 assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name),name
 bits=port['bits'];offset=port.get('offset',0);upto=port.get('upto',0)
 for pos,bit in enumerate(bits):
  assert isinstance(bit,int) and bit not in names
  index=offset+(len(bits)-1-pos if upto else pos)
  label=name if len(bits)==1 and not offset else f'{name}[{index}]'
  names[bit]=label;ports.append(label)
assert len({s.upper() for s in ports})==len(ports)
rails={}
for name in ['VPWR','VGND']:
 p=mod['ports'][name];assert p['direction']=='inout' and len(p['bits'])==1;rails[name]=p['bits'][0]
assert rails['VPWR']!=rails['VGND']
constants=collections.Counter();supplies=collections.Counter();errors=[]
for inst,cell in mod['cells'].items():
 for pin,bits in cell['connections'].items():
  constants.update(b for b in bits if isinstance(b,str))
  if pin.upper() in ['VDD','VDD!','VDDARRAY','VDDARRAY!','VSS','VSS!']:
   rail='VGND' if pin.upper().startswith('VSS') else 'VPWR'
   if bits!=[rails[rail]]:errors.append({'instance':inst,'pin':pin,'bits':bits,'expected_top_port':rail})
   supplies[pin+'->'+rail]+=1
pre={'constants':dict(constants),'supply_connection_counts':dict(supplies),'supply_errors':errors,'full_chip_lvs_passed':False}
(out/'reference-preflight.json').write_text(json.dumps(pre,indent=2))
assert not constants,('Internal constants need explicit evidence-based treatment',dict(constants))
assert not errors,('Supply connectivity differs',errors[:5])
def nodename(bit):
 assert isinstance(bit,int)
 return names.get(bit,f'NSNET_{bit}')
lines=['* Independent powered Verilog reference; full transistor libraries below.','.SUBCKT '+inv['top']]
for start in range(0,len(ports),12):lines.append('+ '+' '.join(ports[start:start+12]))
expected={};opens=0;instance_map={}
libmods={k.upper():v for k,v in json.loads((native/'stdcell-liberty.json').read_text())['modules'].items()}
for ordinal,(inst,cell) in enumerate(mod['cells'].items()):
 typ=cell['type'].upper();conn=cell['connections'];widths={p:len(b) for p,b in sorted(conn.items())}
 variants=[v for v in inv['interfaces'][typ] if v['detail']['connection_widths']==widths];assert len(variants)==1
 mapping={m['formal']:m for m in variants[0]['detail']['mapping']};nodes=[]
 for pin in headers[typ]:
  if pin in mapping:
   m=mapping[pin];nodes.append(nodename(conn[m['verilog_port']][m['bit_position']]))
  else:
   lp=libmods.get(typ,{}).get('ports',{}).get(pin,{})
   assert re.fullmatch(r'clkload[0-9]+',inst) and pin in ('X','Y') and lp.get('direction')=='output' and len(lp['bits'])==1
   nodes.append(f'NSOPEN_{ordinal}_{pin}');opens+=1
 name=f'XNSCELL_{ordinal}';expected[name.upper()]=(nodes,typ);instance_map[name]=inst
 lines.append(name+' '+' '.join(nodes)+' '+typ)
assert opens==1140 and len(expected)==inv['cell_count']
lines.append('.ENDS '+inv['top']);toptext='\n'.join(lines)+'\n'
# Parse emitted cards independently and require every pin position to round-trip.
parsed={};topports=[]
for line in cards(toptext):
 t=line.split()
 if t[0].upper()=='.SUBCKT':topports=t[2:]
 elif t[0][0].upper()=='X':
  assert t[0].upper() not in parsed
  parsed[t[0].upper()]=(t[1:-1],t[-1].upper())
assert parsed==expected and topports==ports
# Every reachable library X call resolves, has exact arity and reaches primitives.
memo={}
def primitives(name,stack=()):
 assert name not in stack,('recursive definition',stack,name)
 if name in memo:return memo[name]
 total=0
 for t in bodies[name]:
  if t[0][0].upper()=='X':
   assert not any('=' in v for v in t),('parameterized call needs explicit parser',t)
   child=t[-1].upper();assert child in headers and len(t)-2==len(headers[child]),t
   total+=primitives(child,stack+(name,))
  else:assert t[0][0].upper() in 'MRCDQ';total+=1
 assert total>0,('empty reference cell',name)
 memo[name]=total;return total
count=sum(primitives(typ) for nodes,typ in expected.values())
full='\n'.join(libs.values())+'\n'+toptext
path=native/'soc_top-full-transistor.cdl';path.write_text(full)
(native/'reference-instance-map.json').write_text(json.dumps(instance_map))
r=dict(pre,status='FULL_TRANSISTOR_REFERENCE_EMITTED',source_netlist_sha256=inv['source_netlist_sha256'],cdl_hashes=inv['cdl_hashes'],output_sha256=digest(path),top_port_count=len(ports),logical_cell_count=len(expected),isolated_open_outputs=opens,reachable_library_definitions=len(memo),recursive_primitive_count=count,roundtrip_pin_order_passed=True,full_chip_lvs_passed=False,manufacturing_approval=False,scope='Independent full hierarchical transistor reference emitted. SRAM engineering CDL preserved exactly; no blackboxes. Electrical layout comparison remains pending.')
(out/'full-reference-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
