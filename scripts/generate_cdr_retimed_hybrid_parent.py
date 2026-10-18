#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use the proven actual supply-riser construction with new hybrid406 leaves."""
import argparse,hashlib,json
from pathlib import Path
import generate_cdr_retimed_risers_parent as original
import generate_cdr_retimed_hybrid_base as base
import cdr_retimed_hybrid_parent_plan as plan
from check_cdr_hybrid_parent_sources import check
TOP='nssoc_cdr_pd406_hybrid_tail_v1'
def generate(out):
    check()
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()=='66524d4eafb105a1a7f1a0a956ccfe34b9ffe494d20a3facf6a1501b51f7a750'
    assert hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()=='39e6d0346d896a93b3cea6570ff8a63bf0ce7c911c510abc4f52bc4885535b4f'
    original.base=base;original.plan=plan;original.TYPES=plan.TYPES;original.TOP=TOP
    original.generate(out)
    p=out/'layout/result.json';d=json.loads(p.read_text())
    assert d['primitive_census']==plan.build()['primitive_census']
    assert sum(d['primitive_census'].values())==406
    d['status']='GENERATED_HYBRID406_REQUIRES_NATIVE_PHYSICAL_AND_FULL_RC'
    d['inputs'][str(Path(__file__).resolve())]=base.sha(Path(__file__).resolve())
    p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
