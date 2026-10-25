#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare unchanged original CDR gates after a frozen-RC sizing experiment."""
import hashlib,json,os,subprocess,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-input-drive-v10-width-comparison'
RUN=39228293871
SOURCE='ccb82a7c18db220e5d20e1c9ca949d42a1dc2d41'
REPO='repos/Melihakbulut221/nssoc/'
def raw_api(path,binary=False):
    args=['gh','api',REPO+path]
    if binary:args+=['-H','Accept: application/octet-stream']
    return subprocess.check_output(args)
def api(path):return json.loads(raw_api(path))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def compact(q):
    result={k:q[k]for k in ('status','data_passed','devices_passed','phase_passed','phase_average_v')}
    keep=('samples','minimum_signed_margin_v','wrong_sign_samples','below_100mv_samples','maximum_clock_to_valid_s','passed')
    result['samplers']={n:{k:v[k]for k in keep}for n,v in q['sampler_checks'].items()}
    result['comparisons']={n:{k:v[k]for k in keep}for n,v in q['comparisons'].items()}
    result['total_wrong_sampler_samples']=sum(v['wrong_sign_samples']for v in q['sampler_checks'].values())
    result['total_low_sampler_samples']=sum(v['below_100mv_samples']for v in q['sampler_checks'].values())
    result['hbt_failed']={n:v for n,v in q['device_checks'].items()if v['minimum_active_vce_v']<.4 or v['maximum_alltime_abs_vce_v']>1.6 or v['maximum_alltime_abs_vbe_v']>1. or v['maximum_alltime_abs_ic_per_emitter_a']>.003}
    result['mos_failed']={n:v for n,v in q['mos_checks'].items()if not v['passed']}
    result['vi']=q['vi']
    return result
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False,geometry_matches_model=False,
        source_run=RUN,source_commit=SOURCE,scope='Diagnostic intrinsic resistor sizing only. Original wire RC is frozen and stale for changed geometry. Comparing original full bit/phase/device gates does not establish physical, closed-loop, PVT or PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        from check_cdr_input_drive_v10_width_sensitivity import check
        check()
        baseline_file=ROOT/'docs/evidence/cdr-input-drive-v10-streamed-native-input-20261019.json'
        baseline_raw=baseline_file.read_bytes();baseline=json.loads(baseline_raw)
        assert baseline['run']==39213606544
        r['baseline_pin_sha256']=sha(baseline_raw)
        protected={str(p):sha(p.read_bytes())for p in [Path(__file__),baseline_file,ROOT/'scripts/cloud_cdr_input_drive_v10_width_sensitivity.py',ROOT/'scripts/cdr_input_drive_v10_width_sensitivity.py']}
        deadline=time.monotonic()+1500
        while True:
            run=api('actions/runs/'+str(RUN))
            assert run['head_sha']==SOURCE and run['run_attempt']==1 and run['path']=='.github/workflows/cdr-input-drive-v10-width-sensitivity-cloud.yml'
            if run['status']=='completed':break
            assert time.monotonic()<deadline,'Specific source run is still live; no restart or completion assumption'
            print('Waiting for exact source run',RUN,run['status'],flush=True);time.sleep(30)
        jobs=api('actions/runs/'+str(RUN)+'/jobs')['jobs']
        assert len(jobs)==5
        control=next(j for j in jobs if j['name']=='syntax-controls')
        assert control['conclusion']=='success'
        r['run_conclusion']=run['conclusion'];r['job_evidence']=[{k:j[k]for k in ('id','name','status','conclusion')}for j in jobs]
        r['cases']={};r['comparison']={}
        for width in (8,16):
            r['comparison'][str(width)]={}
            for case in ('nominal_early','nominal_late'):
                group=f'cdr-input-drive-v10-width{width}-sensitivity-{case}'
                tag=f'cloud-results-{RUN}-1-{group}'
                release=api('releases/tags/'+tag)
                assets={a['name']:a for a in release['assets']}
                stem=f'{group}-{RUN}-1'
                summary_asset=assets[stem+'.summary.json'];parts_asset=assets[stem+'.parts.json']
                raw=raw_api('releases/assets/'+str(summary_asset['id']),True);q=json.loads(raw)
                parts=raw_api('releases/assets/'+str(parts_asset['id']),True);manifest=json.loads(parts)
                assert len(raw)==summary_asset['size']and len(parts)==parts_asset['size']
                assert manifest['parts']and all(p['name']in assets for p in manifest['parts'])
                assert q['source_head']==SOURCE and q['width_um']==width and q['case']==case
                assert q['status']in ('DIAGNOSTIC_ORIGINAL_GATES_PASS_REQUIRES_FRESH_PHYSICAL_AND_PEX','DIAGNOSTIC_ORIGINAL_GATES_REJECTED'),q.get('error')
                assert q['sensitivity_only']and not any(q[k]for k in ('accepted','full_phy_accepted','cdr_accepted','qualified_pex','geometry_matches_model','closed_loop'))
                assert q['sources_unchanged']and q['returncode']==0 and not q['diagnostics']
                assert len(q['sensitivity_controls'])==6 and all(q['sensitivity_controls'].values())
                assert q['sensitivity']['changed_count']==24 and q['sensitivity']['resistor_width_um']==width
                assert not q['sensitivity']['geometry_matches_model']
                old=baseline['cases'][case]['report']
                for field in ('source_bits','source_bits_sha256','expected_samples','expected_comparisons','phase_gate','data_offset_s','corner','native_save_commands'):
                    assert q[field]==old[field],field
                assert sha(bytes(q['source_bits']))==q['source_bits_sha256']
                assert len(q['devices'])==116 and len(q['mos_devices'])==46 and len(q['vectors'])==1107
                assert q['vectors']==old['vectors']
                current=compact(q);previous=compact(old)
                tradeoffs={}
                for name,v in current['samplers'].items():
                    p=previous['samplers'][name]
                    assert v['samples']==p['samples']==765
                    tradeoffs[name]=dict(wrong_change=v['wrong_sign_samples']-p['wrong_sign_samples'],
                        low_margin_change=v['below_100mv_samples']-p['below_100mv_samples'],
                        worst_clock_to_valid_change_ps=(v['maximum_clock_to_valid_s']-p['maximum_clock_to_valid_s'])*1e12,
                        minimum_signed_margin_change_v=v['minimum_signed_margin_v']-p['minimum_signed_margin_v'])
                item=dict(original=previous,candidate=current,sampler_changes=tradeoffs,
                    wrong_sampler_change=current['total_wrong_sampler_samples']-previous['total_wrong_sampler_samples'],
                    low_sampler_change=current['total_low_sampler_samples']-previous['total_low_sampler_samples'],
                    requires_fresh_physical_and_rc=True,physical_accepted=False)
                r['comparison'][str(width)][case]=item
                (OUT/(group+'.summary.json')).write_bytes(raw)
                (OUT/(group+'.parts.json')).write_bytes(parts)
                r['cases'][group]=dict(summary_asset=summary_asset['id'],summary_sha256=sha(raw),parts_asset=parts_asset['id'],parts_sha256=sha(parts),release_url=release['html_url'],status=q['status'])
                save()
        assert all(sha(Path(p).read_bytes())==digest for p,digest in protected.items())
        r.update(status='COMPLETE_FROZEN_RC_WIDTH_DIAGNOSIS_NOT_PHYSICAL_ACCEPTANCE',sources_unchanged=True,protected_inputs=protected)
        print(json.dumps({w:{c:dict(wrong_change=d['wrong_sampler_change'],low_change=d['low_sampler_change'],devices_passed=d['candidate']['devices_passed'],data_passed=d['candidate']['data_passed'])for c,d in rows.items()}for w,rows in r['comparison'].items()}),flush=True)
    except BaseException as e:
        r.update(status='FAIL_OR_INCOMPLETE_DIAGNOSIS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p.read_bytes())for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
