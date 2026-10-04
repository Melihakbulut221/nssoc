# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import characterize_pcie_clock_trim_stream_v3 as m

ADVISORY = ('Warning: memory required (2.4885 GB), made of\n'
            '       167 nodes and approximately 2.00000e6 time steps,\n'
            '       is more than the DRAM memory available (2.393 GB)!\n'
            '       Swapping data to SSD may slow down the simulation.\n')


def classify(monkeypatch,log,**change):
    def native(log,cap,hbts):
        m.require(m.base.old.diagnostics(log)['clean'],'Other native diagnostic')
        return {'structural_control':'tests use separate actual native replay for structural checks'}
    monkeypatch.setattr(m.tiny,'native_log',native)
    args=dict(log=log,capture=dict(step_s=.5e-12,stop_s=1e-6,columns=list(range(167))),hbts={},runtime_sha=m.NG47_SHA,step=.5e-12,returncode=0)
    args.update(change)
    return m.classify_log(**args)


def test_exact_advisory_classified_but_original_strict_failure_preserved(monkeypatch):
    r=classify(monkeypatch,'header\n'+ADVISORY+'complete\n')
    assert not r['original_strict_diagnostics']['clean']
    assert len(r['informational_memory_advisories'])==1
    assert not r['log_file_modified']


def test_clean_native_needs_no_advisory(monkeypatch):
    assert classify(monkeypatch,'complete\n')['original_strict_diagnostics']['clean']


@pytest.mark.parametrize('old,new',[('2.4885','2.5000'),('167 nodes','166 nodes'),('2.00000e6','4.00000e6'),('2.393','3.393'),('Swapping data','Assuming data'),('Warning:','Error:')])
def test_only_exact_source_attributed_advisory(monkeypatch,old,new):
    with pytest.raises(ValueError):classify(monkeypatch,ADVISORY.replace(old,new))


@pytest.mark.parametrize('warning',['Warning: thermal voltage exceeds range','Error: bad vector','thermal nan','singular matrix','gmin stepping','timestep too small','aborted'])
def test_all_other_native_diagnostics_remain_fatal(monkeypatch,warning):
    with pytest.raises(ValueError):classify(monkeypatch,ADVISORY+warning+'\n')


def test_duplicate_advisory_rejected(monkeypatch):
    with pytest.raises(ValueError):classify(monkeypatch,ADVISORY*2)


@pytest.mark.parametrize('change',[dict(runtime_sha='0'*64),dict(returncode=1),dict(step=.25e-12)])
def test_actual_native_identity_not_waived(monkeypatch,change):
    with pytest.raises(ValueError):classify(monkeypatch,ADVISORY,**change)


def periodic():
    t=np.linspace(0,12e-9,24001);clock=np.sin(2*np.pi*8e9*t)
    thermal={f'state{i}':10+.05*np.sin(2*np.pi*8e9*t+i*.2) for i in range(53)}
    legacy=dict(checks=dict(final_four_frequency_means_within100ppm=True))
    return t,clock,thermal,legacy


def test_periodic_all53_phase_means_pass_original_numeric_bounds():
    t,c,d,l=periodic();r=m.phase_convergence(t,c,d,12e-9,l)
    assert r['converged'] and r['original_endpoint_metric_preserved']
    assert r['rate_limit_k_per_ns']==.01 and r['nonincrease_tolerance_k_per_ns']==1e-5


@pytest.mark.parametrize('fault',['drift','late_drift','runaway','missing_node','constant_clock','incomplete_tail','clock_frequency_fail'])
def test_phase_gate_rejects_faults(fault):
    t,c,d,l=periodic()
    if fault=='drift':d['state52']+=.02*t*1e9
    elif fault=='late_drift':d['state52']+=.04*np.maximum(t-10e-9,0)*1e9
    elif fault=='runaway':d['state52']+=.00001*np.exp(t/1e-9)
    elif fault=='missing_node':d.pop('state52')
    elif fault=='constant_clock':c[:]=1
    elif fault=='incomplete_tail':t=t[:-5];c=c[:-5];d={k:v[:-5] for k,v in d.items()}
    elif fault=='clock_frequency_fail':l['checks']['final_four_frequency_means_within100ppm']=False
    if fault in ('missing_node','constant_clock','incomplete_tail'):
        with pytest.raises(ValueError):m.phase_convergence(t,c,d,12e-9,l)
    else:assert not m.phase_convergence(t,c,d,12e-9,l)['converged']


