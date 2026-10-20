#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Review the untouched native OP capture; never rerun CAD to change a reader."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import read_pll845_full_native_op as reader
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll845-op-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),
      reader_sha256=sha(Path(reader.__file__)),accepted=False,full_phy_accepted=False,qualified_pex=False,
      native_execution_repeated=False,zero_source_op_passed=False,full_transient_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        files=['case/op.raw','case/op-only.cir.log','case/circuit.cir','case/parent865.spice','prepared/terminal-instrumentation.json','prepared/composition/composition.json']
        prior,proof=reports.restore_report('pll845-loaded-op',39360539378,
          '487f35fdf208ec2c452d2d1bddb0634b995299489f92c0feae4388dc8fb3e992',
          'b0dbdf006c3c7b183f6b65dbc1d66dc30d27c039c5b4d33093f27eb362ed4eb7',OUT/'source',files)
        assert prior['source_head']=='893bbe5ae33af2e78e57d4c68aa14525995cc832'and prior['status']=='FAIL_OR_ERROR'
        assert len(prior['native_runs'])==1 and prior['native_runs'][0]['returncode']==0 and not prior['native_runs'][0]['diagnostics']
        assert prior['native_runs'][0]['log_sha256']==sha(OUT/'source/case/op-only.cir.log')
        assert prior['native_hbt_off_readback']==dict(devices=102,all_readback_one=True)
        assert prior['native_options']['backend']=='klu'and not prior['native_diagnostics']
        r['native_source']=proof;r['native_hbt_off_readback']=prior['native_hbt_off_readback'];r['native_options']=prior['native_options']
        contract=json.loads((OUT/'source/prepared/composition/composition.json').read_text())
        coverage=json.loads((OUT/'source/prepared/terminal-instrumentation.json').read_text())
        assert contract['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
        assert len(coverage['native_terminal_probes'])==2737 and len(coverage['vectors'])==1694
        assert not contract['uncontacted_body_groups']and coverage['full_native_terminal_coverage']
        assert all(t['explicit_zero_reference']or t['vector']in coverage['vectors']for t in coverage['native_terminal_probes'])
        raw=(OUT/'source/case/op.raw').read_bytes()
        r['operating_point']=reader.read(raw,coverage['vectors']);save()
        assert r['operating_point']['native_columns']==5105
        r['controls']=reader.controls(raw,coverage['vectors'])
        assert len(r['controls'])==10 and all(x['rejected']for x in r['controls'])
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in files)
        assert sha(Path(__file__))==r['controller_sha256']and sha(Path(reader.__file__))==r['reader_sha256']
        r.update(status='PASS_WHOLE_PLL_ALL_NATIVE_ZERO_SOURCE_OP_AND10_CONTROLS_REQUIRES_FULL_LOADED_TRANSIENT',
          sources_unchanged=True,zero_source_op_passed=True,biased_operation_accepted=False)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
