#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind fresh physical retime-input routing and preserve every native extraction gate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_collector_trunks_v21_extraction_sources import check as original
 original()
 d=json.loads((ROOT/'scripts/cdr-retime-trunks-v22-extraction-source-delta.json').read_text())
 for row in d['files']:
  raw=(ROOT/row['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
  text=raw.decode();parts=[];cursor=0
  for e in row['changes']:
   assert cursor<=e['start']<=e['end']<=len(text)
   parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
  parts.append(text[cursor:]);actual=(ROOT/row['candidate_path']).read_bytes()
  assert actual==''.join(parts).encode()and hashlib.sha256(actual).hexdigest()==row['candidate_sha256']
 pin=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-parent-physical-pass-20261020.json').read_text())
 assert pin['run']==39454675485 and pin['source_head']=='41efb1baed378413a8cb49be4b8efcb82c83a5ba'
 assert pin['summary_sha256']=='0425f0b6cbfdae35240d2e99a0faea3f75b114f2e4974639d804556a36ccb266'
 assert pin['parts_sha256']=='bdf63f2c67dc97827411310b1a9d50ccd81855b1aa4d686ce94c81e98747aca3'
 assert pin['report']['outputs']['layout/nssoc_cdr_pd484_localbus_v12.gds']=='ebbdf5d83b35c110409c8934058e838f59751d9088485c36bd4d78e5166e510c'
 print('PASS_EXACT_V22_NATIVE_PARENT_ORIGINAL_COMPLETE_EXTRACTION_GATES')
if __name__=='__main__':check()
