# SPDX-License-Identifier: Apache-2.0
"""Cloud-only nominal RC feasibility screen on the full archived DP256x16 SRAM."""
import hashlib,json,pathlib,subprocess,tarfile,time,sys
import klayout.db as db
root=pathlib.Path('native');root.mkdir(exist_ok=True)
out=pathlib.Path('out');out.mkdir(exist_ok=True)
archive=root/'physical.tar.xz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3fd7b918f112b88146b92c861d0146b4ae7404682ceab27186d4a0f95a72a275'
member='hw/soc/out/sram-closure-20260926/wide-spacing-repair-v2/DP8TSRAMDP256x16.gds'
with tarfile.open(archive,'r:xz') as tar:
 raw=tar.extractfile(member).read()
assert hashlib.sha256(raw).hexdigest()=='c6a1be71d0439e88e2c08729345eb8d8001f773266cb7a8b939446e54999ff45'
gds=root/'DP8TSRAMDP256x16.gds';gds.write_bytes(raw)
layout=db.Layout();layout.read(str(gds));cells=sorted(c.name for c in layout.each_cell())
summary=dict(source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),gds_sha256=hashlib.sha256(raw).hexdigest(),cells=cells,scope='Full-macro nominal extractor execution only. No accepted SRAM RC, capacitance conservation, independent LVS, Liberty or manufacturing acceptance.',qualified_pex=False,manufacturing_approval=False,runs=[])
(out/'summary.json').write_text(json.dumps(summary,indent=2))
candidates=[n for n in cells if n=='DP8TSRAMDP256x16']
assert len(candidates)==1,('Need unambiguous actual DP8T leaf',candidates)
cell=candidates[0];summary['cell']=cell
mode=sys.argv[1];assert mode in ['CC','RC']
for mode in [mode]:
 cmd=['kpex','extract','--pdk','ihp-sg13g2','--gds',str(gds),'--cell',cell,'--2.5D','--mode',mode,'--blackbox','n','--out-dir',str(root/mode),'--out-result',str(out/(mode+'-result.json'))]
 began=time.monotonic()
 with (out/(mode+'.log')).open('w') as log:
  try:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=17000).returncode
  except subprocess.TimeoutExpired:rc=124
 summary['runs'].append(dict(mode=mode,argv=cmd,returncode=rc,seconds=time.monotonic()-began))
 (out/'summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary['runs'][-1]),flush=True)
summary['native_outputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!='physical.tar.xz'}
(out/'summary.json').write_text(json.dumps(summary,indent=2))
raise SystemExit(0 if all(r['returncode']==0 for r in summary['runs']) else 1)
