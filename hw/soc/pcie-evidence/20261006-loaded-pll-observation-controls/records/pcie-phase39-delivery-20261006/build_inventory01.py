# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Copy closed570 text evidence only; preserve archive-only binary/upstream mappings."""
import hashlib,json,re
from pathlib import Path
R=Path.cwd();O=R/'hw/soc/out';B=Path(__file__).resolve().parent
F=O/'pcie-tail115-connected570-controls-finite-20261006'
P=O/'pcie-570-finite-peer-root-20261006'
C=R/'hw/soc/pcie-evidence/20261006-loaded-pll-observation-controls'

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,w):
 assert pin(p)=={k:w[k]for k in('bytes','sha256')},str(p)
def read(p):return json.loads(Path(p).read_text())
def license_for(p):
 # Upstream is never copied; licence statements inside data/JSON do not relabel evidence.
 assert 'upstream-source01' not in p.parts
 if p.suffix in ('.py','.sh') or p.name=='spinit' or p.name.startswith('Makefile'):return 'Apache-2.0'
 if p.suffix in ('.spice','.cir','.v','.vh','.sv','.sdc','.tcl','.ys'):return 'CERN-OHL-W-2.0'
 return 'CC-BY-4.0'
def main():
 j=read(F/'ready-finite02.json');root=read(P/'result01.json')
 assert root['status']=='PASS_INDEPENDENT570_FINITE_SAVED_REVIEW' and root['findings']==[]
 exact(F/'ready-finite02.json',root['ready'])
 assert len(root['checked_inputs'])==841
 for p,w in root['checked_inputs'].items():exact(p,w)
 scope_peer=read(B/'doc150-scope-peer-vco01.json')
 assert scope_peer['status']=='PASS_INDEPENDENT_DOC150_NARRATIVE_SCOPE' and scope_peer['findings']==[]
 exact(R/'docs/150-pcie-loaded-pll-observation-controls.md',scope_peer['doc'])
 assert j['status']=='READY_FINITE570_SOURCE_AND_CONTROL_EVIDENCE_PUBLIC' and not j['sources']
 assert j['active_native_excluded'] and not j['physics_acceptance'] and not j['polarity_selected']
 assert j['current_control_cases']==dict(inherited_finite=11,inherited_storage=23,inherited_lifecycle=7,new_actual_command_and_observation=8,total=49)
 assert root['current_controls_total']==49 and root['composition_controls_separate']==12 and root['positive_rows']==19 and root['positive_native_duration_ps']==2
 assert len(root['closed_transports'])==5 and len(root['roundtrips'])==2
 assert root['full34ns_failure_retained'] and not root['full34ns_physics_acceptance']
 assert len(j['archives'])==len(j['assets'])==1 and j['all_archive_members']==root['members']==380
 archive=j['archives'][0];asset=j['assets'][0]
 exact(archive['path'],archive);exact(archive['manifest'],archive['manifest_pin'])
 assert root['archive']==archive and asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
 assert asset['name']==Path(archive['path']).name and asset['sha256']==archive['sha256'] and asset['bytes']==archive['bytes']
 members=read(archive['manifest']);assert len(members)==380
 for k in ('method_allowlist','compact_evidence','original_evidence','public_receipts'):
  for p,w in j[k].items():exact(p,w)
 assert len(j['method_allowlist'])==82 and len(j['compact_evidence'])==418
 selected={};excluded={};compact_base=F/'compact-evidence/hw/soc/out'
 for source,w in j['compact_evidence'].items():
  p=Path(source);rel=str(p.relative_to(F))
  forbidden=p.suffix in ('.gz','.raw','.bin','.xz') or 'upstream-source01' in p.parts
  if not forbidden:
   try:p.read_text(encoding='utf-8')
   except UnicodeDecodeError:forbidden=True
  if forbidden:
   assert rel in members and members[rel]==w,('excluded_not_in_public_capsule',source)
   excluded[source]=dict(**w,reason='Upstream source and original licence retained only in capsule' if 'upstream-source01' in p.parts else 'Binary/raw/compressed fixture retained only in capsule',
       archive_member=rel,archive_sha256=archive['sha256'],public_asset=asset['url'],asset_id=asset['asset_id'])
   continue
  assert 'native03' not in p.parts,('mutable_native03_forbidden',source)
  target=Path('records')/(p.relative_to(compact_base) if p.is_relative_to(compact_base) else Path(F.name)/p.relative_to(F))
  assert str(target) not in selected,('destination_collision',target)
  selected[str(target)]=(p,w)
 # Root's failed readers01/02 and corrected03 + complete saved outcome remain explicit.
 extras=[F/'ready-finite02.json',*sorted(p for p in P.iterdir() if p.is_file()),*sorted(p for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts)]
 for p in extras:
  target=Path('records')/p.relative_to(O)
  assert str(target) not in selected
  selected[str(target)]=(p,pin(p))
 assert {p.name for p in P.iterdir() if p.is_file()}=={'review01.py','review01.log','review02.py','review02.log','review03.py','review03.log','result01.json'}
 assert not C.exists();C.mkdir(parents=True)
 files={};sidecars=[]
 for relative,(p,w) in sorted(selected.items()):
  exact(p,w);target=C/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());exact(target,w)
  licence=license_for(p)
  if p.suffix in ('.py','.spice','.v','.vh','.sv','.sh','.tcl','.ys'):
   declared=re.findall(r'SPDX-License-Identifier: ([^\r\n]+)',p.read_text()[:700])
   assert not declared or declared[0].strip()==licence,('immutable_source_licence_mismatch',str(p),declared,licence)
  files[relative]=dict(source=str(p.relative_to(R)),**w,licence=licence)
  side=Path(str(target)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+licence+'\n');sidecars.append(str(side.relative_to(C)))
 data=dict(status='PASS_FINITE570_CAPTURE_CONTROLS_DELIVERY',sources={},methods=j['method_allowlist'],files=files,sidecars=sidecars,
   public_only_files=excluded,archives=j['archives'],public_assets=j['assets'],members=380,
   current_controls=j['current_control_cases'],source_composition_controls_separate=12,positive_native_duration_ps=2,positive_rows=19,
   independent_root_peer=dict(path=str((P/'result01.json').relative_to(R)),**pin(P/'result01.json'),verified_bound_paths=841,closed_transports=5,full_saved_readbacks=2),
   pending_flag_resolution='Original ready-finite02 independent_saved_peer_pending=true is historical. Bound completed root result01 resolves the review; original bytes remain unchanged.',
   immutable_compact_records_requested=418,compact_records_copied=len(j['compact_evidence'])-len(excluded),public_only_records=len(excluded),
   binary_and_upstream_omitted_from_git=True,upstream_original_licences_preserved_in_public_capsule=True,
   historical_failures_retained=True,active_native03_outputs_excluded=True,active_journals_excluded=True,
   physics_acceptance=False,polarity_selected=False,full34ns_acceptance=False,full_phy_acceptance=False,production_acceptance=False)
 inventory=C/'delivery-inventory.json';inventory.write_text(json.dumps(data,indent=2)+'\n')
 Path(str(inventory)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
 (B/'source-allowlist.json').write_text('{}\n')
 (B/'method-allowlist.json').write_text(json.dumps(j['method_allowlist'],indent=2)+'\n')
 (B/'public-only-allowlist.json').write_text(json.dumps(excluded,indent=2)+'\n')
 evidence={str(p.relative_to(R)):pin(p)for p in C.rglob('*')if p.is_file()}
 (B/'evidence-allowlist.json').write_text(json.dumps(evidence,indent=2)+'\n')
 record=dict(status='LOCAL_PHASE39_FINITE_DELIVERY_READY_FOR_ROOT_CHECKS',inventory=dict(path=str(inventory.relative_to(R)),**pin(inventory)),
  product_sources=0,captured_methods=82,compact_records=len(files),ready_compact_copied=data['compact_records_copied'],archive_only_records=len(excluded),
  sidecars=len(sidecars)+1,total_delivery_files=len(evidence),archives=1,archive_members=380,public_assets=1,current_controls=49,separate_composition_controls=12,
  no_git_operations=True,no_new_native_or_network=True,document=dict(path='docs/150-pcie-loaded-pll-observation-controls.md',**pin(R/'docs/150-pcie-loaded-pll-observation-controls.md')))
 (B/'delivery-ready01.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record))
if __name__=='__main__':main()
