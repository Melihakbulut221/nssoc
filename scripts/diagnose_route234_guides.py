#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only source-bound diagnosis of the actual rejected GRT guide file."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_branch_hold_eco import guide_blocks
OUT=Path('cloud-route234-guide-diagnosis').resolve()
assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT.mkdir();reports.OUT=OUT
r,proof=reports.restore_report('route234-sized-eco',38924027432,'7b67e9e558aebb4865d0ed086b07793d3e88e5f617f3b488b9c55af430f44c47','925f8a7ed8bcb34937e58fb4568571c18442f837645f749ec6a61b6bd52b28d7',OUT/'source',('changed.guide','parent/candidate.guide','geometry-proof.json','guide-input-proof.json','selected-guides.log'))
assert r['status']=='FAIL_OR_ERROR'and r['guide_input']['status']=='PASS_EXACT_23_SIGNAL_WIRES_REMOVED_ONLY_FROM_GUIDE_COPY'
selected=set(r['geometry']['selected_nets']);assert len(selected)==23
new=guide_blocks((OUT/'source/changed.guide').read_text());old=guide_blocks((OUT/'source/parent/candidate.guide').read_text())
extra=set(new)-selected;missing=selected-set(new)
result=dict(status='COMPLETE_REJECTED_GUIDE_DIAGNOSIS_NOT_ROUTE_ACCEPTANCE',accepted=False,source=proof,selected_count=len(selected),actual_guide_count=len(new),parent_guide_count=len(old),missing=sorted(missing),extra_count=len(extra),extra_sample=sorted(extra)[:30],extra_equal_parent=sum(n in old and new[n]==old[n]for n in extra),extra_different_parent=[n for n in sorted(extra)if n not in old or new[n]!=old[n]][:50],selected_same_parent=sorted(n for n in selected&set(new)&set(old)if new[n]==old[n]),selected_raw_blocks={n:new[n]for n in sorted(selected&set(new))},first_raw_lines=(OUT/'source/changed.guide').read_text().splitlines()[:30])
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
