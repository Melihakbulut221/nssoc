"""Descriptive saved-edge phase offset; never a changed acceptance predicate."""
from pathlib import Path
import json, statistics, hashlib
B = Path(__file__).resolve().parent
A = Path('/dev/shm/nssoc-pll-acquisition-v1-step5-full-review-01/result.json')
a = json.loads(A.read_text())['independent']
b = json.loads((B / 'result.json').read_text())['independent']
def byindex(q):
    assert len(set(q['reference_ordinals'])) == len(q['reference_ordinals'])
    return {i: t - q['reference_edges_s'][i] for t, i in zip(q['feedback_edges_s'], q['reference_ordinals'])}
a, b = byindex(a), byindex(b)
rows = [dict(reference_index=i, phase5ps_s=a[i], phase2p5ps_s=b[i], delta2p5_minus5_s=b[i]-a[i]) for i in sorted(a.keys() & b.keys())]
fixed = [r for r in rows if 79 <= r['reference_index'] <= 98]
v = [r['delta2p5_minus5_s'] for r in fixed]
xs = [r['reference_index'] for r in fixed]
assert xs == list(range(79, 99))
meanx, mean = statistics.mean(xs), statistics.mean(v)
slope = sum((x-meanx)*(y-mean) for x, y in zip(xs, v)) / sum((x-meanx)**2 for x in xs)
summary = dict(first_delta_ps=v[0]*1e12, last_delta_ps=v[-1]*1e12, min_delta_ps=min(v)*1e12, max_delta_ps=max(v)*1e12, range_ps=(max(v)-min(v))*1e12, mean_delta_ps=mean*1e12, linear_slope_ps_per_10ns=slope*1e12, total_change_ps=(v[-1]-v[0])*1e12)
p = B / 'pair-offset-diagnosis01.json'
assert not p.exists()
x = dict(status='SAVED_EDGE_DESCRIPTIVE_DIAGNOSIS_ORIGINAL_PAIR_FAIL_UNCHANGED', inputs={str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [A, B/'result.json', B/'pair-result.json', Path(__file__)]}, sign='2.5ps phase minus5ps phase at equal reference ordinal; neither waveform shifted', fixed_reference_indices=[79,98], fixed_summary=summary, all_shared_edge_rows=rows, interpretation='Late-window difference is predominantly an approximately695ps static phase offset. The full20edge range and fitted residual drift are reported; the difference is not mathematically constant. Startup transient phase differences are preserved. This description does not satisfy the predeclared50ps raw matched-phase predicate: no subtraction, realignment or acceptance change.', passed_pair=False, new_native=False)
p.write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(summary,indent=2))
print('First5', rows[:5])
print('Milestones', [r for r in rows if r['reference_index'] in [9,19,29,39,49,59,69,79,89,98]])
