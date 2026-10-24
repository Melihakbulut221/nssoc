#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One physical resistor sizing candidate after exact244 waveform diagnosis."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='hw/soc/analog/pcie/clock_div2_fast_assert_firstfall_v3.spice'
BASE_SHA='78f3413256b2b2769cebbcda3319762f5ff8a769f8bafd4246bec040de519130'
OUTPUT='hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice'
OLD='XAND_SKEW bip avss sub rppd w=1u l=32u b=0 sw_et=1'
NEW='XAND_SKEW bip avss sub rppd w=1u l=20u b=0 sw_et=1'
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def build(base=None):
    if base is None:base=(ROOT/BASE).read_text()
    assert digest(base)==BASE_SHA and base.splitlines().count(OLD)==1
    return base.replace(OLD,NEW,1)
def recover(text):
    assert text.splitlines().count(NEW)==1 and OLD not in text
    recovered=text.replace(NEW,OLD,1)
    assert digest(recovered)==BASE_SHA,'Source changed outside the single physical offset resistor'
    return recovered
if __name__=='__main__':print(build(),end='')
