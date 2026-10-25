#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify only declared geometry constants differ; execute on GitHub only."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    s=json.loads((ROOT/'scripts/cdr-sampler-compact-v1-delta.json').read_text())
    def read(name,key):
        text=(ROOT/s[name]).read_text()
        assert hashlib.sha256(text.encode()).hexdigest()==s[key]
        return text
    b=read('baseline_generator','baseline_sha256')
    for d in s['exact_replacements']:
        assert b.count(d['before'])==1
        b=b.replace(d['before'],d['after'])
    assert b==read('candidate_generator','candidate_sha256')
    b=read('baseline_checker','baseline_checker_sha256')
    old='from make_pcie_sampler_cell import CIRCUIT, CIRCUIT_SHA256, PORTS, TOP, physical_reference, use_direction'
    new=old.replace('make_pcie_sampler_cell','make_pcie_sampler_compact_v1')
    assert b.count(old)==1 and b.replace(old,new)==read('candidate_checker','candidate_checker_sha256')
    print('PASS_DECLARED_GEOMETRY_CHANGES_ONLY_ALL_ORIGINAL_PHYSICAL_GATES')
if __name__=='__main__':main()
