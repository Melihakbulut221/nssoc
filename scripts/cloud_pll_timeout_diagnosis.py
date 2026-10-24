#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnose retained hosted-budget interruptions, never accept partial PLL runs."""
import argparse,json,os,re
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from read_cloud_pll_acquisition_prefix import decode_prefix
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-timeout-diagnosis'
SOURCES={9:('b9e0263960197063b4dea5c8198d037af7aa026589845dc23a40deee95c0667c','3c73fe7863bdea7f6d38a2507017357e81ea2a7a1f50876f998e786a6856dc03'),11:('c931c1e40aee5fe1b97b3dfcfea72ca8944cf2d2f5d1c6a26def02cbd2d386c8','37daac655dcd40159383ca27ed110ac563ace149b8128f5830a4a2a4b2f21de1')}
def main():
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,choices=(9,11),required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],filter_cap_um=args.size,accepted=False,full_capture=False,full_phy_accepted=False,acquisition_passed=False,
        scope='Only source-bound retained interrupted waveform diagnosis. No padded row, restart, waveform splice, changed integration step, relaxed acquisition gate or candidate adoption.')
    try:
        dest=OUT/'source';source,proof=reports.restore_report('pll-filter-'+str(args.size),38847729630,*SOURCES[args.size],dest,('patched/actual-acquisition.raw','patched/run.log','patched/circuit.cir'))
        assert source['source_head']=='beb087ef2714d1a45aa146e9a2975c6038ac48fd'and source['filter_cap_um']==args.size
        assert source['status']=='FAIL_OR_ERROR'and source['error']=="TimeoutError('Native1us exceeded hosted19800s budget; preserve incomplete capture')"
        assert not source['accepted']and not source['physical_candidate_accepted']
        path=dest/'patched/actual-acquisition.raw';before=sha(path);names,v,meta=decode_prefix(path.read_bytes(),interrupted_diagnostic=True)
        assert len(names)==35 and names[0]=='time';t=v[:,0];assert t[0]==0 and 0<t[-1]<1e-6
        delta=np.diff(t);assert delta.max()<=3.125e-13*1.00001
        circuit=(dest/'patched/circuit.cir').read_text();vectors=next(l[5:].split()for l in circuit.splitlines()if l.startswith('save '))
        assert set(names)=={'time',*vectors} and len(vectors)==34
        assert circuit.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
        text=(dest/'patched/run.log').read_text(errors='replace')
        result.update(status='COMPLETE_INTERRUPTED_PREFIX_DIAGNOSIS_NOT_ACQUISITION_ACCEPTANCE',source=proof,source_error=source['error'],native_raw_sha256=before,parser=meta,
            observed_start_s=float(t[0]),observed_end_s=float(t[-1]),required_end_s=1e-6,missing_duration_s=float(1e-6-t[-1]),observed_duration_fraction=float(t[-1]/1e-6),native_rows=len(v),
            time_step_s=dict(minimum=float(delta.min()),median=float(np.median(delta)),maximum=float(delta.max())),
            tail_times_s=[float(x)for x in t[-16:]],last_values={n:float(v[-1,i])for i,n in enumerate(names)},
            native_diagnostic_lines=[l for l in text.splitlines()if re.search(r'warning|error|singular|too small|jmax|vmax',l,re.I)],
            hosted_internal_budget_s=19800,restartable_state_preserved=False)
        assert sha(path)==before
        # Original immutable release keeps every byte. Do not republish another
        # huge duplicate of the same failed waveform just for this diagnosis.
        del v,t,delta;path.unlink()
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items()if k in ('status','error','observed_end_s','missing_duration_s','observed_duration_fraction')}),flush=True)
if __name__=='__main__':main()
