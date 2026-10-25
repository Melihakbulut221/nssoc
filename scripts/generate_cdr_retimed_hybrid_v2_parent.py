#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use the proven actual supply-riser construction with new hybrid420 leaves."""
import argparse,hashlib,json
from pathlib import Path
import generate_cdr_retimed_hybrid_v2_risers as original
import generate_cdr_retimed_hybrid_v2_base as base
import cdr_retimed_hybrid_v2_parent_plan as plan
from check_cdr_hybrid_v2_parent_sources import check
TOP='nssoc_cdr_pd420_hybrid_tail_v2'
def generate(out):
    check()
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()=='8a20854668fa808ef80cc599e43f767bae85c10ad24753ae043411886bf0e6b6'
    assert hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()=='c63fd6f5c37e927cdb26f29d4b7786bb0ebdbeaeb9f63c1ac09124d13eb113e9'
    original.base=base;original.plan=plan;original.TYPES=plan.TYPES;original.TOP=TOP
    original.generate(out)
    p=out/'layout/result.json';d=json.loads(p.read_text())
    assert d['primitive_census']==plan.build()['primitive_census']
    assert sum(d['primitive_census'].values())==420
    d['status']='GENERATED_HYBRID420_REQUIRES_NATIVE_PHYSICAL_AND_FULL_RC'
    d['inputs'][str(Path(__file__).resolve())]=base.sha(Path(__file__).resolve())
    p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
