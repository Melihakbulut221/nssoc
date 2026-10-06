"""Bounded narrative review against closed receipt summaries; no archive/native read."""
from pathlib import Path
import datetime,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
doc=R/'docs/150-pcie-loaded-pll-observation-controls.md'
assert pin(doc)==dict(bytes=5036,sha256='5e04b15f66a37433bb4529c2b062b2acf40809397bcc2cff6df9c7822fc382ff')
F=R/'hw/soc/out/pcie-tail115-connected570-controls-finite-20261006'
ready=F/'ready-finite02.json';d=json.loads(ready.read_text())
assert d['current_control_cases']['total']==49 and not d['physics_acceptance'] and not d['polarity_selected']
C=R/'hw/soc/out/pcie-tail115-connected570-save-batches-20261006/native-control01/result.json'
c=json.loads(C.read_text());assert not c['full34ns_tuning_executed'] and not c['physics_acceptance']
S=R/'hw/soc/out/pcie-tail115-connected570-source-20261006/source-controls01.json'
s=json.loads(S.read_text())
text=doc.read_text()
for token in ['455-instance','115 schematic instances','102 in the phase/frequency detector',
 'ten in the charge pump','three in the loop filter','two positive cases and ten deliberate graph changes',
 '65,596-byte','1,133 requested observations','eight groups of 128 and one of 109',
 '1,134 columns','2 ps and produces 19 rows','does **not** prove','380 members',
 'not a power-loss durability','Both loop-polarity variants are preserved']:
 assert token in text,token
assert 128*8+109==1133 and 455+102+10+3==570 and 11+23+7+8==49
result=dict(status='PASS_INDEPENDENT_DOC150_NARRATIVE_SCOPE',utc=datetime.datetime.now(datetime.UTC).isoformat(),
 reviewer='vco_loaded_feedback',doc=pin(doc),method=pin(Path(__file__)),
 closed_summary_inputs={str(p):pin(p)for p in [ready,C,S]},findings=[],
 review=['49 current capture/storage/lifecycle/batch controls are separate from twelve source-composition cases.',
 'Nine save batches retain 1133 observations plus time; actual 2ps/19-row positive checks command/header/startup only.',
 'Original 65596-byte native failure is read back as the negative, not claimed to be rerun. Historical failures and source corrections remain visible.',
 '455 physical/schematic mixed chain plus 115 PFD/pump/filter elements is not fully extracted layout or qualified connected-loop operation.',
 'No 34ns tuning, electrical qualification, pump reachability, selected polarity or lock follows from this closed packet; live03 including .6V completion excluded.',
 'Captured-byte retention and close-time synchronization are explicitly narrower than power-loss durability or solver checkpoint; upstream copyright/licence preserved.'],
 scope='Narrative-only cross-check. No simulation, archive rehash, publication or source mutation; archive/member and transport census remain root independent saved-review responsibility.')
with(B/'doc150-scope-peer-vco01.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(pin(B/'doc150-scope-peer-vco01.json')))
