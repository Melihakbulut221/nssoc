"""Independent saved-edge arithmetic only; no producer imports or raw replay."""
from pathlib import Path
import json,hashlib,math
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'pair-result.json';result=json.loads(p.read_text());assert result['inputs']=={p:pin(p) for p in result['inputs']}
paths=[Path('/dev/shm/nssoc-pll-acquisition-v1-step5-full-review-01/result.json'),B/'result.json'];reviews=[json.loads(p.read_text()) for p in paths];captures=[Path('/dev/shm/nssoc-pll-acquisition-v1-step5-01'),Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02')];native=[json.loads((p/'result.json').read_text()) for p in captures]
assert native[0]['devices']==native[1]['devices'] and len(native[0]['devices'])==539
assert {k:v for k,v in native[0]['config'].items() if k!='step_s'}=={k:v for k,v in native[1]['config'].items() if k!='step_s'}
a=(captures[0]/'bench.cir').read_text();b=(captures[1]/'bench.cir').read_text();assert a.count('.tran 5e-12 1e-06 0 5e-12')==1 and a.replace('.tran 5e-12 1e-06 0 5e-12','.tran 2.5e-12 1e-06 0 2.5e-12')==b
windows=[]
for path,q,cap,r in zip(paths,reviews,captures,native):
 assert q['status']=='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC' and q['native_result']==pin(cap/'result.json')
 assert q['inputs']=={p:pin(p) for p in q['inputs']}
 assert q['rows']==r['rows'] and q['values']==r['values'] and q['full_raw_sha256']==r['raw_sha256']
 refs=q['independent']['reference_edges_s'];fb=q['independent']['feedback_edges_s'];ordinals=[]
 for values in [refs,fb]:assert all(math.isfinite(x) for x in values) and all(a<b for a,b in zip(values,values[1:]))
 for t in fb:
  distances=[abs(t-x) for x in refs];nearest=min(distances);assert distances.count(nearest)==1;ordinals.append(distances.index(nearest))
 assert ordinals==q['independent']['reference_ordinals']
 w=[]
 for lo,hi in [(800e-9,900e-9),(900e-9,1e-6)]:
  vals=[(t,i,t-refs[i]) for t,i in zip(fb,ordinals) if lo<=t<hi];ids=[x[1] for x in vals];phase=[x[2] for x in vals]
  assert len(vals)>=9 and all(y==x+1 for x,y in zip(ids,ids[1:]));frequency=(len(vals)-1)/(vals[-1][0]-vals[0][0]);span=max(phase)-min(phase)
  w.append(dict(interval_s=[lo,hi],reference_indices=ids,frequency_hz=frequency,phase_s=phase,phase_mean_s=sum(phase)/len(phase),phase_span_s=span,passed=abs(frequency/1e8-1)<=100e-6 and span<=50e-12))
 windows.append(w)
rows=[]
for a,b,expected in zip(windows[0],windows[1],result['windows']):
 assert a['reference_indices']==b['reference_indices']==expected['reference_indices'];df=abs(a['frequency_hz']-b['frequency_hz'])/1e8*1e6;dp=max(abs(x-y) for x,y in zip(a['phase_s'],b['phase_s']));checks=dict(both_individual_windows_pass=a['passed'] and b['passed'],frequency_difference_100ppm=df<=100,matched_phase_difference_50ps=dp<=50e-12)
 assert df==expected['frequency_difference_ppm'] and dp==expected['maximum_matched_phase_difference_s'] and checks==expected['checks'] and all(checks.values())==expected['passed']
 rows.append(dict(interval_s=a['interval_s'],frequency_difference_ppm=df,maximum_matched_phase_difference_s=dp,original_screen_passed=False,first_phase_mean_s=a['phase_mean_s'],second_phase_mean_s=b['phase_mean_s']))
assert result['passed'] is False and result['status']=='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'
r=dict(status='PASS_INDEPENDENT_SAVED_PAIR_RECOUNT_FAILED_PHASE',inputs={str(p):pin(p) for p in [p,*paths,*[d/'bench.cir' for d in captures]]},method=pin(__file__),findings=[],windows=rows,source_pair_status=result['status'],source_failed_phase_limits_retained=True,native_graph_exact=539,native_decks_differ_only_5ps_vs_2point5ps=True,source_review_input_pins_rehashed=[len(q['inputs']) for q in reviews],scope='Independent exhaustive nearest-reference ordinal/window/phase/frequency arithmetic from two frozen completed saved replay edge arrays. No producer imports, downloads, raw-wave reprocessing, native rerun, threshold change, or full PLL closure.')
out=B/'pair-saved-peer-vco.json';out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out));print(rows)
