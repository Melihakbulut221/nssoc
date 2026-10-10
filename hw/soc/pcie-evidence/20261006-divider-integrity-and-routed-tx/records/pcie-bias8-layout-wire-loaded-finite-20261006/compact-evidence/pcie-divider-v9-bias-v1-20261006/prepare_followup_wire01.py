"""Drafting is gated on completed fresh physical validation and its saved peer."""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;R=P.parents[3];OLD=P.with_name('pcie-divider-v8-cap-v1-wire-v1-20261006');B=P.with_name('pcie-divider-v9-bias-v1-wire-v1-20261006');G=Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01');C=Path('/dev/shm/nssoc-div4-v9-bias-v1-checks-01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert not B.exists()
c=json.loads((C/'result.json').read_text());assert c['status']=='PASS_DIV4_V9_BIAS_V1_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY' and len(c['steps'])==21
assert c['outputs']=={n:pin(C/n)['sha256']for n in c['outputs']}
peer=json.loads((P/'native-saved-peer-rx.json').read_text());assert peer['status']=='PASS_INDEPENDENT_SAVED_BIAS8_V1_NATIVE_RESULT' and not peer['findings']
assert peer['checks']==pin(C/'result.json') and peer['geometry']==pin(C/'power-geometry.json') and peer['GDS']==pin(G/'nssoc_clock_div4_v9_bias_v1_layout.gds')
assert len(c['power_geometry_audit']['controls'])==8
oldf=json.loads((OLD/'geometry-source-freeze.json').read_text());assert oldf['inputs']=={p:pin(p)for p in oldf['inputs']}
B.mkdir()
replacements=[('v8-cap-v1','v9-bias-v1'),('v8_cap_v1','v9_bias_v1'),('V8_CAP_V1','V9_BIAS_V1'),('V8_CAP24','V9_BIAS8'),('CAP24_V1','BIAS8_V1'),('PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS','PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS'),('4361db967f0df1d340360f6b50461274b8a36cb49d208072a911cfd2077c78c1',pin(G/'nssoc_clock_div4_v9_bias_v1_layout.gds')['sha256'])]
bridges=[]
for name in ['run_geometry.py','probe_native_cells.py','probe_device_locations.py','probe_wire_components.py','probe_terminal_anchors.py','prepare_anchors.py','bind_source_ids.py']:
 old=OLD/name;new=B/name;s=old.read_text()
 for a,b in replacements:s=s.replace(a,b)
 new.write_text(s);a=old.read_text().splitlines(keepends=True);b=s.splitlines(keepends=True)
 ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(b[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]
 assert ''.join(x['before']for x in ops)==old.read_text() and ''.join(x['after']for x in ops)==s
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
shutil.copyfile(OLD/'native_unsimplified.lvs',B/'native_unsimplified.lvs')
(B/'source-bridge01.json').write_text(json.dumps(bridges,indent=2)+'\n')
(B/'draft-only.json').write_text(json.dumps(dict(status='PREPARED_FOR_SOURCE_FREEZE_AND_INDEPENDENT_PEER_NO_WIRE_NATIVE',preparer=pin(Path(__file__)),parent_freeze=pin(OLD/'geometry-source-freeze.json'),closed_physical=pin(C/'result.json'),closed_physical_peer=pin(P/'native-saved-peer-rx.json'),declared_delta='Only two top-level W1/L7→8 pull-downs; caps24 and89otherintrinsics retained. Seven full wire producers retain same91/283/205/37/72 schema, unsimplified extraction and lifecycle.'),indent=2)+'\n')
print(B)
