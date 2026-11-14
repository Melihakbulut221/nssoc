# SPDX-License-Identifier: Apache-2.0
"""Qualify intentionally open outputs against frozen Liberty; emit diagnosis only."""
import pathlib,json,hashlib,subprocess,re,collections
P=pathlib.Path;out=P('hw/soc/out/namespaced-streamout');native=out/'pinmap-native'
inv=json.loads((out/'pinmap-inventory.json').read_text());net=json.loads((native/'logical-netlist.json').read_text())['modules'][inv['top']]
libs=list(P('hw/soc/tools/ciel-corrpre').rglob('sg13g2_stdcell_typ_1p20V_25C.lib'));assert len(libs)==1,list(map(str,libs))
lib=libs[0];dest=native/'stdcell-liberty.json'
assert not any(c in str(lib) for c in ['"','\n',';'])
with (native/'liberty-yosys.log').open('w') as log:
 result=subprocess.run(['yosys','-Q','-T','-p',f'read_liberty -lib "{lib.resolve()}"; write_json "{dest.resolve()}"'],stdout=log,stderr=subprocess.STDOUT,timeout=600)
assert result.returncode==0
mods={k.upper():v for k,v in json.loads(dest.read_text())['modules'].items()}
def qualifies(instance,error,ports):
 if error.get('reason')!='missing named connection':return False
 formal=error.get('formal','');p=ports.get(formal)
 return bool(re.fullmatch(r'clkload[0-9]+',instance) and p and p.get('direction')=='output' and len(p.get('bits',[]))==1 and formal in ('X','Y'))
controls={}
for name,inst,err,ports,want in [
 ('scalar_output','clkload1',{'reason':'missing named connection','formal':'X'},{'X':{'direction':'output','bits':[1]}},True),
 ('input','clkload1',{'reason':'missing named connection','formal':'X'},{'X':{'direction':'input','bits':[1]}},False),
 ('power','clkload1',{'reason':'missing named connection','formal':'VDD'},{'VDD':{'direction':'inout','bits':[1]}},False),
 ('bus','clkload1',{'reason':'missing named connection','formal':'X'},{'X':{'direction':'output','bits':[1,2]}},False),
 ('wrong_width','clkload1',{'reason':'scalar width differs','formal':'X'},{'X':{'direction':'output','bits':[1]}},False),
 ('unrelated_instance','logic1',{'reason':'missing named connection','formal':'X'},{'X':{'direction':'output','bits':[1]}},False)]:
 actual=qualifies(inst,err,ports);assert actual==want;controls[name]={'accepted':actual,'expected':want}
counts=collections.Counter();rejected=[];examined=0
for instance,cell in net['cells'].items():
 typ=cell['type'].upper();variants=inv['interfaces'].get(typ,[])
 widths={p:len(b) for p,b in sorted(cell['connections'].items())}
 matching=[v for v in variants if v['detail']['connection_widths']==widths];assert len(matching)==1,(instance,typ)
 mapped={m['formal'] for m in matching[0]['detail']['mapping']}
 issues=inv['interface_issues'].get(typ,[])
 missing=[e for v in issues for e in v['detail'] if e.get('formal') not in mapped]
 # Deduplicate repeated diagnostics across connection variants.
 missing=list({json.dumps(e,sort_keys=True):e for e in missing}.values())
 for error in missing:
  examined+=1
  if qualifies(instance,error,mods.get(typ,{}).get('ports',{})):counts[typ+':'+error['formal']]+=1
  else:rejected.append({'instance':instance,'type':typ,'error':error})
assert sum(counts.values())==1140 and examined==1140 and not rejected,(examined,counts,rejected[:10])
ports={};bybit=collections.defaultdict(list);constants=[]
for name,port in net['ports'].items():
 ports[name]={k:port.get(k) for k in ('direction','offset','upto','signed')};ports[name]['width']=len(port['bits'])
 for pos,bit in enumerate(port['bits']):
  label={'port':name,'position':pos}
  if isinstance(bit,str):constants.append(dict(label,value=bit))
  else:bybit[bit].append(label)
report={'status':'OPEN_OUTPUTS_QUALIFIED_TOP_PORTS_INVENTORIED','source_netlist_sha256':inv['source_netlist_sha256'],'liberty_path':str(lib),'liberty_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'liberty_parser_returncode':result.returncode,'qualified_open_outputs':sum(counts.values()),'qualified_counts':dict(counts),'rejected':rejected,'negative_controls':controls,'top_ports':ports,'top_constants':constants,'top_aliases':[{'bit':b,'ports':v} for b,v in bybit.items() if len(v)>1],'supply_configuration':inv['supply_configuration'],'full_chip_lvs_passed':False,'scope':'All omitted pins checked against pinned Liberty and exact clkload instance naming. No netlist alteration or electrical LVS acceptance. Constant and alias mapping still requires explicit schematic emission.'}
(out/'open-output-qualification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['status','qualified_open_outputs','qualified_counts','top_constants','top_aliases','supply_configuration']}))
