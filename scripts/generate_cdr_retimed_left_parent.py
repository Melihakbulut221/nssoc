#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reassemble the frozen full PD with four verified left-output sampler leaves.

All original supply-riser geometry construction and checks are retained. Parent
placement/routes are freshly generated for the new real child ports and bounds.
"""
import argparse,hashlib
from pathlib import Path
import generate_cdr_retimed_risers_parent as original
import cdr_retimed_left_parent_plan as plan
TOP='nssoc_cdr_pd394_left_outputs_v1'
def generate(out):
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()=='66524d4eafb105a1a7f1a0a956ccfe34b9ffe494d20a3facf6a1501b51f7a750'
    original.plan=plan;original.TYPES=plan.TYPES;original.TOP=TOP
    original.base.TOP='nssoc_cdr_pd394_left_outputs_base_v1'
    original.generate(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
