#!/usr/bin/env python3
"""Parser controls only; current routed OpenDB classification is still required."""
import hashlib,json,py_compile
from pathlib import Path
from audit_core_only_route_annotation import drivers,controls,name_controls
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'hw/soc/out/core-only-annotation-controls'
out.mkdir(parents=True,exist_ok=False)
paths=['scripts/audit_core_only_route_annotation.py','scripts/cloud_core_only_routed_extraction.py',
       'scripts/cloud_core_only_routed_boot.py']
for p in paths:py_compile.compile(str(ROOT/p),doraise=True)
valid='Found 0 unannotated drivers.\nFound 0 partially unannotated drivers.'
assert drivers(valid)==[]
try:drivers(valid+'\n'+valid)
except AssertionError:pass
else:raise AssertionError('Ambiguous annotation sections accepted')
r=dict(status='PASS_ANNOTATION_PARSER_CONTROLS_NOT_NATIVE_DATABASE_AUDIT',
       annotation=controls(),names=name_controls(),zero_driver_case=True,
       duplicate_section_rejected=True,accepted=False,native_database_executed=False,
       sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
