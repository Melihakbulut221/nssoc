#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only diagnostic on the unchanged complete rejected PLL capture."""
import hashlib, json, os, signal, sys, threading, traceback
from pathlib import Path
import cloud_pll845_contiguous_driver as base
import pll845_vctrl_wire_observation as wires
from run_cloud_tx_layout_repair import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-vctrl-wire'
METHOD=ROOT/'scripts/pll845-vctrl-wire-method.json'

def verified():
    method=json.loads(METHOD.read_text())
    for p,h in method['new_files'].items():assert sha(ROOT/p)==h, ('Method source drift',p)
    original=base.verified()
    assert sha(base.MANIFEST)==method['original_reader_method_sha256']
    return method,original

def prepare():
    values=wires.inputs()
    binding,controls=wires.binding_controls(*values[:4])
    controls['numeric']=wires.numeric_controls()
    return binding,controls,values[4]

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    method,original=verified()
    binding,controls,prior=prepare()
    if '--controls' in sys.argv:
        print(json.dumps(dict(status='PASS_ACTUAL_SOURCE_WIRE_BINDING_AND_NEGATIVE_CONTROLS_NOT_CURRENT_MEASUREMENT',
                              controls=controls,terminals=len(binding['terminals']),
                              network_nodes=len(binding['modeled_network_nodes']))))
        return
    spec=json.loads(os.environ['SOURCE_CHECKPOINT'])
    assert spec==prior['source_checkpoint'], 'Only original completed immutable capture'
    OUT.mkdir(exist_ok=False)
    base.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],acquisition_accepted=False,
           full_phy_accepted=False,full_device_safety_accepted=False,qualified_pex=False,
           native_activation_performed=False,controls=controls,source_checkpoint=spec)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    (OUT/'wire-current-plan.json').write_text(json.dumps(binding,indent=2)+'\n')
    (OUT/'method.json').write_bytes(METHOD.read_bytes())
    def cached(names,values):
        data=base.cached_columns(names,values)
        r['wire_observation']=wires.observe(names,values,binding,OUT,base.phase)
        save()
        return data
    read=base.adapted(base.reader,original['reader_edits'],{'_phase':base.phase,'_cached_columns':cached})
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,base.interrupted)
    timer=threading.Thread(target=base.heartbeat,daemon=True);timer.start()
    base.phase('START_ORIGINAL_CAPTURE_WIRE_CURRENT_DIAGNOSIS')
    try:
        error=None
        try:read()
        except AssertionError as caught:error=caught
        p=ROOT/'cloud-pll845-sparse-completed-reader/result.json'
        observed=json.loads(p.read_text())
        assert error is not None, 'Expected original failed acquisition unchanged'
        assert observed['status']=='REJECTED_ORIGINAL_FULL845_ACQUISITION_GATES'
        assert observed['full_capture'] and observed['verified_ordinary_source']
        assert observed['capture']['raw_sha256']==wires.RAW_SHA
        assert observed['independent_acquisition']==prior['independent_acquisition']
        assert observed['cycle_diagnosis']==prior['cycle_diagnosis']
        assert 'wire_observation' in r
        r.update(status='COMPLETE_MODELED_WIRE_CURRENT_DIAGNOSIS_ORIGINAL_ACQUISITION_STILL_REJECTED',
                 full_capture=True,raw_sha256=wires.RAW_SHA,
                 exact_original_acquisition_and_cycle_results=True,
                 original_acquisition_error=repr(error))
        base.phase('COMPLETE_DIAGNOSTIC_ORIGINAL_ACQUISITION_REMAINS_REJECTED')
    except BaseException as e:
        r.update(status='FAIL_WIRE_CURRENT_DIAGNOSTIC',error=repr(e),traceback=traceback.format_exc())
        raise
    finally:
        base._stopped.set()
        p=ROOT/'cloud-pll845-sparse-completed-reader/result.json'
        if p.exists():(OUT/'original-reader-result.json').write_bytes(p.read_bytes())
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'}
        save()
        print(json.dumps({k:r[k] for k in ('status','acquisition_accepted','full_phy_accepted')}))
if __name__=='__main__':main()
