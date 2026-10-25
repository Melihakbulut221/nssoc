#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind fresh physical collector routing and preserve every native extraction gate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 from check_cdr_data_v20_extraction_sources import check as original
 original()
 d=json.loads((ROOT/'scripts/cdr-collector-trunks-v21-extraction-source-delta.json').read_text())
 for row in d['files']:
  raw=(ROOT/row['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
  text=raw.decode();parts=[];cursor=0
  for e in row['changes']:
   assert cursor<=e['start']<=e['end']<=len(text)
   parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
  parts.append(text[cursor:]);actual=(ROOT/row['candidate_path']).read_bytes()
  assert actual==''.join(parts).encode()and hashlib.sha256(actual).hexdigest()==row['candidate_sha256']
 pin=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-parent-physical-pass-20261020.json').read_text())
 assert pin['run']==39440691879 and pin['source_head']=='4446725afb079d53c9f707c92fc4cfb2a94e31a7'
 assert pin['summary_sha256']=='ae578b3ecf11a68193c310a0a496d47c959d30a411f7c6803aeb04f1e5dfff0d'
 assert pin['parts_sha256']=='ef981a03d4fc541876d3ec0ff8d514c8a47751b29f812f7708e588da8b8359f7'
 assert pin['report']['outputs']['layout/nssoc_cdr_pd484_localbus_v12.gds']=='3fdfff892b3c84d78349c7358699dfa2ec8fd98a98b887573beb4f4b3219c936'
 print('PASS_EXACT_V21_NATIVE_PARENT_ORIGINAL_COMPLETE_EXTRACTION_GATES')
if __name__=='__main__':check()
