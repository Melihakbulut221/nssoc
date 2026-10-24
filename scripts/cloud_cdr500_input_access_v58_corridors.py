#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One read-only native all-primitives collision and finite-corridor survey."""
import argparse, ast, importlib.util, json, os, shutil, subprocess, sys, tarfile, traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch, sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr500-input-access-v58-corridors'
OLD='nssoc_cdr_pd500_active_input_v57'
TOP='nssoc_cdr_pd500_input_access_v58'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'

def derive(text, edits):
    original=text;changes=[]
    for a,b in edits:
        count=text.count(a);assert count>0 and b not in text,(a,count)
        text=text.replace(a,b);changes.append(dict(before=a,after=b,count=count))
    reversed_text=text
    for v in reversed(changes):
        assert reversed_text.count(v['after'])==v['count']
        reversed_text=reversed_text.replace(v['after'],v['before'])
    assert reversed_text==original
    ast.parse(text)
    return text,changes

def native(which):
    sys.path.insert(0,str(OUT/'methods'))
    module=__import__('cdr_v58_'+which)
    module.OUT=OUT;module.ROOT=ROOT
    getattr(module,'native'if which=='planes'else'recover')()

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',choices=('planes','recover'));args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native(args.native);return
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False,loaded_simulation_started=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,name):
        log=OUT/(name+'.log')
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(name=name,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-20000:],flush=True)
        assert rc==0,(name,rc)
    save()
    try:
        method=json.loads((ROOT/'scripts/cdr500-input-access-v58-methods.json').read_text())
        required=dict(method['protected'])
        required.update(json.loads((ROOT/'scripts/cdr500-input-access-v58-physical-methods.json').read_text())['protected'])
        assert all(sha(ROOT/n)==v for n,v in required.items())
        required.update(json.loads((ROOT/'scripts/cdr500-input-access-v58-corridors-methods.json').read_text())['protected'])
        assert all(sha(ROOT/n)==v for n,v in required.items())
        protected={str(ROOT/n):v for n,v in required.items()}
        pin=json.loads((ROOT/'docs/evidence/cdr500-floating-wire-cleanup-pass-20261024.json').read_text())
        selected=[n for n in pin['report']['outputs']if n.startswith('parent/')or n in ('wire/native05/wires.l2n','wire/native05/result.json','wire/probe01.py','wire/locate01.py','wire/anchors01.py','wire/dedup01.py')]
        prior,proof=reports.restore_report('cdr500-floating-wire-cleanup',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['sources_unchanged']
        assert prior['status']=='PASS_PD500_FLOATING_ROOT_CLEANUP_FULL_PHYSICAL_AND_UNCHANGED_STRICT_WIRES_REQUIRES_FRESH_RC'
        r['cleaned_physical_source']=proof
        assert sha(OUT/'source/parent/layout'/(OLD+'.gds'))=='e6ab61471595cd3635c8e2ef3922a09d6b128db0a5338fd6106f3a8e4aefc2f3'
        dpin=json.loads((ROOT/'docs/evidence/cdr500-input-path-diagnosis-pass-20261024.json').read_text())
        (OUT/'diagnosis').mkdir()
        diagnostic=OUT/'diagnosis/result.json'
        diagnostic_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-40085495203-1-cdr500-input-path-diagnosis/cdr500-input-path-diagnosis-40085495203-1.summary.json'
        fetch(diagnostic_url,dpin['summary_sha256'],diagnostic)
        observed=json.loads(diagnostic.read_text())
        assert sha(diagnostic)==dpin['summary_sha256']and observed['source_head']==dpin['source_head']
        assert observed['status']==dpin['status']and observed['sources_unchanged']
        r['owned_path_source']=dict(run=dpin['run'],source_head=dpin['source_head'],summary_sha256=sha(diagnostic),summary_url=diagnostic_url,source_archive_previously_verified=dpin['small_archive_fully_verified_in_memory'])
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(Path(n))==h for n,h in protected.items())
        source_path=ROOT/'scripts/generate_cdr500_input_access_v58.py'
        original=source_path.read_text()
        assert sha(source_path)=='9485afdff48bd00b7bd3ba0b761980c3a0d187be4fe0a3a127a93307449b17fb'
        hook='    diagnostic_active = True\n'
        insertion='    from cdr500_input_access_v58_corridors import survey\n    survey(locals(), globals())\n    return\n'
        assert original.count(hook)==1 and insertion not in original
        changed=original.replace(hook,insertion+hook)
        assert changed.replace(insertion+hook,hook)==original
        prefix='import sys\nsys.path.insert(0,'+repr(str(ROOT/'scripts'))+')\nSURVEY_ORIGINAL_GENERATOR='+repr(str(source_path))+'\n'
        changed=prefix+changed;ast.parse(changed)
        generated=OUT/'native-survey.py';generated.write_text(changed)
        r['diagnostic_derivation']=dict(original_sha256=sha(source_path),derived_sha256=sha(generated),
            sole_hook='Return into read-only survey before any candidate insertion; qualification generator remains byte-identical',
            full_source_reversal_verified=True)
        run([app,'python',generated,'--physical',OUT/'source','--diagnosis',diagnostic,'--pdk',ROOT/'pdk','--out',OUT/'survey'],'native-all-primitives-survey')
        r['geometry_survey']=json.loads((OUT/'survey/result.json').read_text())
        measurement=r['geometry_survey']
        assert measurement['status']=='PASS_READ_ONLY_ALL44_NATIVE_CANDIDATE_PRIMITIVES_AND_FINITE_CORRIDOR_SURVEY_NOT_PHYSICAL_ACCEPTANCE'
        assert measurement['primitive_count']==44 and measurement['via_count']==28 and measurement['line_count']==16
        assert measurement['exact_original_high_via4_sets']==8 and len(measurement['original_preinsertion_controls'])==8 and len(measurement['survey_controls'])==4
        choices=measurement['sampler_finite_choices']
        assert len(choices['sampler_cut_controls'])==2
        assert len(choices['groups'])==4 and len(choices['all567_combination_results'])==567
        assert all(len(g['via_candidates'])==7 and len(g['width_candidates'])==81 for g in choices['groups'])
        assert choices['all_original_Via1_Via2_four_cut_phases_preserved']and choices['all_candidates_subset_of_original_screened_maximum_owners']
        assert measurement['original_material_hierarchy_labels_unchanged']and not measurement['planned_candidate_inserted']and not measurement['candidate_gds_written']
        assert not list((OUT/'survey').rglob('*.gds'))
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(Path(n))==v for n,v in protected.items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        r.update(status='PASS_READ_ONLY_NATIVE_ALL_PRIMITIVES_CORRIDOR_DIAGNOSIS_NOT_PHYSICAL_RC_OR_ELECTRICAL_ACCEPTANCE',sources_unchanged=True)
    except BaseException as e:
        r.update(status='FAIL_READ_ONLY_NATIVE_CORRIDOR_DIAGNOSIS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
