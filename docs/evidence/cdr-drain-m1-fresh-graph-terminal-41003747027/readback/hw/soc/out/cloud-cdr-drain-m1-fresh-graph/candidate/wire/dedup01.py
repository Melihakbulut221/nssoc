# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One solver port per exact geometric point, keeping all logical terminals."""
from pathlib import Path
import json,hashlib,copy
B=Path(__file__).resolve().parent;P=B/'anchors03.json';original=json.loads(P.read_text());groups={};alias={};new=copy.deepcopy(original)
for a in original['anchors']:
 key=(a['metal'],*a['point_dbu']);groups.setdefault(key,[]).append(a)
anchors=[]
for key,items in groups.items():
 assert len({(a['wire_component'],a['native_cluster'])for a in items})==1
 a=copy.deepcopy(items[0]);a['logical_labels']=[r['label']for r in items];a['coincident_witnesses']=copy.deepcopy(items)
 for item in items:alias[item['label']]=a['label']
 anchors.append(a)
assert len(anchors)>25 and len(alias)==len(original["anchors"])
for r in new['rows']:
 if r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':r['wire_anchor']=alias[f"T{r['device']:03d}_{r['terminal']}"]
new.update(status='PASS_EXACT_PHYSICAL_POINTS_FOR_ALL_LOGICAL_REFERENCES',anchors=anchors,logical_anchor_aliases=alias,logical_anchor_count=len(alias),physical_anchor_count=len(anchors),point_quantization_used_to_merge=False)
new['inputs'][str(P)]=hashlib.sha256(P.read_bytes()).hexdigest();new['inputs'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(B/'anchors08.json').write_text(json.dumps(new,indent=2)+'\n');print(new['status'])
