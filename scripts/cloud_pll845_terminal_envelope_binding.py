#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind all845 PLL physical devices before full-duration terminal-envelope analysis."""
import json, os
from collections import Counter
from pathlib import Path
import numpy as np
import cloud_pll845_native_reader as prepare
import read_pll845_all_native_transient as reader
import pll845_terminal_envelopes as envelope
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-terminal-envelope-binding'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_performed=False,
                full_capture=False,full_device_safety_accepted=False,full_phy_accepted=False)
    def save(): (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['controls']=envelope.controls();save()
        prepare.OUT=OUT/'original-reader';prepare.main()
        old=json.loads((prepare.OUT/'result.json').read_text())
        assert old['sources_unchanged'] and len(old['reader_controls']['controls'])==16
        comp_path=prepare.OUT/'prepared/composition/composition.json'
        coverage_path=prepare.OUT/'prepared/terminal-instrumentation.json'
        comp=json.loads(comp_path.read_text());cov=json.loads(coverage_path.read_text())
        assert comp['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
        assert len(comp['device_records'])==845 and len(cov['native_terminal_probes'])==2737
        assert len(comp['auxiliary_contact_models'])==4 and not comp['uncontacted_body_groups']
        contract=json.loads((prepare.OUT/'reader-contract.json').read_text())
        table=reader.contract_check(contract)
        plan=envelope.binding(comp,cov,table)
        (OUT/'terminal-envelope-plan.json').write_text(json.dumps(dict(
            composition_sha256=sha(comp_path),coverage_sha256=sha(coverage_path),
            raw_table_sha256=reader.digest(table),native_devices=845,auxiliary_contacts=4,
            terminal_probes=2737,measurements=plan,
            full_capture=False,full_device_safety_accepted=False),indent=2)+'\n')
        prefix_path=prepare.OUT/'header/native-header-prefix.bin'
        before=sha(prefix_path);prefix=prefix_path.read_bytes();actual,meta=reader.parse(prefix)
        assert actual==table
        stride=8*len(table);payload=prefix[meta['header_bytes']:]
        rows=len(payload)//stride;assert rows==46
        values=np.frombuffer(payload[:rows*stride],dtype='<f8').reshape(rows,len(table))
        observed=envelope.envelopes([r[1]for r in table],values,plan)
        observed.update(status='ACTUAL46_ROW_STARTUP_PREFIX_ONLY_NOT_FULL_CAPTURE',
                        preserved_source_prefix_sha256=before,
                        retained_partial_bytes=len(payload)%stride,partial_row_analyzed=False)
        (OUT/'actual-prefix-terminal-envelopes.json').write_text(json.dumps(observed,indent=2)+'\n')
        assert sha(prefix_path)==before
        assert all(sha(prepare.OUT/p)==h for p,h in old['outputs'].items())
        result.update(status='PASS_ALL845_PHYSICAL_TERMINAL_BINDINGS_AND11_CONTROLS_REQUIRES_FULL1US_ANALYSIS',
                      original_reader_controls=old['reader_controls'],
                      native_devices=845,auxiliary_contacts=4,physical_terminal_probes=2737,
                      model_census=dict(Counter(d['model']for d in comp['device_records'])),
                      measurements=len(plan),terminal_measurements=sum(r['kind']=='terminal'for r in plan),
                      differential_measurements=sum(r['kind']=='difference'for r in plan),
                      actual_prefix_complete_rows=rows,original_partial_bytes_retained=len(payload)%stride,
                      sources_unchanged=True,original_reader_unchanged=True,
                      source_preparation=old['prepared_source'],source_header=old['header_source'],
                      scope='Binding/control proof and preserved startup-prefix observation only. A future complete ordinary1us capture must undergo every original reader and acquisition gate and all-sample envelope analysis. Voltages do not establish current density or device reliability limits.')
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save();print(json.dumps({k:result[k]for k in ['status','full_capture','full_device_safety_accepted']}))
if __name__=='__main__':main()
