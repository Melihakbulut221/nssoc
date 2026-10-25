#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Simulator-free cloud proof of exact334 model/source/physical role bindings."""
import argparse,hashlib,json,os,subprocess,traceback
from pathlib import Path
import tx_phase_reset334_loaded_binding as binding
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-phase-reset334-loaded-binding'
METHOD='scripts/tx-phase-reset334-loaded-binding-methods.json'
SOURCE='hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice'
PHYSICAL=dict(run=40120130880,head='2e1f26e9c4fdf37d63433a0c859c2d305db3486b',release=422903518,
 summary_asset=672983363,summary_sha256='5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913',
 group='tx-phase-reset244-physical')
RC=dict(run=40125124288,head='3cb1350dcbda569ac0073b0211cdaa2a47dc70ed',release=422935028,
 group='tx-phase-reset334-mim-precision',summary_asset=673109002,
 summary_sha256='a11da5bb7ee22134f9373d43a1fffda9d1f6538877b440031ffd910adec56bcf',
 parts_sha256='258a9cbc9e122b64276c390e94ff3df079f35b94be0fd01e867cf69e73eaa3a5')
def sha(p):return binding.digest(Path(p).read_bytes())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def source_pins():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def source_controls():
    m=source_pins();text=(ROOT/SOURCE).read_text()
    pub=publication.controls();assert len(pub['rejected'])==17
    rows={p:binding.source_rows(text,p)for p in ('p','n')}
    assert all(len(r)==244 for r in rows.values())
    try:binding.source_rows(text+'\n','p')
    except AssertionError:pass
    else:raise AssertionError('Accepted changed original244 source')
    return dict(status='PASS_SOURCE_PINS_AND_BOTH_ORIGINAL244_FLATTENINGS_NOT_NATIVE_BINDING',
      protected_files=len(m['protected']),source_device_counts={p:len(r)for p,r in rows.items()},
      changed_original_source_rejected=True,publication_faults=pub,actual_native_binding_executed=False,**binding.FLAGS)
def summary(spec):
    run=api('actions/runs/'+str(spec['run']))
    assert run['head_sha']==spec['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    release=api('releases/'+str(spec['release']))
    assert release['tag_name']=='cloud-results-'+str(spec['run'])+'-1-'+spec['group']
    assert api('git/ref/tags/'+release['tag_name'])['object']['sha']==spec['head']
    asset=next(a for a in release['assets']if a['id']==spec['summary_asset'])
    assert asset['digest']=='sha256:'+spec['summary_sha256']
    raw=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/releases/assets/'+str(spec['summary_asset']),'-H','Accept: application/octet-stream'])
    assert len(raw)==asset['size']and binding.digest(raw)==spec['summary_sha256']
    d=json.loads(raw);assert d['source_head']==spec['head']
    return raw,d
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    source_pins();OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING_SOURCE_NATIVE334_BINDING',source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),validation_errors=[],variants={},simulator_invoked=False,
      new_extraction_performed=False,**binding.FLAGS)
    try:
        tag,head=publication.context('tx-phase-reset334-loaded-binding',os.environ)
        result['release_prerequisite']=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
        pbytes,physical=summary(PHYSICAL);rbytes,rc=summary(RC)
        (OUT/'physical.summary.json').write_bytes(pbytes);(OUT/'RC.summary.json').write_bytes(rbytes)
        assert physical['validation_errors']==[]and physical['sources_unchanged']
        assert rc['validation_errors']==[]and rc['sources_unchanged']and rc['both_polarities_and_orders_verified']
        assert rc['native_RC_and_device_records_equal_in_both_orders']
        selected=[p+'/'+suffix for p in ('p','n')for suffix in ('source/native.json','composition/composition.json','composition/reset334-wire.spice')]
        restored,proof=reports.restore_report(RC['group'],RC['run'],RC['summary_sha256'],RC['parts_sha256'],OUT/'qualified-rc',selected)
        assert restored==rc
        result['qualified_archive']=proof
        for p in ('p','n'):
            base=OUT/'qualified-rc'/p
            native=json.loads((base/'source/native.json').read_text())
            comp=json.loads((base/'composition/composition.json').read_text())
            model=(base/'composition/reset334-wire.spice').read_text()
            v=physical['variants'][p]
            assert comp==rc['polarities'][p]['composition']
            assert comp['model_sha256']==binding.MODELS[p]
            case=dict(text=(ROOT/SOURCE).read_text(),sign=p,geometry=v['generation'],planes=v['wires']['anchors'],
                      native=native,composition=comp,model_text=model)
            proof=binding.controls(case);write(OUT/(p+'-bindings-and-controls.json'),proof)
            assert len(proof['positive']['compact_roles'])==244 and len(proof['positive']['hbt_roles'])==106
            assert len(proof['negative_controls'])==20 and proof['controls_passed']
            result['variants'][p]=dict(status='PASS_BOTH_SOURCE_AND_ACTUAL334_MODEL_ROLE_BINDING_WITH20_FAULTS',
                compact_source_devices=244,native_model_devices=334,hbt_devices=106,finite_body_contacts=90,
                actual_internal_probe_pairs=proof['positive']['fixed_internal_probes'],
                negative_controls=proof['negative_controls'],model_sha256=sha(base/'composition/reset334-wire.spice'),
                binding_result_sha256=sha(OUT/(p+'-bindings-and-controls.json')))
        source_pins();result['sources_unchanged']=True
        result['status']='PASS_TWO_PHYSICAL334_ROLE_BINDINGS_NOT_LOADED_ELECTRICAL_ACCEPTANCE'
        result['actual_native_binding_executed']=True
    except BaseException as error:
        result['status']='FAIL_SOURCE_NATIVE334_BINDING';result['validation_errors'].append(dict(error=repr(error),traceback=traceback.format_exc()))
        raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        write(OUT/'result.json',result)
        print(json.dumps(dict(status=result['status'],result_sha256=sha(OUT/'result.json'),
          validation_errors=result['validation_errors'],variant_status={p:r['status']for p,r in result['variants'].items()},
          simulator_invoked=False,postlayout_electrical_accepted=False,full_PHY_accepted=False)),flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source-controls',action='store_true');args=a.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.source_controls:print(json.dumps(source_controls(),indent=2))
    else:main()
