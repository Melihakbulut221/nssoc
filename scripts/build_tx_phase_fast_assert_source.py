#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measured-reset-latency candidate; actual passive AND fan-in, no electrical claim."""
import hashlib
from pathlib import Path
from build_tx_phase_async_preset_source import definitions,NAMES
ROOT=Path(__file__).resolve().parents[1]
BASE='hw/soc/analog/pcie/clock_div2_async_preset_firstfall_v2.spice'
BASE_SHA='2ce563119aedf629608b2c66a1f605f719f7a58765af77a965ae0a7e4598e4e6'
OUTPUT='hw/soc/analog/pcie/clock_div2_fast_assert_firstfall_v3.spice'
AND='nssoc_phase_arm_release_level_v3'
OLD='XRUN releasedp releasedn runp runn DIV_AVDD AVSS SUB '+NAMES['level']
NEW='XRUN releasedp releasedn ARM_P ARM_N runp runn DIV_AVDD AVSS SUB '+AND
EXTRA=[
 'XARM_P armp bip sub rppd w=2u l=3.6u b=0 sw_et=1',
 'XARM_N armn bin sub rppd w=2u l=3.6u b=0 sw_et=1',
 'XAND_SKEW bip avss sub rppd w=1u l=32u b=0 sw_et=1']
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def addition(base):
    d=definitions(base)[NAMES['level']]
    assert d['ports']==['ip','in','cp','cn','avdd','avss','sub']
    cards=[' '.join(r)for r in d['cards']]
    return ('* Real-device fast assertion candidate: ARM and release must both be positive.\n'
      '* Extra positive-base shunt gives the passive fan-in a negative decision offset.\n'
      '* Geometry-only nominal algebra is not loaded transistor or corner qualification.\n'
      '.subckt '+AND+' ip in armp armn cp cn avdd avss sub\n'+
      '\n'.join(cards+EXTRA)+'\n.ends '+AND+'\n')
def build(base=None):
    if base is None:base=(ROOT/BASE).read_text()
    assert digest(base)==BASE_SHA and base.count(OLD)==2
    return base.replace(OLD,NEW)+'\n'+addition(base)
if __name__=='__main__':print(build(),end='')
