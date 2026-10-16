#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full original actual845 1us acquisition with the measured VBIC companion fix.

All original34 probes and original100ppm/50ps/no-slip/control gates are retained.
This is not full-device safety, timestep/PVT/load/CDR or serialPHY acceptance.
"""
import hashlib,json,os,re,resource,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_tx_companion_replay as engines
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-vbic-acquisition';SOURCE=ROOT/'cloud-pll-snapshot'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
STEM='pll-snapshot-actual_parent_d2_rc-38674687038-1'
URL=BASE+'cloud-results-38674687038-1-pll-pfd-actual_parent_d2_rc/'+STEM
SUMMARY_SHA='9dfa7f360da5bc7ee8023230cf3ec1bb2da976e65db5ae33f4cd735d8637ad54'
ARCHIVE_SHA='e9056bf3eda2384204a9cfdc7b34c4725f15c0221389cb9dc937d176d2097dee'
PAIR_SHA='f5acc88de2631537a200454a915fdf5d52a1be3e181f4d4a985719df87a22e57'
PARENT_SHA='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc'

def capture(path,vectors):
    raw=path.read_bytes();names,values,meta=pll.decode_prefix(raw)
    assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
    assert set(names)=={'time',*vectors} and len(names)==35 and names[0]=='time'
    assert np.isfinite(values).all() and len(values)>3000000
    t=values[:,0];assert t[0]==0 and abs(t[-1]-1e-6)<1e-15 and np.all(np.diff(t)>0)
    assert np.max(np.diff(t))<=3.125e-13*1.00001
    return names,values,dict(**meta,raw_sha256=hashlib.sha256(raw).hexdigest(),start_s=float(t[0]),end_s=float(t[-1]),native_max_step_s=float(np.diff(t).max()))

def main(filter_cap_um=None):
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,acquisition_accepted=False,full_phy_accepted=False,full_device_safety_accepted=False,
        original_run=38674687038,paired_engine_run=38805695818,
        scope='Original actual845 parent/all8648wire records, same32models/3OSDIs, zero-sourceOP/102OFF commands, KLU/.3125ps/1us from timezero and all34original voltage probes. Only native VBIC companion engine changes. Original final800-900ns/900-1000ns100ppm/50ps/no-slip/control gates are frozen. Selected-probe measurement cannot establish full845safety, timestep/PVT/load/CDR/x4 or fullPHY acceptance.')
    if filter_cap_um is not None:
        assert type(filter_cap_um) is int and filter_cap_um in (9,11)
        result.update(filter_cap_um=filter_cap_um,physical_candidate_accepted=False,
            scope='Pre-layout filter-capacitor design experiment on frozen actual845 source. Only one cap_cmim width/length changes. Same8648baseline wire records are estimates, NOT candidate extracted parasitics. Same original1us/.3125ps/34probes/zeroOP/102OFF/engine/PDK and mandatory100ppm/50ps/no-slip/control gates. Passing requires new physical geometry, fresh RC, full device safety and PVT/load/refinement before acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['controls']=dict(reader=pll.self_test(),acquisition=pll.acquisition_controls(),cycles=pll.acquisition_cycle_controls(),readback=readback_controls())
        fetch(BASE+'cloud-results-38805695818-1-pll-vbic-replay/pll-vbic-replay-38805695818-1.summary.json',PAIR_SHA,OUT/'paired50-summary.json')
        paired=json.loads((OUT/'paired50-summary.json').read_text())
        assert paired['pristine_reproduces_original'] and paired['all_cases_complete'] and paired['protected_inputs_unchanged']
        assert paired['source_receipt']['parent_sha256']==PARENT_SHA
        engines.OUT=OUT;paths,proof=engines.restore_engines();result['runtime_provenance']=proof
        assert sha(paths['patched'])==paired['cases']['patched']['executable_sha256']=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        fetch(URL+'.json',SUMMARY_SHA,OUT/'original-summary.json');original=json.loads((OUT/'original-summary.json').read_text())
        assert original['status']=='COMPLETE_ACTUAL845_ONE_US_SELECTED_PROBES_REQUIRES_LOCK_AND_SAFETY_REVIEW'
        assert original['parent_sha256']==PARENT_SHA and original['executable_sha256']==sha(paths['packaged'])
        assert original['actual_parent_acquisition'] and original['native_stop_s']==1e-6 and len(original['vectors'])==34
        packed=OUT/'source.tar.gz';fetch(URL+'.tar.gz',ARCHIVE_SHA,packed);assert packed.stat().st_size==1318040150 and not SOURCE.exists()
        seen=set()
        with tarfile.open(packed) as archive:
            for member in archive:
                p=Path(member.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='cloud-pll-snapshot'
                assert member.name not in seen and (member.isfile() or member.isdir());seen.add(member.name)
                archive.extract(member,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==SUMMARY_SHA
        protected={}
        for row in original['inputs'].values():
            rel=Path(row['hosted_path']);assert not rel.is_absolute() and '..' not in rel.parts
            p=SOURCE/rel;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];protected[str(p)]=row['sha256']
        assert len(protected)==35
        for rel,key in [('source/bench.cir','source_deck_sha256'),('circuit.cir','relocated_deck_sha256'),('parent865.spice','parent_sha256')]:
            p=SOURCE/rel;assert sha(p)==original[key];protected[str(p)]=original[key]
        raw=SOURCE/'actual-acquisition.raw';assert raw.stat().st_size==original['captures'][raw.name]['bytes'] and sha(raw)==original['captures'][raw.name]['sha256']
        protected[str(raw)]=sha(raw)
        body=(SOURCE/'circuit.cir').read_text();assert body.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
        assert '.options reltol=1e-4 abstol=1e-12 klu' in body
        assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==original['native_off_flags']==102
        assert '.control\n' in body
        vectors=next(l[5:].split() for l in body.splitlines() if l.startswith('save '));assert vectors==original['vectors']
        expected='NSSOC actual845 original1us continuous capture\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun actual-acquisition.raw\nquit\n.endc\n.end\n'
        assert (SOURCE/'actual-acquisition.cir').read_text()==expected and (SOURCE/'spinit').read_text()=='set num_threads=1\n'
        protected[str(SOURCE/'actual-acquisition.cir')]=sha(SOURCE/'actual-acquisition.cir');protected[str(SOURCE/'spinit')]=sha(SOURCE/'spinit')
        result['protected_inputs']=protected;result['source_receipt']=dict(summary_sha256=SUMMARY_SHA,archive_sha256=ARCHIVE_SHA,paired50_sha256=PAIR_SHA,parent_sha256=PARENT_SHA)
        names,old,meta=capture(raw,vectors);result['original_capture']=meta
        original_analysis=pll.acquisition_analyzer()({n:old[:,i] for i,n in enumerate(names)})
        result['original_acquisition']=original_analysis
        assert not original_analysis['passed'],'Expected original failed acquisition must be reproduced'
        del old
        case=OUT/'patched';case.mkdir()
        for rel in ('circuit.cir','parent865.spice','spinit'):shutil.copyfile(SOURCE/rel,case/rel)
        if filter_cap_um is not None:
            from cloud_pll_filter_experiment import prepare
            candidate,receipt=prepare((case/'parent865.spice').read_text(),filter_cap_um,OUT)
            (case/'parent865.spice').write_text(candidate)
            result['filter_experiment']=receipt;save()
        readback='echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\n'
        deck=expected.replace('quit\n.endc',readback+'quit\n.endc');assert deck.replace(readback,'')==expected
        (case/'actual-acquisition.cir').write_text(deck)
        result['native_started_epoch']=time.time();result['status']='RUNNING_FILTER_CANDIDATE_ONE_US' if filter_cap_um is not None else 'RUNNING_PATCHED_ACTUAL845_ONE_US';save()
        env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        started=time.monotonic()
        with (case/'run.log').open('w') as log:
            proc=subprocess.Popen([str(paths['patched']),'-n','-b','actual-acquisition.cir'],cwd=case,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
            try:
                while True:
                    try:code=proc.wait(timeout=60);break
                    except subprocess.TimeoutExpired:
                        elapsed=time.monotonic()-started;p=case/'actual-acquisition.raw'
                        print(json.dumps(dict(native_pid=proc.pid,elapsed_s=elapsed,raw_bytes=p.stat().st_size if p.exists() else 0)),flush=True)
                        if elapsed>=19800:raise TimeoutError('Native1us exceeded hosted19800s budget; preserve incomplete capture')
            finally:
                if proc.poll() is None:proc.terminate();proc.wait(timeout=30)
        result.update(returncode=code,elapsed_s=time.monotonic()-started)
        log=(case/'run.log').read_text(errors='replace');options,diagnostics,block=backend_readback(log,'klu');(case/'native-options.txt').write_text(block)
        result.update(native_options=options,diagnostics=diagnostics);save()
        assert code==0 and not diagnostics
        for k in ('numeric','method','backend'):assert options[k]==paired['cases']['patched']['native_options'][k]
        cn,cv,cap=capture(case/'actual-acquisition.raw',vectors);assert cn==names
        result['capture']=cap;result['zero_source_operating_point']=pll.zero_source_operating_point((case/'op.raw').read_bytes(),vectors)
        columns={n:cv[:,i] for i,n in enumerate(cn)}
        result['independent_acquisition']=pll.acquisition_analyzer()(columns)
        result['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(columns,result['independent_acquisition'])
        result['original_gate_passed']=bool(result['independent_acquisition']['passed'])
        assert all(sha(Path(p))==d for p,d in protected.items());result['protected_inputs_unchanged']=True
        if filter_cap_um is not None:
            from cloud_pll_filter_experiment import validate_delta
            validate_delta((SOURCE/'parent865.spice').read_text(),(case/'parent865.spice').read_text(),filter_cap_um)
            result['candidate_gate_passed']=result['original_gate_passed']
        result['status']='COMPLETE_FILTER_CANDIDATE_ONE_US_NOT_PHYSICAL_ACCEPTANCE' if filter_cap_um is not None else 'COMPLETE_PATCHED_ACTUAL845_ONE_US_MEASUREMENT_NOT_PHY_ACCEPTANCE'
        print(json.dumps(dict(status=result['status'],original_gate_passed=result['original_gate_passed'],elapsed_s=result['elapsed_s'])),flush=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
