# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify all local delivery bytes and exact archive-only exclusions; no EDA/network."""
import hashlib,json
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;C=R/'hw/soc/pcie-evidence/20261006-loaded-pll-observation-controls'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def main():
 j=read(C/'delivery-inventory.json');seen=set()
 for rel,w in j['files'].items():
  p=C/rel;assert pin(p)=={k:w[k]for k in('bytes','sha256')};assert pin(R/w['source'])==pin(p)
  assert p.suffix not in ('.gz','.raw','.bin','.xz') and 'upstream-source01' not in p.parts
  p.read_text(encoding='utf-8');seen.add(rel)
 for rel in j['sidecars']:
  p=C/rel;assert p.read_text().startswith('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: ');seen.add(rel)
 seen.update(['delivery-inventory.json','delivery-inventory.json.license'])
 assert seen=={str(p.relative_to(C))for p in C.rglob('*')if p.is_file()}
 archive=j['archives'][0];members=read(archive['manifest']);asset=j['public_assets'][0]
 for source,w in j['public_only_files'].items():
  assert pin(source)=={k:w[k]for k in ('bytes','sha256')}==members[w['archive_member']]
  assert w['archive_sha256']==archive['sha256'] and w['public_asset']==asset['url'] and w['asset_id']==asset['asset_id']
 assert j['current_controls']['total']==49 and j['source_composition_controls_separate']==12
 assert j['positive_native_duration_ps']==2 and j['positive_rows']==19 and not j['full34ns_acceptance'] and not j['physics_acceptance']
 for file in ('README.md','docs/00-index.md'):
  assert '150-pcie-loaded-pll-observation-controls.md' in (R/file).read_text()
 doc=R/'docs/150-pcie-loaded-pll-observation-controls.md';text=doc.read_text()
 assert '**49 current' in text and '**2 ps and produces 19 rows**' in text and 'without rerunning the oversized command' in text
 result=dict(status='PASS_LOCAL_PHASE39_DELIVERY_BYTES_SCOPE_AND_PUBLIC_ONLY_MAPPING',files=len(seen),records=len(j['files']),archive_only=len(j['public_only_files']),members=j['members'],assets=len(j['public_assets']),method=pin(__file__),inventory=pin(C/'delivery-inventory.json'),document=pin(doc),no_native_or_network=True,no_git_operations=True)
 (B/'inventory-verification01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
