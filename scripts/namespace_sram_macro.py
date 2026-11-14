# SPDX-License-Identifier: Apache-2.0
"""Namespace native SRAM geometry and CDL without changing circuit contents."""
import re,json,hashlib,pathlib
import klayout.db as db
P=pathlib.Path

def cards(text):
 result=[]
 for line in text.splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  if line.startswith('+'):
   assert result;result[-1]+=line[1:].upper().split()
  else:result.append(line.upper().split())
 return result

def remap(records,names):
 result=[];inside=False
 for original in records:
  row=original[:]
  if row[0]=='.SUBCKT':assert not inside;inside=True;row[1]=names.get(row[1],row[1])
  elif row[0]=='.ENDS':
   assert inside;inside=False
   if len(row)>1:row[1]=names.get(row[1],row[1])
  elif row[0].startswith('X') and inside:
   hits=[i for i,token in enumerate(row[1:],1) if token in names]
   assert len(hits)<=1,(row[0],hits)
   if hits:row[hits[0]]=names[row[hits[0]]]
  result.append(row)
 assert not inside
 return result

def geometry(layout,inverse=None):
 inverse=inverse or {};result={}
 for c in layout.each_cell():
  layers=[]
  for li in layout.layer_indexes():
   info=layout.get_info(li);shapes=sorted(s.to_s() for s in c.shapes(li).each())
   if shapes:layers.append((info.layer,info.datatype,shapes))
  children=[]
  for i in c.each_inst():
   name=layout.cell(i.cell_index).name
   children.append((inverse.get(name,name),i.trans.to_s(),str(i.a),str(i.b),i.na,i.nb))
  result[inverse.get(c.name,c.name)]={'layers':sorted(layers),'children':sorted(children),'bbox':c.bbox().to_s()}
 return {'dbu':layout.dbu,'cells':result}

def namespace_macro(gds,reference,top,prefix,output):
 assert prefix in ['NSDP_','NSSP_']
 text=P(reference).read_text();original=cards(text)
 definitions=[r[1] for r in original if r[0]=='.SUBCKT'];assert len(definitions)==len(set(definitions))==145
 assert top.upper() in definitions
 mapping={n:(n if n==top.upper() else prefix+n) for n in definitions}
 changed=remap(original,mapping);inverse={v:k for k,v in mapping.items()};assert len(inverse)==len(mapping)
 assert remap(changed,inverse)==original
 assert next(r for r in changed if r[:2]==['.SUBCKT',top.upper()])==next(r for r in original if r[:2]==['.SUBCKT',top.upper()])
 # Verify that preservation check detects a modified native device parameter.
 damaged=[r[:] for r in changed];hits=[i for i,r in enumerate(damaged) if r[0].startswith('R') and any(t.startswith('W=') for t in r)]
 assert hits
 i=hits[0];j=next(j for j,t in enumerate(damaged[i]) if t.startswith('W='));damaged[i][j]='W=9E-7'
 assert remap(damaged,inverse)!=original
 encoded='* Namespaced engineering reference; not foundry approval\n'+'\n'.join(' '.join(r) for r in changed)+'\n'
 assert cards(encoded)==changed
 layout=db.Layout();layout.read(str(gds));before=geometry(layout);physical_names={c.name:(c.name if c.name.upper()==top.upper() else prefix+c.name) for c in layout.each_cell()}
 assert len(set(physical_names.values()))==len(physical_names)
 for c in layout.each_cell():c.name=physical_names[c.name]
 physical_inverse={v:k for k,v in physical_names.items()}
 assert geometry(layout,physical_inverse)==before
 layout.write(str(gds));check=db.Layout();check.read(str(gds));assert geometry(check,physical_inverse)==before
 P(reference).write_text(encoded)
 renames={k.upper():v for k,v in physical_names.items()}
 for k,v in mapping.items():
  if k in renames:assert renames[k].upper()==v
  else:renames[k]=v
 proof={'prefix':prefix,'top':top,'original_reference_sha256':hashlib.sha256(text.encode()).hexdigest(),'namespaced_reference_sha256':hashlib.sha256(encoded.encode()).hexdigest(),'namespaced_gds_sha256':hashlib.sha256(P(gds).read_bytes()).hexdigest(),'reference_definition_count':145,'physical_cell_count':len(physical_names),'reversible_all_records':True,'device_parameter_mutation_rejected':True,'top_ports_unchanged':True,'physical_geometry_and_instances_unchanged_after_roundtrip':True,'reference_renames':mapping,'physical_renames':physical_names,'renames':renames,'full_chip_lvs_passed':False,'manufacturing_approval':False}
 P(output).write_text(json.dumps(proof,indent=2));return proof

def namespace_deck(text,renames):
 # Only exact quoted cell-name operands; layers, models, pins and global nets unchanged.
 def replace(m):
  quote=m.group(1);name=m.group(2);return quote+renames.get(name.upper(),name)+quote
 return re.sub(r"(['\"])([^'\"\n]+)\1",replace,text)
