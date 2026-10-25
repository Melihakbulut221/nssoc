#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Summarize previously captured native master/slave input samples, cloud only.

This reads no new transient, changes no sampling edge and passes no PHY gate.
Inputs outside the acquisition window are descriptive, not pass/fail criteria.
"""
import argparse,json,math,os,statistics
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def stats(values,indices=None):
    x=values if indices is None else [values[i]for i in indices]
    assert x and all(math.isfinite(v)for v in x)
    return dict(samples=len(x),different_sign_count=sum(v<=0 for v in x),below_100mv_count=sum(v<.1 for v in x),minimum_signed_v=min(x),maximum_signed_v=max(x),mean_signed_v=statistics.fmean(x))
def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=('nominal_early','nominal_late'),required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-fixed-input-summary-'+a.case);out.mkdir(exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',case=a.case,source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,scope='Only summaries of original native stage-input samples at fixed phases. Original electrical failures remain. No waveform, latency or threshold changes.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        receipt=ROOT/'docs/evidence/cdr-collector-v8-fixed-sampling-review-20261019.json';pin=json.loads(receipt.read_text());case=pin['cases'][a.case]
        prior,proof=reports.restore_report('cdr-collector-v8-sampling-review-'+a.case,pin['run'],case['summary_sha256'],case['parts_sha256'],out/'input',['fixed-sampling-review.json'])
        assert prior==case['report'] and prior['sources_unchanged'] and not prior['accepted']
        data=json.loads((out/'input/fixed-sampling-review.json').read_text());assert set(data['samples'])==set('abcd')
        r['source']=proof;r['receipt_sha256']=sha(receipt);r['samplers']={}
        for tag,d in data['samples'].items():
            expected=d['expected_bits'];assert len(expected)==255 and set(expected)<={0,1}
            changed=[i for i in range(1,255)if expected[i]!=expected[i-1]]
            held=[i for i in range(1,255)if expected[i]==expected[i-1]]
            assert len(changed)+len(held)==254 and changed and held
            public=('dp','dn')if tag in 'ab'else('cup','cun')if tag=='c'else('dup','dun')
            assert tuple(d['public_input_nets'])==public and len(d['public_input_witnesses'])==2
            assert len(d['slave_input_devices'])==len(d['master_input_devices'])==2
            rr=dict(public_input_nets=list(public),master_input_devices=d['master_input_devices'],slave_input_devices=d['slave_input_devices'],changed_bits=len(changed),held_bits=len(held),stages={})
            for stage in ('master_inputs','slave_inputs'):
                rr['stages'][stage]={}
                for phase,row in d[stage].items():
                    x=row['signed_against_original_expected_v'];assert len(x)==255
                    differential=row['differential_v'];assert len(differential)==255
                    assert all(abs(v-(2*bit-1)*raw)<1e-15 for v,raw,bit in zip(x,differential,expected,strict=True))
                    rr['stages'][stage][phase]=dict(all_bits=stats(x),changed_bits=stats(x,changed),held_bits=stats(x,held))
            rr['output']={}
            for phase,row in d['output'].items():
                x=row['signed_output_v'];assert len(x)==len(row['time_s'])==255
                measured=stats(x);original=prior['fixed_sampling_phase_review'][tag]['output_at_original_phases'][phase]
                assert measured['different_sign_count']==original['wrong_sign_samples'] and measured['below_100mv_count']==original['below_100mv_samples'] and abs(measured['minimum_signed_v']-original['minimum_signed_margin_v'])<1e-12
                rr['output'][phase]=dict(all_bits=measured,changed_bits=stats(x,changed),held_bits=stats(x,held))
            r['samplers'][tag]=rr
        assert sha(out/'input/fixed-sampling-review.json')==prior['outputs']['fixed-sampling-review.json']
        r.update(status='COMPLETE_NATIVE_MASTER_SLAVE_FIXED_PHASE_SUMMARY_ORIGINAL_GATES_REMAIN_FAILED',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
