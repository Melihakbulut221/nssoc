# SPDX-License-Identifier: Apache-2.0
"""Cloud-only preflight of the two verified engineering SRAM reference libraries."""
import hashlib,json,zipfile,tarfile,io,pathlib
P=pathlib.Path
configs={
 'dp':('bff8640c1efc79d3877f3ececa08d369d5c80bbc81556c13284e540566aa260e','1b8f2b6d11af2956fa0caf074b8329bf2e49722a4c5ce954c2119ad9ae4992b0'),
 'sp':('0f1064d309dfe7e2e91d448e10ebc0f3234f046f9858fc67f94903cb8a76ece6','3ef741993177dccaf1be29e34561c2b6d13d4c20dc75b00d6ab72b0a4a972a7c')}
libs={};evidence={}
for kind,(archive_hash,reference_hash) in configs.items():
 raw=P(kind+'.zip').read_bytes();assert hashlib.sha256(raw).hexdigest()==archive_hash
 z=zipfile.ZipFile(io.BytesIO(raw));assert z.namelist()==['bounded-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:
  raw=t.extractfile('native/engineering-reference-v1.cdl').read()
 assert hashlib.sha256(raw).hexdigest()==reference_hash
 cells={};current=None;records=[];outside=[]
 for line in raw.decode().splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  tokens=line.upper().split()
  if tokens[0]=='.SUBCKT':
   assert current is None and len(tokens)>2
   current=tokens[1];assert current not in cells;records=[tokens]
  elif tokens[0]=='.ENDS':
   assert current is not None
   assert len(tokens)==1 or tokens[1]==current
   cells[current]=records;current=None;records=[]
  elif current is not None:
   if tokens[0]=='+':assert records;records[-1]+=tokens[1:]
   else:records.append(tokens)
  else:outside.append(tokens)
 assert current is None and cells
 libs[kind]=cells
 evidence[kind]={'reference_sha256':reference_hash,'cell_count':len(cells),'cells':{n:{'sha256':hashlib.sha256(json.dumps(rows).encode()).hexdigest(),'ports':len(rows[0])-2,'records':len(rows)-1} for n,rows in cells.items()},'outside_directive_types':sorted({r[0] for r in outside})}
common=sorted(libs['sp'].keys()&libs['dp'].keys());identical=[];different=[]
for name in common:
 (identical if libs['sp'][name]==libs['dp'][name] else different).append(name)
reachability={}
for kind,cells in libs.items():
 top={'dp':'RM_IHPSG13_2P_256X16_C2_BM_BIST','sp':'RM_IHPSG13_1P_2048X64_C2_BM_BIST'}[kind]
 assert top in cells
 edges={};unknown={}
 for name,records in cells.items():
  edges[name]=[];unknown[name]=[]
  for tokens in records[1:]:
   if not tokens[0].startswith('X'):continue
   refs=[tok for tok in tokens[1:] if tok in cells]
   assert len(refs)<=1,(kind,name,tokens[0],refs)
   if refs:edges[name].append(refs[0])
   else:unknown[name].append(tokens[0])
 reached=set();frontier={top}
 while frontier:
  reached.update(frontier);frontier={target for name in frontier for target in edges[name]}-reached
 reachability[kind]={'top':top,'reachable_cells':sorted(reached),'unreachable_cells':sorted(cells.keys()-reached),'conflicting_cells_reachable':sorted(set(different)&reached),'unresolved_reachable_X_instances':{name:unknown[name] for name in reached if unknown[name]},'direct_reference_counts':{target:sum(edges[name].count(target) for name in reached) for target in different}}
r={'status':'REFERENCE_LIBRARY_COLLISION_PREFLIGHT','accepted':False,'full_chip_lvs_passed':False,'manufacturing_approval':False,'libraries':evidence,'reachability':reachability,'identical_shared_cells':identical,'different_shared_cells':different,'scope':'Exact case/whitespace/continuation-normalized subcircuit records only; differing definitions cannot be merged by name. No geometry or circuit edits, no electrical equivalence claim.'}
P('out').mkdir();P('out/reference-library-preflight.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'common':len(common),'identical':len(identical),'different':different}))
