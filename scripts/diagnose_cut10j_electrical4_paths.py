# SPDX-License-Identifier: Apache-2.0
"""Cloud-only full native timing report survey before hold ECO."""
import pathlib,hashlib,zipfile,tarfile,json,re,io
p=pathlib.Path('reports.zip')
with p.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest=='809a2a994149ddf95ca42d0deaa5f89a8a4692c47df9186cb0bd1a2ef2d714f2'
rows=[];inventory=[]
with zipfile.ZipFile(p) as z:
 names=[n for n in z.namelist() if n.endswith('.tgz') or n.endswith('.tar.gz')];assert len(names)==1,names
 with z.open(names[0]) as payload, tarfile.open(fileobj=payload,mode='r|gz') as tar:
  for member in tar:
   n=member.name
   if not member.isfile() or not n.endswith(('/max.rpt','/min.rpt')):continue
   if not any(c in n for c in ['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']):continue
   inventory.append({'path':n,'bytes':member.size});count=0;best=[];blocks_seen=0
   def consume(block):
    global count,blocks_seen,best
    start=re.search(r'^Startpoint:\s*(.*)',block,re.M);end=re.search(r'^Endpoint:\s*(.*)',block,re.M)
    if not start or not end:return
    blocks_seen+=1
    # Require bank-6 SRAM endpoint, not a path ending at its launching register.
    if 'u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem' not in end[1]:return
    if 'A_ADDR[6]' not in block:return
    sl=re.search(r'(-?\d+(?:\.\d+)?)\s+slack\s*\((?:VIOLATED|MET)\)',block)
    if not sl:sl=re.search(r'slack\s*\((?:VIOLATED|MET)\)\s+(-?\d+(?:\.\d+)?)',block)
    assert sl, 'Targeted full path has no parseable slack'
    count+=1;best.append({'startpoint':start[1],'endpoint':end[1],'slack_report_units':float(sl[1]),'path':block})
    best.sort(key=lambda x:x['slack_report_units']);best=best[:3]
   block=[]
   for line in (raw.decode('utf-8') for raw in tar.extractfile(member)):
    if line.startswith('Startpoint:'):
     consume(''.join(block));block=[]
    block.append(line)
   consume(''.join(block))
   rows.append({'report':n,'paths_seen':blocks_seen,'matching_paths':count,'worst_matching_paths':best})
assert inventory, 'No full timing reports found in native archive'
r={'source_run':43505737740,'native_artifact':14088684253,'native_archive_sha256':digest,'reports':rows,'inventory':inventory,'scope':'Exact RX bank6 A_ADDR6 endpoint in existing full corner reports; absence still does not establish a safe timing margin. Any ECO requires fresh routing and all-corner STA.','production_accepted':False}
pathlib.Path('out').mkdir();pathlib.Path('out/ethernet-full-path-budget.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'reports':len(rows),'matching_paths':sum(x['matching_paths'] for x in rows)}))
