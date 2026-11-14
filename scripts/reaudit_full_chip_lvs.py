# SPDX-License-Identifier: Apache-2.0
"""Reaudit unchanged completed LVS database; never rerun or modify extraction."""
import pathlib,json,hashlib,zipfile,tarfile,io,subprocess,sys,runpy,copy
P=pathlib.Path;out=P('out');out.mkdir();derived=out/'derived';derived.mkdir()
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assess=runpy.run_path('hw/soc/flow/audit_klayout_lvs.py')['assess']
base=[{'layout':'soc_top','schematic':'SOC_TOP','status':'Match','layout_devices_recursive':10,'schematic_devices_recursive':10}]
controls=[]
for verdict in ['INFO : Congratulations! Netlists match.','INFO : Netlists match.']:
 for prefix in ['', '2026-11-14 14:28:43 +0000: Memory Usage (4512444K) : ']:
  log=prefix+verdict
  cases=[('identity',base,log,[],True),('empty',[],log,[],False),('absent_verdict',base,'',[],False),('truncated_verdict',base,log[:-1],[],False),('contradictory_verdict',base,log+"\nERROR : Netlists don't match",[],False),('must_connect',base,log,[{'severity':'Info','category':'must-connect'}],False),('warning',base,log,[{'severity':'Warning','category':'extract'}],False)]
  for status in ['NoMatch','Skipped','MatchWithWarning']:
   row=copy.deepcopy(base);row[0]['status']=status;cases.append((status,row,log,[],False))
  for label,rows,text,diagnostics,want in cases:
   result=assess(rows,'soc_top',text,diagnostics);actual=not result['reasons'];assert actual==want,(label,verdict,result)
   controls.append({'label':label,'verdict':verdict,'timestamped':bool(prefix),'accepted':actual,'expected':want})
(derived/'verdict-controls.json').write_text(json.dumps({'status':'PASS','cases':controls},indent=2))
assert sha('native.zip')=='fd250afa9a2c55ef266149c583d76256dd8dcdd9d5f043cfd892a7043e15979b'
with zipfile.ZipFile('native.zip') as z:
 assert z.namelist()==['full-chip-lvs-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read(z.namelist()[0])),mode='r:gz') as t:
  for m in t.getmembers():assert not P(m.name).is_absolute() and '..' not in P(m.name).parts and (m.isfile() or m.isdir())
  t.extractall(out,filter='data')
assert sha('previous-derived.zip')=='2bb376f7b18c99c01e9ad1deab66f49ad27ba112416c0bcf3de0faf82971b698'
with zipfile.ZipFile('previous-derived.zip') as z:
 original=json.loads(z.read('derived/full-chip-result.json'));native=json.loads(z.read('derived/native-compare-result.json'));normal=json.loads(z.read('derived/full-chip-normalization.json'));old_audit=json.loads(z.read('derived/full-chip-audit.json'))
assert original['native_returncode']==0 and native['native_compare_passed'] is True
assert old_audit['reasons']==['Missing explicit successful deck verdict'] and old_audit['circuit_status_counts']=={'Match':108} and not old_audit['extraction_diagnostics']
report=out/'native/full-chip.lvsdb';log=out/'native/full-chip-deck.log'
assert sha(report)=='3ddd851b8f0d80050bc97aabb6576836eb1d20ef41d0184c239f7840b479ca22'
assert sha(log)=='53f82704bcd70166dd6d978a6bddf4611a5a9726626e62538cc39e4033e150e1'
with (derived/'audit.log').open('w') as f:r=subprocess.run([sys.executable,'hw/soc/flow/audit_klayout_lvs.py',str(report),'--top','soc_top','--deck-log',str(log),'--output',str(derived/'audit.json')],stdout=f,stderr=subprocess.STDOUT,timeout=600)
assert r.returncode==0
result=json.loads((derived/'audit.json').read_text());assert result['status']=='PASS within comparison scope' and not result['reasons'] and result['circuit_status_counts']=={'Match':108} and not result['extraction_diagnostics']
assert result['circuits']==old_audit['circuits']
assert sha(report)=='3ddd851b8f0d80050bc97aabb6576836eb1d20ef41d0184c239f7840b479ca22' and sha(log)=='53f82704bcd70166dd6d978a6bddf4611a5a9726626e62538cc39e4033e150e1'
(derived/'normalization.json').write_text(json.dumps(normal,indent=2))
(derived/'result.json').write_text(json.dumps({'status':'FULL_CHIP_ENGINEERING_LVS_AUDIT_PASSED','original_run':43602758557,'original_native_returncode':0,'native_compare_and_missing_ports_passed':True,'all_circuit_pairs_match':108,'extraction_diagnostics':[],'report_and_log_byte_unchanged':True,'audit_returncode':r.returncode,'layout_sha256':original['layout_sha256'],'reference_sha256':original['reference_sha256'],'full_chip_lvs_passed':True,'manufacturing_approval':False,'scope':'Exact prior packet-interface chip layout, complete engineering SRAM transistor interiors. Not final diode-legalized route, serial PHY, padframe, final timing or foundry approval.'},indent=2))
