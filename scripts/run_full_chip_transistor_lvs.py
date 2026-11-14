# SPDX-License-Identifier: Apache-2.0
"""Run full transistor chip LVS with proven SRAM hierarchy normalization."""
import pathlib,hashlib,json,zipfile,tarfile,subprocess,os,io,time,sys
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);derived=out/'derived';derived.mkdir(exist_ok=True)
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def restore(archive,expected,inner,dest):
 assert sha(archive)==expected
 with zipfile.ZipFile(archive) as z:
  assert z.namelist()==[inner]
  with tarfile.open(fileobj=io.BytesIO(z.read(inner)),mode='r:gz') as t:
   for m in t.getmembers():assert not P(m.name).is_absolute() and '..' not in P(m.name).parts and (m.isfile() or m.isdir())
   t.extractall(dest,filter='data')
restore('macro.zip','1b536d31758f4abf1fb7af4700a59fd64d891e41044ec1f1230da02b84a324c1','namespaced-native.tgz',out)
restore('reference.zip','894aa48ad4ee2c0f6e43724f1a88f20b278128e49d27b3584148759317c5c0b9','streamout-native.tgz',P('.'))
restore('layout.zip','bb1421b73653582fb56f11abedf90d66153e4d5919ef761a1d8a685b12d08d31','streamout-native.tgz',P('.'))
assert sha('/usr/bin/klayout')=='288ed7a513436fac79255686914ff71b1d351fd79bd98f2eb6f9fecd14e149f7'
ref=P('hw/soc/out/namespaced-streamout/pinmap-native/soc_top-full-transistor.cdl').resolve()
layout=P('hw/soc/out/namespaced-streamout/run/1-nssoc-namespacedsramstreamout/soc_top.klayout.gds').resolve()
assert sha(ref)=='523438b6014557b86ee7d438f95ddbfaabb76f390265283fcb844c233fcb8aa4'
assert sha(layout)=='c6c7df7f7fe7d23c03847ffa49bb547423ff89b7dc9266a47effa495efea077d'
cmd=json.loads((out/'native/effective-command.json').read_text());assert cmd[:4]==['/usr/bin/klayout','-b','-zz','-r']
deck=P(cmd[4]);assert deck.is_relative_to(P.cwd()/'out/native') and deck.is_file()
text=deck.read_text();assert hashlib.sha256(text.encode()).hexdigest()=='b3118b51496453219f9d2e6f9fed5d896c0a7e3fb40fc39e03c398f4bb9389ec'
assert sha('sources.zip')=='a5738706249770973fe0edb52578c5e04be8240c51c664b244a3f6c3a36eb8f5'
anchor='# === Aligns the extracted netlist vs. the schematic ===';assert text.count(anchor)==1
with zipfile.ZipFile('sources.zip') as z:
 dp=z.read('dp-lvs-deck-source.txt').decode();sp=z.read('sp-lvs-deck-source.txt').decode()
 assert dp==text and sp.count(anchor)==1 and dp.split(anchor)[0]==sp.split(anchor)[0]
prefix=text.split(anchor)[0];deck.write_text(prefix+P('scripts/full_chip_transistor_compare.rb').read_text())
values={'input':str(layout),'schematic':str(ref),'topcell':'soc_top','report':str((out/'native/full-chip.lvsdb').resolve()),'log':str((out/'native/full-chip-deck.log').resolve()),'target_netlist':str((out/'native/full-chip-extracted.cir').resolve())}
for key,value in values.items():
 hits=[i for i,v in enumerate(cmd) if v.startswith(key+'=')];assert len(hits)==1;cmd[hits[0]]=key+'='+value
r={'status':'RUNNING','command':cmd,'reference_sha256':sha(ref),'layout_sha256':sha(layout),'deck_sha256':sha(deck),'shared_extraction_prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Prior failed-timing route, full transistor engineering SRAM reference. No final serial PHY or manufacturing acceptance.'}
(derived/'full-chip-command.json').write_text(json.dumps(r,indent=2));env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None);rc=2;start=time.monotonic()
try:
 with (out/'native/full-chip-run.log').open('w') as log:proc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=18000)
 r['native_returncode']=proc.returncode;assert proc.returncode==0
 audit=[sys.executable,'hw/soc/flow/audit_klayout_lvs.py',values['report'],'--top','soc_top','--deck-log',values['log'],'--output',str(derived/'full-chip-audit.json')]
 with (derived/'audit.log').open('w') as log:a=subprocess.run(audit,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 r['audit_returncode']=a.returncode;report=json.loads((derived/'full-chip-audit.json').read_text());native=json.loads((derived/'native-compare-result.json').read_text())
 assert a.returncode==0 and report['status']=='PASS within comparison scope' and not report['reasons'] and native['native_compare_passed']
 r['full_chip_lvs_passed']=True;r['status']='FULL_CHIP_ENGINEERING_LVS_PASSED';rc=0
except Exception as e:r['status']='FAILED_OR_INCOMPLETE';r['error']=type(e).__name__+': '+str(e)
finally:
 r['elapsed_seconds']=time.monotonic()-start;r['log_tail']={p.name:p.read_text(errors='replace').splitlines()[-100:] for p in [out/'native/full-chip-run.log',out/'native/full-chip-deck.log'] if p.is_file()}
 (derived/'full-chip-result.json').write_text(json.dumps(r,indent=2));sys.exit(rc)
