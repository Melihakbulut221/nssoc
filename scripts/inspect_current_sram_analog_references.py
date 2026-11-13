# SPDX-License-Identifier: Apache-2.0
"""Inventory exact routed SRAM analog references and extraction support."""
import hashlib,json,pathlib,re,tarfile,collections
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'status':'ERROR','qualified_lvs':False,'manufacturing_approval':False}
try:
 with open('pkg.tgz','rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 with tarfile.open('pkg.tgz','r:gz') as t:
  members=t.getmembers();contracts=[m for m in members if m.isfile() and m.name.endswith('/input-contract.json')];assert len(contracts)==1
  c=json.loads(t.extractfile(contracts[0]).read());prefix=str(pathlib.PurePosixPath(contracts[0].name).parent)+'/files/';index={m.name:m for m in members}
  names=list(c['input_files']);r['sram_extensions']=dict(collections.Counter(pathlib.PurePosixPath(n).suffix for n in names if '/sg13g2_sram/' in n));rows=[]
  for name,info in c['input_files'].items():
   if '/sg13g2_sram/' not in name or pathlib.PurePosixPath(name).suffix.lower() not in ['.cdl','.spice','.spi','.cir']:continue
   raw=t.extractfile(index[prefix+name]).read();sha=hashlib.sha256(raw).hexdigest();assert sha==info['sha256']
   text=raw.decode();lines=[]
   for l in text.splitlines():
    l=l.strip()
    if not l or l.startswith('*'):continue
    if l.startswith('+'):assert lines;lines[-1]+=' '+l[1:]
    else:lines.append(l)
   subs=[l.split()[1] for l in lines if l.lower().startswith('.subckt ')];targets=[x for x in subs if x in ['RM_IHPSG13_1P_2048x64_c2_bm_bist','RM_IHPSG13_2P_256x16_c2_bm_bist']]
   rows.append({'path':name,'sha256':sha,'bytes':len(raw),'subcircuit_count':len(subs),'target_subcircuits':targets,'subcircuits':subs,'includes':[l.split()[1:] for l in lines if l.lower().startswith(('.include ','.inc ','.lib '))]})
  r['analog_references']=rows
  r['extraction_support_paths']=[n for n in names if any(v in n.lower() for v in ['lvs','extract']) and pathlib.PurePosixPath(n).suffix.lower() in ['.lylvs','.lym','.rb','.py','.tcl','.spice','.json','.tech']]
 r['status']='CURRENT_PACKAGE_REFERENCE_INVENTORY_COMPLETE'
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'current-sram-reference-inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['analog_references','extraction_support_paths']}));raise SystemExit(0 if r['status'].endswith('_COMPLETE') else 1)
