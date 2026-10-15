#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare original full34ns 32:1 captures; never infer full PHY acceptance."""
import argparse,copy,json,os,re
from pathlib import Path
from cloud_verified_parts import extract_verified,controls
from cloud_tx_stream import read_streamed_wave
from analyze_cloud_assembled_wave import step_metrics
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tree32-step-compare'

def compatible(coarse,fine,ca,cb):
    for result,step in ((coarse,.5),(fine,.25)):
        assert result['status']=='COMPLETE_FULL34NS_TREE32_COMPONENT_SCREEN_NOT_PHYSICAL_OR_PHY_ACCEPTANCE'
        assert result['component_screen_passed'] and result['review']['all_engineering_gates_passed']
        assert result['protected_inputs_unchanged'] and result['returncode']==0 and not result['diagnostics']
        assert result['tmax_ps']==step
    for key in ('backend','executable_sha256','backend_prerequisite','source_receipt','protected_inputs'):
        assert coarse[key]==fine[key],('Different physical/runtime provenance',key)
    for key in ('numeric','method'):assert coarse['native_options'][key]==fine['native_options'][key]
    a=copy.deepcopy(ca);b=copy.deepcopy(cb)
    assert a['condition']['step_ps']==.5 and b['condition']['step_ps']==.25
    b['condition']['step_ps']=.5
    assert a==b,'Changed bits, vectors, circuit or engineering contract'
    assert a['streams']==32 and a['fault']=='none'
    return dict(only_maximum_time_step_differs=True,original_full_window_and_gates_unchanged=True)

def restore(run,summary_sha,manifest_sha,backend,step):
    assert run>0 and backend in ('sparse','klu') and step in ('0.5','0.25')
    for value in (summary_sha,manifest_sha):assert re.fullmatch(r'[a-f0-9]{64}',value)
    stem=f'vbic-tree32-full-{backend}-{step}-{run}-1'
    base=f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{run}-1-vbic-tree32-full-{backend}-{step}/'
    directory=OUT/step;directory.mkdir();summary_path=directory/'summary.json';manifest_path=directory/'parts.json'
    fetch(base+stem+'.summary.json',summary_sha,summary_path);result=json.loads(summary_path.read_text())
    fetch(base+stem+'.parts.json',manifest_sha,manifest_path);manifest=json.loads(manifest_path.read_text())
    assert manifest['stem']==stem and manifest['source_directory']=='cloud-vbic-tree32-full'
    assert result['backend']==backend and result['tmax_ps']==float(step)
    assert result['component_screen_passed'] and result['protected_inputs_unchanged'],'Failed full capture cannot be adopted'
    for i,part in enumerate(manifest['parts']):
        assert part['index']==i and part['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        fetch(base+part['name'],part['sha256'],directory/part['name'])
    expected={n:result['outputs'][n] for n in ('native/wave.raw','native/contract.json','native/bench.cir','native/native-options.txt')}
    expected['result.json']=summary_sha
    proof=extract_verified(manifest,directory,directory/'restored',expected)
    for part in manifest['parts']:(directory/part['name']).unlink()
    contract=json.loads((directory/'restored/native/contract.json').read_text())
    t,v,cap=read_streamed_wave(directory/'restored/native/wave.raw',contract['vectors'],34e-9,float(step)*1e-12)
    return result,contract,(t,v),dict(run=run,summary_sha256=summary_sha,manifest_sha256=manifest_sha,restore=proof,capture=cap)

def main(args):
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,full_phy_accepted=False,source_head=os.environ['GITHUB_SHA'],scope='Full original34ns, every original vector/sample/edge/energy gate. Frozen32:1 per-macroRC component only: imposed clocks and ideal intermacro wires remain. No whole-tree physical/PVT/PLL/CDR/x4/mainchip timing acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        a,ca,wa,pa=restore(args.coarse_run,args.coarse_sha,args.coarse_parts_sha,args.backend,'0.5');result['coarse']=pa;save()
        b,cb,wb,pb=restore(args.fine_run,args.fine_sha,args.fine_parts_sha,args.backend,'0.25');result['fine']=pb
        result['provenance']=compatible(a,b,ca,cb)
        result['step_comparison']=step_metrics(wa,wb,ca)
        result['component_numerical_screen_passed']=result['step_comparison']['passed']
        result['status']='COMPLETE_TREE32_FULL_WINDOW_NUMERICAL_COMPARISON_NOT_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');p.add_argument('--backend',choices=['sparse','klu'])
    for name in ('coarse','fine'):
        p.add_argument('--'+name+'-run',type=int);p.add_argument('--'+name+'-sha');p.add_argument('--'+name+'-parts-sha')
    a=p.parse_args()
    if a.controls_only:
        assert os.environ.get('GITHUB_ACTIONS')=='true';print(json.dumps(controls()))
    else:main(a)
