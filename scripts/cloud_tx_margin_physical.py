#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate fresh native TX prestage layouts only after exact full32 PVT proof."""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
from cloud_corrpre_banked_handoff import api,get_asset,wait_success
import cloud_tx_tree32_margin as native
ROOT=Path(__file__).resolve().parents[1]
WAIT=ROOT/'cloud-tx-margin-pre-source'
OUT=ROOT/'hw/soc/out/cloud-tx-margin-pre'
BASE_SHA='312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f'
ADAPTED_SHA='f45c72a6b8b0322a306562fccbfb2bc9df187cb2726d2d9b21ae59c1a9b81c28'
EDITS=[{'before': 'cloud-tx-layout-repair', 'after': 'cloud-tx-margin-pre', 'count': 1}, {'before': 'from cloud_tx_tree32_budget import trim_dividers', 'after': 'from cloud_tx_tree32_margin import candidate as trim_dividers', 'count': 1}, {'before': 'docs/evidence/tx-tree32-headroom-fixed-pvt-pass-20261017.json', 'after': 'docs/evidence/tx-margin-native-input.json', 'count': 1}, {'before': '39005251402', 'after': '39055820343', 'count': 2}, {'before': 'ad92399dccc8a4b58ee8afc83cbc4bc0df64c061', 'after': '9a12e63608607c9cc3a74da4d644690516c0c3f1', 'count': 1}, {'before': "proof['variant']=='budget_high3_trim'", 'after': "proof['variant']=='budget_drive_v3'", 'count': 1}, {'before': "('_trim_layout_v1'if args.prestage_headroom_trim else'_layout_v1')", 'after': "('_margin_layout_v1'if args.prestage_headroom_trim else'_layout_v1')", 'count': 1}]
RUN=39055820343
HEAD='9a12e63608607c9cc3a74da4d644690516c0c3f1'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert '--prestage-headroom-trim'in sys.argv and '--prestage-nx'in sys.argv
    nx=int(sys.argv[sys.argv.index('--prestage-nx')+1]);assert nx in (1,3)
    WAIT.mkdir(exist_ok=False)
    r=dict(status='WAITING_FOR_EXACT_FULL32_NATIVE_MARGIN',source_head=os.environ['GITHUB_SHA'],accepted=False,physical_complete=False,nx=nx)
    def save():(WAIT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=wait_success(RUN,'.github/workflows/tx-tree32-margin-cloud.yml',time.monotonic()+14400,r,save)
        assert run['head_sha']==HEAD and run['event']=='push'and run['run_attempt']==1
        expected=native.controls();cases=[];receipts={}
        for condition,fault in [('nominal','none'),('hot_low','none'),('cold_high','none'),('nominal','swap_leaf_select')]:
            group='tx-tree32-margin-'+condition+'-'+fault;stem=group+'-'+str(RUN)+'-1'
            rel=api('releases/tags/cloud-results-'+str(RUN)+'-1-'+group)
            matches=[a for a in rel['assets']if a['name']==stem+'.summary.json'];assert len(matches)==1
            asset=matches[0];raw,digest=get_asset(asset);proof=json.loads(raw)
            assert proof['source_head']==HEAD and proof['variant']=='budget_drive_v3'and proof['source_unchanged']
            assert proof['condition']==condition and proof['fault']==fault and not proof['diagnostics']and proof['returncode']==0
            assert proof['candidate_controller_sha256']==hashlib.sha256((ROOT/'scripts/cloud_tx_tree32_margin.py').read_bytes()).hexdigest()
            for size in (1,3):assert proof['outputs']['pre-nx'+str(size)+'.spice']==expected[size]['candidate_sha256']
            if fault=='none':
                assert proof['schematic_screen_passed']and proof['review']['all_engineering_gates_passed']
                assert not proof['review']['failed_hbts']and not proof['review']['failed_mos']
            else:assert proof['actual_leaf_fault_rejected_by_original_bits']and not proof['review']['signals']['passed']
            cases.append(dict(run=RUN,source_head=HEAD,group=group,summary_url=asset['browser_download_url'],summary_sha256=digest))
            receipts[group]=dict(summary_sha256=digest,report=proof)
        evidence=dict(status='FIXED_GEOMETRY_NOMINAL_HOT_COLD_AND_ACTUAL_FAULT_PASSED_NOT_PHYSICAL_ACCEPTANCE',cases=cases)
        target=ROOT/'docs/evidence/tx-margin-native-input.json';assert not target.exists();target.write_text(json.dumps(evidence,indent=2)+'\n')
        base=ROOT/'scripts/run_cloud_tx_layout_repair.py';text=base.read_text();assert hashlib.sha256(text.encode()).hexdigest()==BASE_SHA
        for edit in EDITS:assert text.count(edit['before'])==edit['count'];text=text.replace(edit['before'],edit['after'])
        assert hashlib.sha256(text.encode()).hexdigest()==ADAPTED_SHA
        generated=ROOT/'scripts/_cloud_tx_margin_physical_native.py';assert not generated.exists();generated.write_text(text)
        r.update(status='RUNNING_FRESH_NATIVE_PHYSICAL_GATES',native_cases=receipts,source_candidate=expected[nx],base_sha256=BASE_SHA,adapted_sha256=ADAPTED_SHA,edits=EDITS);save()
        spec=importlib.util.spec_from_file_location('tx_margin_physical_native',generated);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.main()
        result=json.loads((OUT/'result.json').read_text())
        assert hashlib.sha256(base.read_bytes()).hexdigest()==BASE_SHA and hashlib.sha256(generated.read_bytes()).hexdigest()==ADAPTED_SHA
        assert result['prestage_sizing']['candidate_sha256']==expected[nx]['candidate_sha256']
        r.update(status='COMPLETED_FRESH_LAYOUT_CONTROLLER_SEE_NATIVE_PHYSICAL_GATES',physical_result=result)
    except BaseException as error:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        save()
        # Preserve failures before generator startup under the same workflow output root.
        OUT.mkdir(parents=True,exist_ok=True)
        if not (OUT/'result.json').exists():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
        (OUT/'source-handoff.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
