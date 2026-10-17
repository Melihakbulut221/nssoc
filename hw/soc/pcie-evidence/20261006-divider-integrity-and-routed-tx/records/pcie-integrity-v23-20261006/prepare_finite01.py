# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal completed V23 public/control/native scope; no producer or EDA rerun."""
from pathlib import Path
import json,hashlib,datetime,xml.etree.ElementTree as E
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def load(p):return json.loads(Path(p).read_text())
freeze=load(B/'source-freeze03.json')
for p,h in freeze['sources'].items():assert pin(R/p)==h,p
counts=[]
for n,expected in [('01',(28,7)),('02',(6,3)),('03',(3,0))]:
 cs=list(E.parse(B/f'controls{n}.xml').iter('testcase'));fail=sum(c.find('failure') is not None or c.find('error') is not None for c in cs);passed=len(cs)-fail
 assert (passed,fail)==expected and not any(c.find('skipped') is not None for c in cs);counts.append({'campaign':n,'passed':passed,'failed':fail,'xml':pin(B/f'controls{n}.xml')})
peer=load(B/'native-saved-peer-vco.json');assert not peer['findings']
assert pin(B/'native-saved-peer-vco.json')=={'bytes':6039,'sha256':'25cc42dd48b0eed29a9af62885e2f66b8adbb14578832a5b844c78f283a8dda2'}
releases={};assets=[]
for n in ['failed-controls01-release.json','failed-controls02-release.json','controls-composite-release01.json','native-release01.json']:
 d=load(B/n);assert d['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
 for f in d['files']:assert pin(Path(f['path']))=={k:f[k] for k in ['bytes','sha256']}
 for a in d['assets']:assert a['authenticated_roundtrip'] and a['anonymous_roundtrip'];assets.append(a)
 releases[n]=pin(B/n)
assert len(assets)==len({a['name'] for a in assets})==8
s=load(B/'continuation-status01.json');assert s['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
assert len(s['stages'])==7 and all(x['returncode']==0 for x in s['stages'])
d=load(B/'candidate-decision.json');assert d['setup_ns']=={'slow':-3.191682,'typical':-.549377,'fast':.998914};assert not d['adopted'] and not d['physical_acceptance']
controls={'original_selected_predicates_covered':35,'additional_real_block_port_burst_positive':True,'pytest_executions':47,'passed_executions':37,'historical_failed_executions':10,'campaigns':counts,'direct_public_profile_cases':18,'cycle_miter_profile_cases':18,'saved_targeted_public_native_cases':{'passed':1,'failed':0,'selected_out_skips':17},'literal_binary_vectors':557056,'literal_xz_vectors':1440,'meaningful_header_mutants':5,'actual_wrapper_miter_mutants':11,'actual_product_faults':12,'actual_block_burst':{'accepted_blocks':15,'bytes':786,'packets':25,'promotions':14,'changed_relation_promotions':13,'simultaneous_promotion_accept':13,'input_stall_cycles':38,'output_stall_cycles':6},'surviving_wrapper_promotion_mutant_now_real_framer_detected_at_ns':28,'all_original_17_case_prefix_unchanged':True,'MAX4118_profile_excluded':True,'scope':'Original 28/7 and targeted6/3 remain failed execution records. Host false-positive-reader schema failures recounted from exact sealed native metadata; real promotion mutant fixed by stronger real block-port stimulus. No failed simulation relabeled; final combined predicate coverage is explicit.'}
package={'status':'FINITE_PUBLIC_V23_ADJACENT_HEADER_NATIVE_SETUP_REJECTED','utc':datetime.datetime.now(datetime.UTC).isoformat(),'source_freeze':pin(B/'source-freeze03.json'),'source_allowlist':freeze['sources'],'controls':controls,'functional_source_peer':pin(B/'source-only-peer-vco03.json'),'saved_controls_peer':pin(B/'saved-controls-peer-vco03.json'),'native_source_peer':pin(B/'native-source-only-peer01.json'),'native_saved_peer':pin(B/'native-saved-peer-vco.json'),'registered_boundary':pin(B/'native-registered-boundary.json'),'critical_path':pin(B/'critical-path-attribution.json'),'native':d,'releases':releases,'assets':assets,'adopted':False,'stable_baseline':'V11','physical_acceptance':False,'scope':'Same4ns CPU6/2GiB native preplacement screen, whole original pin graph preserved, registered retire data boundary confirmed. Setup remains negative at SS and TT despite352.600ps SS gain versusV22. No mapped functional replay, CTS/routeRC/mainchip/PHY production acceptance. All predecessor failures remain immutable.'}
p=B/'pcie-integrity-v23-finite-package-20261006.json';assert not p.exists();p.write_text(json.dumps(package,indent=2)+'\n');print(pin(p))
