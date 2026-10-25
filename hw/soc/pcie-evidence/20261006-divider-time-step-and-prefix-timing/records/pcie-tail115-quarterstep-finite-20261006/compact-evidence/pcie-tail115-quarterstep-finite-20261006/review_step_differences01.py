# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,os,resource
import numpy as np
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent;Q=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-quarterstep-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
c=json.loads((Q/'step-comparison01.json').read_text());results=[]
for z in c['captures']:
 resultpath=next(Path(p)for p in z['source_inputs']if p.endswith('/result.json'));r=json.loads(resultpath.read_text());assert pin(resultpath)==z['source_inputs'][str(resultpath)]
 es=z['cml_boundaries'];phase=[e['fixed_phase_ps']for e in es];results.append(dict(step_s=z['step_s'],native_status=z['native_status'],result_path=str(resultpath),result=pin(resultpath),raw=next(v for p,v in z['source_inputs'].items()if p.endswith('/wave.raw.gz')),vco_frequency_hz=r['measurement']['vco_frequency_hz'],feedback_frequency_hz=r['measurement']['feedback_frequency_hz'],electrical_pass=r['safety']['passed'],all_checks=r['measurement']['checks'],rows=r['rows'],values=r['values'],cml_count=z['cml_edges'],vco_count=z['vco_edges'],bad_bucket_indices=z['bad_bucket_indices'],nearest_ordinal_advances=sorted(set(z['nearest_ordinal_advances'])),fixed_phase_ps=dict(first=phase[0],last=phase[-1],min=min(phase),max=max(phase)),cml_edge_times_s=[e['cml_edge']['time_s']for e in es],fixed_phases_ps=phase))
pairs=[]
for a,b in zip(results[:-1],results[1:]):
 assert len(a['cml_edge_times_s'])==len(b['cml_edge_times_s'])==61
 dt=[(y-x)*1e12 for x,y in zip(a['cml_edge_times_s'],b['cml_edge_times_s'])];dp=[y-x for x,y in zip(a['fixed_phases_ps'],b['fixed_phases_ps'])]
 pairs.append(dict(from_step_s=a['step_s'],to_step_s=b['step_s'],vco_frequency_change_hz=b['vco_frequency_hz']-a['vco_frequency_hz'],vco_frequency_change_ppm=(b['vco_frequency_hz']/a['vco_frequency_hz']-1)*1e6,feedback_frequency_change_ppm=(b['feedback_frequency_hz']/a['feedback_frequency_hz']-1)*1e6,same_windowed_CML_ordinal_time_delta_ps=dict(first=dt[0],last=dt[-1],min=min(dt),max=max(dt),all=dt),same_CML_ordinal_relative_phase_delta_ps=dict(first=dp[0],last=dp[-1],min=min(dp),max=max(dp),all=dp),alignment='Same declared4–34ns window, all61 CML indices matched directly. No phase offset fit/removal or shift ofwindow/threshold. This descriptive matching is not an assertion of startupacquisition equivalence.'))
r=dict(status='EXACT_SAVED_THREE_STEP_FREQUENCY_AND_PHASE_DIFFERENCES_NO_CONVERGENCE_ACCEPTANCE',method=pin(__file__),comparison=pin(Q/'step-comparison01.json'),captures=results,adjacent_comparisons=pairs,absolute_VCO_step_change_ratio=pairs[0]['vco_frequency_change_hz']/pairs[1]['vco_frequency_change_hz'],conclusion='Only1.25ps individual full34ns run passes all original predicates.5ps and2.5ps retainFAIL. Adjacent frequency movement decreases approximately4fold, but1.25ps differs1079ppm from2.5ps; no numerical convergence tolerance hasbeen met or adopted here. No newnative or physicaloracle changed.',overall_physical_acceptance=False)
(B/'step-differences01.json').write_text(json.dumps(r,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
for z in results:
 x=np.array(z['cml_edge_times_s'])*1e9;y=z['fixed_phases_ps'];label=f"{z['step_s']*1e12:g} ps ({z['native_status'].split('_')[0]})";axes[0].plot(x,y,marker='.',label=label)
axes[0].axhline(0,color='k',lw=.8);axes[0].set_xlabel('CML edge time (ns)');axes[0].set_ylabel('CML minus fixed VCO ordinal (ps)');axes[0].legend()
xx=[z['step_s']*1e12 for z in results];yy=[z['vco_frequency_hz']/1e9 for z in results];axes[1].plot(xx,yy,'o-')
for x,y in zip(xx,yy):axes[1].annotate(f'{y:.9f} GHz',(x,y),xytext=(6,7),textcoords='offset points')
axes[1].set_xlabel('Output/maxstep (ps), same full34ns circuit');axes[1].set_ylabel('Measured VCO frequency (GHz)');axes[1].set_xlim(.8,5.8);axes[1].set_ylim(min(yy)-.004,max(yy)+.006)
for ax in axes:ax.grid(alpha=.25)
fig.suptitle('Tail115: one full-window pass; numerical convergence still open')
fig.savefig(B/'three-step-frequency-and-phase.png',dpi=140);plt.close(fig)
print(json.dumps({k:r[k]for k in ['status','absolute_VCO_step_change_ratio','conclusion']},indent=2))
for p in pairs:print({k:v for k,v in p.items()if 'delta'not in k and k!='alignment'})
