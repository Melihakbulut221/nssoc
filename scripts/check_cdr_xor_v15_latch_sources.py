#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 d=json.loads((ROOT/'scripts/cdr-xor-v15-latch-source-delta.json').read_text())
 raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
 text=raw.decode()
 for e in d['edits']:
  assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
 actual=(ROOT/d['candidate_path']).read_bytes()
 assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
 print('PASS_ORIGINAL_SAMPLER_HBT_WAVE_AND_PHYSICAL_BINDING_REPLAY_RETAINED')
if __name__=='__main__':check()
