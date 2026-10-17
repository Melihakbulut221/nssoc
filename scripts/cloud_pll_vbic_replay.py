#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Paired native VBIC engines on the unchanged actual845 physical PLL parent.

The exact50ns original495 probes are retained. This cannot pass1us acquisition.
"""
import hashlib,json,os,re,resource,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_tx_companion_replay as engines
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from cloud_tx_step_factorial import wave_difference
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-vbic-replay'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38672412524-1-pll-pfd-actual_parent_d2_rc/'
STEM='pll-snapshot-actual_parent_d2_rc-38672412524-1'
SUMMARY_SHA='1d0e5874f38e796ba3391d575b70a2bb370e0a9e5500013a161b6212016393b5'
ARCHIVE_SHA='fe8d9619f48add85c9819c86cf3f86a2efefeef9e26beec862e7ad995cb17752'


def restore(packaged):
    source=ROOT/'cloud-pll-snapshot';assert not source.exists()
    summary_path=OUT/'original-summary.json';fetch(BASE+STEM+'.json',SUMMARY_SHA,summary_path);summary=json.loads(summary_path.read_text())
    assert summary['status']=='COMPLETE_ACTUAL845_PARENT_NATIVE50_CAPTURE_NOT_LOCK_SAFETY_OR_PVT_ACCEPTANCE'
    assert summary['executable_sha256']==sha(packaged) and len(summary['vectors'])==495
    assert summary['pfd_replacement']['actual_parent_layout_rc'] and summary['pfd_replacement']['total_native_instances']==845
    packed=OUT/'source.tar.gz';fetch(BASE+STEM+'.tar.gz',ARCHIVE_SHA,packed);assert packed.stat().st_size==563519069
    seen=set()
    with tarfile.open(packed) as archive:
        for entry in archive:
            name=Path(entry.name)
            assert not name.is_absolute() and '..'not in name.parts and name.parts[0]=='cloud-pll-snapshot'
            assert entry.name not in seen and (entry.isfile() or entry.isdir());seen.add(entry.name)
            archive.extract(entry,ROOT,filter='data')
    packed.unlink();assert sha(source/'result.json')==SUMMARY_SHA
    protected={}
    for old,row in summary['inputs'].items():
        rel=Path(row['hosted_path']);assert not rel.is_absolute() and '..'not in rel.parts
        p=source/rel;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];protected[str(p)]=row['sha256']
    assert len(protected)==35
    for rel,key in [('source/bench.cir','source_deck_sha256'),('circuit.cir','relocated_deck_sha256'),('parent865.spice','parent_sha256')]:
        p=source/rel;assert sha(p)==summary[key];protected[str(p)]=summary[key]
    assert summary['parent_sha256']=='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc'
    assert sha(source/'candidate.cir.log')==summary['native_runs'][0]['log_sha256']
    assert sha(source/'candidate.raw')==summary['captures']['candidate.raw']['sha256']
    for rel in ('candidate.cir','spinit'):protected[str(source/rel)]=sha(source/rel)
    body=(source/'circuit.cir').read_text()
    assert body.count('.tran 3.125e-13 5e-08 0 3.125e-13')==1
    assert '.options reltol=1e-4 abstol=1e-12 klu' in body
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==summary['native_off_flags']==102
    return source,summary,protected


def capture(path,vectors):
    raw=path.read_bytes();names,values,meta=pll.decode_prefix(raw)
    assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows']
    assert set(names)=={'time',*vectors} and len(names)==496 and names[0]=='time'
    assert np.isfinite(values).all() and len(values)>150000
    t=values[:,0];assert t[0]==0 and abs(t[-1]-50e-9)<1e-15 and np.all(np.diff(t)>0)
    assert np.max(np.diff(t))<=3.125e-13*1.00001
    return names,values,dict(**meta,raw_sha256=hashlib.sha256(raw).hexdigest(),start_s=float(t[0]),end_s=float(t[-1]),native_max_step_s=float(np.diff(t).max()))


def wave(values,names):return values[:,0],{n:values[:,i] for i,n in enumerate(names) if i}


def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,acquisition_accepted=False,full_phy_accepted=False,cases={},
        original_parent_source_run=38672412524,
        scope='Exact actual845 physical parent and original32models/3OSDIs, same .3125ps/50ns, KLU/options, zero-sourceOP and102OFF commands; all495original voltage probes. Paired engine experiment only; original1us100ppm/50ps/slip/VCTRL acquisition and full845 safety/PVT/load/CDR/x4/mainchip remain OPEN.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['readback_controls']=readback_controls();result['native_reader_controls']=pll.self_test()
        engines.OUT=OUT;paths,provenance=engines.restore_engines();result['runtime_provenance']=provenance
        source,original,protected=restore(paths['packaged']);result['protected_inputs']=protected
        result['source_receipt']=dict(summary_sha256=SUMMARY_SHA,archive_sha256=ARCHIVE_SHA,parent_sha256=original['parent_sha256'],vectors=original['vectors'],original_native_off_commands=original['native_off_flags'])
        names,old,receipt=capture(source/'candidate.raw',original['vectors']);result['original_capture']=receipt
        text=(source/'candidate.cir').read_text();assert text.count('quit\n.endc')==1
        readback='echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\n'
        deck=text.replace('quit\n.endc',readback+'quit\n.endc');assert deck.replace(readback,'')==text
        pristine=None
        for variant in ('pristine','patched'):
            if variant=='patched':assert result.get('pristine_reproduces_original')
            case=OUT/variant;case.mkdir()
            for rel in ('circuit.cir','parent865.spice','spinit'):shutil.copyfile(source/rel,case/rel)
            (case/'candidate.cir').write_text(deck)
            row=dict(variant=variant,executable_sha256=sha(paths[variant]),complete=False,accepted=False);result['cases'][variant]=row;save()
            try:
                env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
                def limits():
                    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
                started=time.monotonic()
                with (case/'run.log').open('w') as log:proc=subprocess.run([str(paths[variant]),'-n','-b','candidate.cir'],cwd=case,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,timeout=7200)
                row.update(returncode=proc.returncode,elapsed_s=time.monotonic()-started)
                log=(case/'run.log').read_text(errors='replace');row['native_options'],row['diagnostics'],block=backend_readback(log,'klu');(case/'native-options.txt').write_text(block)
                assert proc.returncode==0 and not row['diagnostics'],'Native execution/diagnostic failure'
                cn,cv,cap=capture(case/'candidate.raw',original['vectors']);assert cn==names
                row['capture']=cap;row['zero_source_operating_point']=pll.zero_source_operating_point((case/'op.raw').read_bytes(),original['vectors'])
                row['pfd_terminal_measurements']=pll.pfd_terminal_diagnosis((case/'parent865.spice').read_text(),cn,cv)
                row['complete']=True
                if variant=='pristine':
                    row['original_fixed_bounds_comparison']=pll.compare((names,old),(cn,cv))
                    row['whole50ns_comparison']=wave_difference(wave(old,names),wave(cv,cn),names[1:],end=50e-9)
                    result['pristine_reproduces_original']=bool(row['original_fixed_bounds_comparison']['passed'] and row['whole50ns_comparison']['worst_voltage_difference_v']<=pll.MAX_NODE_ERROR_V)
                    pristine=cv
                else:
                    assert row['native_options']['numeric']==result['cases']['pristine']['native_options']['numeric'] and row['native_options']['method']==result['cases']['pristine']['native_options']['method']
                    row['whole50ns_engine_effect']=wave_difference(wave(pristine,names),wave(cv,cn),names[1:],end=50e-9)
                    signal={n:cv[:,i] for i,n in enumerate(cn)};t=cv[:,0]
                    row['edge_observations']={label:pll.rising(t,y,threshold).tolist() for label,y,threshold in [('vco',signal['v(clkp)']-signal['v(clkn)'],0.),('feedback',signal['v(fb)'],1.25),('reference',signal['v(reference)'],1.25)]}
                    row['control_range_v']=[float(signal['v(vctrl)'].min()),float(signal['v(vctrl)'].max())]
                    del cv
            except Exception as error:row['error']=repr(error)
            save();print(json.dumps(dict(case=variant,complete=row['complete'],error=row.get('error'),elapsed_s=row.get('elapsed_s'))),flush=True)
        assert all(sha(Path(p))==d for p,d in protected.items());result['protected_inputs_unchanged']=True
        result['all_cases_complete']=all(c['complete'] and not c.get('error') for c in result['cases'].values())
        result['status']='COMPLETE_ACTUAL845_PAIRED_ENGINE_DIAGNOSIS_NOT_ACQUISITION_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()

if __name__=='__main__':main()
