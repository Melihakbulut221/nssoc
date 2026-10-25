#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run unchanged full capture/acquisition gates, then all physical voltage envelopes."""
import json, os, traceback
from pathlib import Path
import cloud_pll845_terminal_envelope_binding as binding_stage
import read_pll845_sparse_completed as original
import read_pll845_all_native_transient as wave
import pll845_terminal_envelopes as envelope
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-complete-terminal-envelopes'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_capture=False,
                full_device_safety_accepted=False,full_phy_accepted=False,acquisition_accepted=False,
                native_activation_performed=False)
    def save(): (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        binding_stage.OUT=OUT/'binding'
        binding_stage.main()
        bound=json.loads((binding_stage.OUT/'result.json').read_text())
        assert bound['sources_unchanged'] and bound['native_devices']==845 and bound['measurements']==6167
        assert len(bound['controls']['rejected'])==11
        # Keep the complete original reader/controller untouched. Its rejected
        # acquisition remains a rejection, even when useful diagnostics follow.
        acquisition_error=None
        try: original.main()
        except BaseException as error:
            original_path=ROOT/'cloud-pll845-sparse-completed-reader/result.json'
            if not original_path.exists(): raise
            prior=json.loads(original_path.read_text())
            if not (isinstance(error,AssertionError) and
                    prior['status']=='REJECTED_ORIGINAL_FULL845_ACQUISITION_GATES' and
                    prior['full_capture'] and prior['verified_ordinary_source']): raise
            acquisition_error=error
        prior=json.loads((ROOT/'cloud-pll845-sparse-completed-reader/result.json').read_text())
        assert prior['native_complete'] and prior['full_capture'] and prior['verified_ordinary_source']
        assert prior['original_inputs_unchanged'] and prior['original_release_retains_all_native_bytes']
        report['original_reader']=prior
        save()
        raw=ROOT/'cloud-pll845-sparse-completed-input/complete-original.raw'
        contract=json.loads((binding_stage.OUT/'original-reader/reader-contract.json').read_text())
        plan=json.loads((binding_stage.OUT/'terminal-envelope-plan.json').read_text())
        assert plan['raw_table_sha256']==wave.digest(wave.contract_check(contract))
        names,values,capture=wave.capture(raw,contract)
        assert capture['raw_sha256']==prior['logical_capture']['sha256']==prior['capture']['raw_sha256']
        observed=envelope.envelopes(names,values,plan['measurements'])
        assert observed['rows']==capture['rows'] and observed['start_s']==0 and abs(observed['end_s']-1e-6)<1e-15
        observed.update(full_capture=True,raw_sha256=capture['raw_sha256'],native_devices=845,
                        physical_terminal_probes=2737,auxiliary_contacts=4,
                        required_full_capture_reader=capture)
        (OUT/'complete-terminal-envelopes.json').write_text(json.dumps(observed,indent=2)+'\n')
        report.update(status='COMPLETE_FULL1US_TERMINAL_VOLTAGES_REQUIRES_DEVICE_LIMIT_CURRENT_PVT_PHY_SIGNOFF',
                      full_capture=True,rows=capture['rows'],raw_sha256=capture['raw_sha256'],
                      measurements=6167,all_original_samples_analyzed=True,
                      acquisition_accepted=prior['acquisition_accepted'],
                      original_acquisition_rejection_preserved=acquisition_error is not None)
        save()
        if acquisition_error is not None:
            report['status']='REJECTED_ORIGINAL_ACQUISITION_WITH_COMPLETE_TERMINAL_VOLTAGE_DIAGNOSIS'
            save()
            raise acquisition_error
    except BaseException as error:
        if report['status']=='RUNNING':report['status']='FAIL_FULL_TERMINAL_ENVELOPES'
        report.update(error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        old=ROOT/'cloud-pll845-sparse-completed-reader/result.json'
        if old.exists():
            (OUT/'original-reader-result.json').write_bytes(old.read_bytes())
        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
        print(json.dumps({k:report[k]for k in ['status','full_capture','acquisition_accepted','full_device_safety_accepted']}))
if __name__=='__main__':main()