def test_original_lifecycle_is_exact_alias_and_not_a_new_watchdog():
    assert m.lifecycle.sha(m.lifecycle.__file__)==m.LIFECYCLE_SHA
    assert 'elapsed_watchdog_seconds=None' in Path(m.lifecycle.__file__).read_text()


def test_second_native_cannot_start_after_failed_first_replay(tmp_path,monkeypatch):
    import json
    first=tmp_path/'first';first.mkdir()
    (first/'result.json').write_text(json.dumps(dict(status='FAIL_V3_FIRST_CAPTURE_SCREEN')))
    monkeypatch.setattr(m.lifecycle,'native_wait',lambda *a,**k:pytest.fail('Native must not start'))
    with pytest.raises(ValueError):m.run_second(first,tmp_path/'parent',tmp_path/'new','not-launched')
    assert not (tmp_path/'new').exists()


@pytest.mark.parametrize('status',['FAIL_V3_FIRST_CAPTURE_SCREEN','ERROR_V3_INCOMPLETE'])
def test_cli_failure_exits_nonzero(monkeypatch,status):
    monkeypatch.setattr(sys,'argv',['test','replay-first','--prior','unused','--out','unused'])
    monkeypatch.setattr(m,'replay_first',lambda *a:dict(status=status))
    with pytest.raises(SystemExit) as e:m.main()
    assert e.value.code==1


@pytest.mark.parametrize('name',['bench.cir','circuit.spice','spinit','producer.py'])
def test_generated_inputs_reject_real_file_mutation(tmp_path,name):
    expected={tmp_path/n:'exact '+n+'\n' for n in ['bench.cir','circuit.spice','spinit','producer.py']}
    for p,text in expected.items():p.write_text(text)
    pins=m.bind_generated(expected);m.verify_pins(pins)
    (tmp_path/name).write_text(expected[tmp_path/name]+'mutated\n')
    with pytest.raises(ValueError):m.verify_pins(pins)
    with pytest.raises(ValueError):m.bind_generated(expected)


@pytest.mark.parametrize('name',['run.log','initial-op.dat','bench.cir','spinit'])
def test_sealed_original_outputs_reject_mutation(tmp_path,monkeypatch,name):
    import json
    import hashlib
    root=tmp_path/'native';root.mkdir();proofpath=tmp_path/'proof.json';case='fixed'
    names=['result.json','producer.py','spinit',*(case+'/'+n for n in ['run.log','initial-op.dat','bench.cir',m.base.prior.FILE,'capture/header.bin','capture/trailer.bin','capture/parts/parts.json'])]
    inventory={}
    for n in names:
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('exact '+n+'\n');inventory[n]=dict(bytes=p.stat().st_size,sha256=m.sha(p))
    proof=dict(native_result_sha256=m.phase.RESULT_SHA,source_inputs_rehashed=101,case=dict(name=case),native_output_inventory=inventory)
    proofpath.write_text(json.dumps(proof));monkeypatch.setattr(m,'PRIOR_REVIEW_PATH',proofpath);monkeypatch.setattr(m,'PRIOR_REVIEW_SHA',hashlib.sha256(proofpath.read_bytes()).hexdigest())
    pins=m.bind_prior_outputs(root);m.verify_pins(pins)
    path=root/(name if name=='spinit' else case+'/'+name);path.write_text(path.read_text()+'mutated\n')
    with pytest.raises(ValueError):m.bind_prior_outputs(root)
    with pytest.raises(ValueError):m.verify_pins(pins)
