# SPDX-License-Identifier: Apache-2.0
import hashlib,json,pathlib,subprocess,tarfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
root=pathlib.Path('native');root.mkdir(exist_ok=True)
expected='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9'
rows=[];found=[]
for name,digest in [('replay-inputs','44bf3bb09e1ccba823a15390ad6ca30e6cf2f8dd46ee17f2a2c74508ad4b8da3'),('corresponding-sources','d3ab6880d1cce8162d127cad40f74981c853f50bdcb5e04cf3cfbe56837c9aca')]:
 archive=root/(name+'.tar.xz')
 url='https://raw.githubusercontent.com/Melihakbulut221/nssoc/3a997ac4fb7a212b941139b9ec3e68824d4dc2d4/docs/evidence/sram-chip-integration-20260925-'+name+'.tar.xz'
 subprocess.run(['curl','-fL','--retry','5',url,'-o',str(archive)],check=True)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
 with tarfile.open(archive,'r:xz') as tar:
  for member in tar:
   if not member.isfile() or not member.name.endswith(('.spice','.cdl','.cir')):continue
   b=tar.extractfile(member).read();sha=hashlib.sha256(b).hexdigest();text=b.decode();subs=[line.split()[1] for line in text.splitlines() if line.lower().startswith('.subckt ')]
   rows.append(dict(archive=name,member=member.name,sha256=sha,bytes=len(b),subcircuits=subs,mos_cards=sum(line.lstrip().lower().startswith('m') for line in text.splitlines())))
   if sha==expected:(root/'reference.spice').write_bytes(b);found.append(rows[-1])
result=dict(status='FOUND_HASH_LOCKED_REFERENCE' if found else 'REFERENCE_NOT_IN_SELECTED_ARCHIVES',expected_sha256=expected,found=found,inventory=rows,scope='Reference recovery only; no topology, RC, LVS or timing acceptance.')
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
raise SystemExit(0 if found else 1)
