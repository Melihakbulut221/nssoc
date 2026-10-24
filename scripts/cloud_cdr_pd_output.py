#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual PD output voltages before designing a directly loaded V/I stage."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
RUN=39056756395
HEAD='3aa56a8e362dd952c0de7c081efe37882ca5d7ec'
CASES=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late']
START=2e-9;UI=125e-12;STOP=START+258*UI;STEP=.3125e-12

def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-pd-output-'+a.case);out.mkdir(exist_ok=False);reports.OUT=out
    scratch=ROOT/('scratch-cdr-pd-output-'+a.case);assert not scratch.exists()
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=a.case,accepted=False,full_phy_accepted=False,scope='Reanalysis of unchanged native retimed-PD capture. No new simulation, V/I circuit, load model or closed-loop claim. Original waveforms remain in source releases.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        path=ROOT/'docs/evidence/cdr-retimed-pd-pass-20261017.json';pin=json.loads(path.read_text());row=pin['reports'][a.case]
        run=api('actions/runs/'+str(RUN));assert run['head_sha']==HEAD and run['event']=='push'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='success'
        proof=row['report'];assert proof['sources_unchanged']and proof['data_passed']and proof['devices_passed']and proof['phase_passed']and proof['returncode']==0 and not proof['diagnostics']and proof['zero_source_op_maximum']==0 and proof['native_flags_verified']==114
        group='cdr-retimed-pd-'+a.case;release=api(f'releases/tags/cloud-results-{RUN}-1-{group}')
        assets=[x for x in release['assets']if x['name']==f'{group}-{RUN}-1.parts.json'];assert len(assets)==1
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(assets[0]['id']),'-H','Accept: application/octet-stream']);parts_sha=hashlib.sha256(raw).hexdigest()
        selected=['native/wave.dat','native/bench.cir','actual-pd.spice']
        actual,receipt=reports.restore_report(group,RUN,row['summary_sha256'],parts_sha,scratch,selected);assert actual==proof
        wavefile=scratch/'native/wave.dat';assert sha(wavefile)==proof['outputs']['native/wave.dat']
        with wavefile.open()as f:header=f.readline().lower().split()
        assert header==['time',*proof['vectors']]
        names=['time','v(xp)','v(xn)','v(yp)','v(yn)'];columns=[header.index(n)for n in names]
        wave=np.loadtxt(wavefile,skiprows=1,usecols=columns);t=wave[:,0]
        assert wave.shape[1]==5 and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        active=t>=START;window=(t>=START+8*UI)&(t<=START+255*UI)
        def bounds(values):return dict(minimum=float(values.min()),maximum=float(values.max()))
        legs={names[i]:dict(alltime_v=bounds(wave[:,i]),active_v=bounds(wave[active,i]))for i in range(1,5)}
        pairs={}
        for name,pcol,ncol in [('x',1,2),('y',3,4)]:
            cm=(wave[:,pcol]+wave[:,ncol])/2;diff=wave[:,pcol]-wave[:,ncol]
            pairs[name]=dict(commonmode_active_v=bounds(cm[active]),differential_active_v=bounds(diff[active]),commonmode_alltime_v=bounds(cm),differential_alltime_v=bounds(diff))
        delta=wave[:,1]-wave[:,2]-wave[:,3]+wave[:,4]
        phase=float(np.trapezoid(delta[window],t[window])/(t[window][-1]-t[window][0]));assert abs(phase-proof['phase_average_v'])<1e-12
        assert proof['wire_counts']=={'R':8040,'C':5282}
        r.update(status='PASS_EXACT_NATIVE_PD_OUTPUT_REANALYSIS_NOT_LOADED_CONVERTER_ACCEPTANCE',restore=receipt,source_summary_asset=row['summary_asset'],source_summary_sha256=row['summary_sha256'],parts_asset=assets[0]['id'],parts_sha256=parts_sha,wave_sha256=proof['outputs']['native/wave.dat'],rows=len(t),time_s=bounds(t),legs=legs,pairs=pairs,recomputed_phase_average_v=phase,original_phase_average_v=proof['phase_average_v'],loaded_by_converter=False,external_output_capacitance_f=50e-15,reference_current_source='external ideal sources, unchanged',hbt_corner='hbt_typ',corner=proof['corner'],pins_sha256=sha(path))
        shutil.copyfile(scratch/'native/bench.cir',out/'original-bench.cir')
        shutil.copyfile(scratch/'actual-pd.spice',out/'original-pd.spice')
        # Only disposable cloud restoration is removed. Hash-bound original
        # native captures and every failure remain in their source release.
        shutil.rmtree(scratch)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
