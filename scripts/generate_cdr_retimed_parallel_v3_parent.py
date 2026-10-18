#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use the proven actual supply-riser construction with new parallel484 leaves."""
import argparse,hashlib,json
from pathlib import Path
import generate_cdr_retimed_parallel_v3_risers as original
import generate_cdr_retimed_parallel_v3_base as base
import cdr_retimed_parallel_v3_parent_plan as plan
from check_cdr_parallel_v3_parent_sources import check
TOP='nssoc_cdr_pd484_parallel_tail_v2'
def generate(out):
    check()
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()=='e9c3fa6553d797fec0c216c0ae4d3e6d9d4759666a0b0e77e7160c30a5eaa116'
    assert hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()=='42e71e6995a4fbcabe4b320a0e0fca2e24c8904bfbfb2f2da7ab62c9a5f36b3e'
    original.base=base;original.plan=plan;original.TYPES=plan.TYPES;original.TOP=TOP
    original.generate(out)
    p=out/'layout/result.json';d=json.loads(p.read_text())
    assert d['primitive_census']==plan.build()['primitive_census']
    assert sum(d['primitive_census'].values())==484
    d['status']='GENERATED_PARALLEL484_REQUIRES_NATIVE_PHYSICAL_AND_FULL_RC'
    d['inputs'][str(Path(__file__).resolve())]=base.sha(Path(__file__).resolve())
    p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
