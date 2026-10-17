#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare a source-pinned, Boolean-equivalent NPU initialization experiment.

The mapped refractory bit-zero data cone implements
  F = ~((a | b) & ~(a & c & d)).
Factoring it as a native mux, a ? (c & d) : ~b, preserves every binary
assignment. It also avoids reconvergent X pessimism when b=0 and c=d=1:
both mux data inputs are then 1, independently of the unknown stored data a.
No memory, reset, clock, firmware, observation, or simulator model is changed.
This is an experimental mapped-netlist ECO, not an accepted chip repair.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

SOURCE_SHA = 'ff0fa54dac1855c21c43e3c463042ff21eefa3be65f8481ba79701742c5f796c'
OLD = '''  sg13g2_o21ai_1 _103492_ (
    .A1(_026035_),
    .A2(_043474_),
    .B1(_043518_),
    .Y(_043519_)
  );'''
PREDECESSOR = '''  sg13g2_nand3_1 _103491_ (
    .A(_026035_),
    .B(_032758_),
    .C(_043517_),
    .Y(_043518_)
  );'''
NEW = '''  wire nssoc_npu_init_b_n;
  wire nssoc_npu_init_cd;
  sg13g2_inv_1 nssoc_npu_init_invert (
    .A(_043474_), .Y(nssoc_npu_init_b_n)
  );
  sg13g2_and2_1 nssoc_npu_init_product (
    .A(_032758_), .B(_043517_), .X(nssoc_npu_init_cd)
  );
  sg13g2_mux2_1 _103492_ (
    .A0(nssoc_npu_init_b_n),
    .A1(nssoc_npu_init_cd),
    .S(_026035_),
    .X(_043519_)
  );'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def binary_truth_table():
    rows = []
    for a, b, c, d in itertools.product((0, 1), repeat=4):
        original = 1 ^ ((a | b) & (1 ^ (a & c & d)))
        factored = (c & d) if a else (1 ^ b)
        assert original == factored
        rows.append(dict(inputs=[a, b, c, d], original=original, factored=factored))
    return rows


def prepare(data):
    if digest(data) != SOURCE_SHA:
        raise ValueError('Exact rejected timing-candidate input differs')
    text = data.decode()
    if text.count(OLD) != 1 or text.count(PREDECESSOR) != 1 or 'nssoc_npu_init_' in text:
        raise ValueError('Native reconvergent gate binding differs')
    candidate = text.replace(OLD, NEW)
    if candidate.replace(NEW, OLD) != text:
        raise ValueError('ECO changed text outside the one exact gate')
    binary_truth_table()
    return candidate.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    candidate = prepare(data)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'soc_top.netlist.v').write_bytes(candidate)
    row = dict(status='SOURCE_PREPARED_NATIVE_CONTROLS_AND_FULL_BOOT_REQUIRED', source=str(args.source),
        source_sha256=digest(data), candidate_sha256=digest(candidate), original_gate=OLD,
        retained_predecessor=PREDECESSOR, replacement=NEW, all_binary_assignments=binary_truth_table(),
        other_text_unchanged=True, sequential_cells_unchanged=True, simulator_models_unchanged=True,
        candidate_adopted=False, full_soc_functional_accepted=False, timing_accepted=False,
        scope=__doc__)
    (args.output / 'source-receipt.json').write_text(json.dumps(row, indent=2) + '\n')


if __name__ == '__main__':
    main()
