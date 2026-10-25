#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only replay of three authenticated rejected native captures; no simulator."""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,tarfile,traceback
from pathlib import Path,PurePosixPath
import numpy as np
import cloud_cdr500_v58_loaded as original
import cloud_tx_stream as stream
import cdr_v58_current_ledger as rows
from cloud_verified_parts import JoinedParts
from cloud_chunked_results import verify_parts
ROOT=Path(__file__).resolve().parents[1]
REQ='docs/evidence/cdr500-v58-rejected-capture-readback-requirements-20261024.json'
METHOD='scripts/cdr-v58-current-ledger-methods.json'
RUN=40108285374
HEAD='d92a3367a1013d1071125b753ec4f65ae4ec813b'
JOBS={'nominal_early':120914806150,'nominal_late':120914806173,'hot_early':120914806160}
SELECT=['native/wave.raw','native/native.log','native/bench.cir','native/original-bench.cir','native/op.dat',
        'composed/composition/pd500-mim-wire.spice','composed/composition/composition.json','planes/native-planes.json']
API='repos/Melihakbulut221/nssoc/'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def api(path):
    return json.loads(subprocess.check_output(['gh','api',API+path,'--allow-escape-sequences']))

def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for path,digest in m['protected'].items():assert sha(ROOT/path)==digest,path
    old=json.loads((ROOT/'scripts/cdr500-v58-loaded-methods.json').read_text())
    for path,digest in old['protected'].items():assert sha(ROOT/path)==digest,path
    assert m['native_simulation_authorized'] is False and m['original_source']==HEAD
    return m

def identity(run,job,case):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']=='failure'
    assert run['path']=='.github/workflows/cdr500-v58-loaded-cloud.yml' and run['event']=='workflow_dispatch'
    assert job['id']==JOBS[case] and job['run_id']==RUN and job['run_attempt']==1 and job['head_sha']==HEAD
    assert job['name']=='loaded ('+case+')' and job['status']=='completed' and job['conclusion']=='failure'

def validate_asset(meta,pin):
    for key in ('id','name','size','digest'):
        assert meta[key]==pin[key],('asset identity',key)
    assert meta['state']=='uploaded' and pin['digest'].startswith('sha256:')

def asset(pin,destination):
    meta=api('releases/assets/'+str(pin['id']));validate_asset(meta,pin)
    with destination.open('xb') as f:
        proc=subprocess.run(['gh','api',API+'releases/assets/'+str(pin['id']),'-H','Accept: application/octet-stream','--allow-escape-sequences'],stdout=f)
    assert proc.returncode==0 and destination.stat().st_size==pin['size'] and sha(destination)==pin['digest'][7:]
    return meta

def summary(report,pin):
    assert report['source_head']==HEAD and report['case']==pin['case']
    assert report['status']==pin['original_status']=='REJECTED_WHOLE_MIM_PD500_LOADED'
    assert report['error']==pin['original_error'] and report['sources_unchanged']
    assert report['returncode']==0 and not report['diagnostics'] and report['native_flags_verified']==124
    assert report['zero_source_op_maximum']==0 and not report['actual_fault_detected']
    assert not any(report[k] for k in ('accepted','full_phy_accepted','cdr_accepted','qualified_pex','closed_loop'))
    assert report['outputs']['native/wave.raw']==pin['original_wave_sha256']
    assert report['outputs']['native/native.log']==pin['original_log_sha256']
    assert report['outputs']['composed/composition/pd500-mim-wire.spice']==pin['model_sha256']
    assert all(report['raw_capture'][k]==v for k,v in pin['raw_capture'].items())
    assert len(report['vectors'])==len(set(report['vectors']))==1151
    assert len(report['source_bits'])==256 and set(report['source_bits'])=={0,1}
    assert hashlib.sha256(bytes(report['source_bits'])).hexdigest()==report['source_bits_sha256']
    assert report['source_bits']==original.primitive.prbs(0x7f)
    assert report['data_offset_s']==(-.15 if pin['case'].endswith('_early') else .15)*rows.UI
    assert not report['devices_passed'] and not report['data_passed'] and not report['vi']['passed']
    assert len(report['binding_controls']['rejected'])==13
    assert report['traceback'].endswith("AssertionError: Actual whole-wire retimed sampling, loaded phase/current or device gate failed\n")

def manifest_valid(m,pin):
    assert m==pin['parts']['manifest'],'Changed original parts or concatenation order'
    assert m['source_directory']=='cloud-cdr500-v58-loaded-'+pin['case']
    assert m['stem']=='cdr500-v58-loaded-'+pin['case']+'-'+str(RUN)+'-1'
    assert [p['index'] for p in m['parts']]==list(range(len(m['parts'])))
    assert len({p['name'] for p in m['parts']})==len(m['parts'])
    for i,p in enumerate(m['parts']):
        assert p['name']==m['stem']+'.tar.gz.part'+str(i).zfill(4)
    assert sum(p['bytes'] for p in m['parts'])==m['bytes']

def member_name(name,prefix):
    assert isinstance(name,str) and '\\' not in name and '\x00' not in name and ':' not in name
    p=PurePosixPath(name)
    assert str(p)==name and not p.is_absolute() and '..' not in p.parts and p.parts[0]==prefix
    return str(p.relative_to(prefix))

def restore(manifest,folder,destination,report,summary_sha):
    assert not destination.exists();destination.mkdir()
    archive_proof=verify_parts(manifest,folder)
    expected={name:report['outputs'][name] for name in SELECT};expected['result.json']=summary_sha
    all_expected=set(report['outputs'])|{'result.json'}
    seen=set();files=set();found={}
    with JoinedParts([folder/p['name'] for p in manifest['parts']]) as joined:
        with tarfile.open(fileobj=joined,mode='r|gz') as archive:
            for entry in archive:
                relative=member_name(entry.name,manifest['source_directory'])
                assert entry.name not in seen and (entry.isfile() or entry.isdir()),'Duplicate or nonregular archive member'
                seen.add(entry.name)
                if entry.isdir():continue
                assert relative in all_expected and relative not in files
                files.add(relative)
                if relative not in expected:continue
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256();count=0
                with archive.extractfile(entry) as inp,target.open('xb') as out:
                    while block:=inp.read(4*1024**2):out.write(block);h.update(block);count+=len(block)
                assert count==entry.size and h.hexdigest()==expected[relative],relative
                found[relative]=dict(bytes=count,sha256=h.hexdigest())
    assert files==all_expected and set(found)==set(expected),'Missing original archive/member'
    assert json.loads((destination/'result.json').read_text())==report
    return dict(archive=archive_proof,selected=found,full_original_file_inventory=len(files))

def validate_capture(capture,report):
    assert capture==report['raw_capture'],'Original capture/header/vector order not reproduced'
    assert capture['header_rows']==113475 and capture['columns']==1152
    assert len(capture['logical_vector_order'])==1152 and capture['logical_vector_order'][0]=='time'

def validate_native(saved,report,requirements):
    model=(saved/'composed/composition/pd500-mim-wire.spice').read_text()
    contract=json.loads((saved/'composed/composition/composition.json').read_text())
    planes=json.loads((saved/'planes/native-planes.json').read_text())
    protected_composition=json.loads((ROOT/'docs/evidence/cdr500-v58-mim-precision-pass-20261024.json').read_text())
    protected_physical=json.loads((ROOT/'docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json').read_text())
    assert contract==protected_composition['report']['composition']['contract']
    assert planes==protected_physical['report']['native_planes']
    bound=original.bind_native(model,contract,planes)
    assert bound==report['binding'] and bound['groups']['npn13g2']==report['devices']
    assert bound['groups']['sg13_lv_nmos']==report['mos_devices'] and bound['groups']['cap_cmim']==report['native_caps']
    groups=bound['groups'];nodes={n for group in groups.values() for dev in group.values() for n in dev['nodes']}|set(bound['ports'])|set(bound['aliases'].values());nodes.discard('0')
    vectors=['v('+n+')' for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]' for n in groups['npn13g2']]+['@n.'+n+'.nsg13_lv_nmos[ids]' for n in groups['sg13_lv_nmos']]
    assert vectors==report['vectors']
    original_deck=(saved/'native/original-bench.cir').read_text();deck=(saved/'native/bench.cir').read_text()
    assert deck==stream.streaming_deck(original_deck,dict(vectors=vectors))
    assert [n for line in original.native_save_commands(vectors) for n in line.split()[1:]]==vectors
    assert all(original_deck.count(line+'\n')==1 for line in original.native_save_commands(vectors))
    assert '.options reltol=1e-4 abstol=1e-12 klu\n' in original_deck
    for net,point in bound['sampler_points'].items():assert original_deck.count(f'C_{net} {point} 0 150f\n')==1
    for node in ('xp','xn','yp','yn'):assert original_deck.count(f'C_{node} {node} 0 50f\n')==1
    log=(saved/'native/native.log').read_text()
    opts,notes,_=original.backend_readback(log,'klu')
    notes += [line for line in log.splitlines() if 'too many arg' in line.lower() or 'no such vector' in line.lower()]
    assert opts==report['native_options'] and notes==report['diagnostics']==[]
    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
    assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2' for n in report['devices']]
    assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1'] for _,s in flags)
    op=np.loadtxt(saved/'native/op.dat',skiprows=1)
    assert op.size==1152 and np.isfinite(op).all() and float(abs(op).max())==report['zero_source_op_maximum']==0.
    return rows.topology(contract,planes,bound,requirements)

def run_case(pin,out,requirements):
    case=pin['case'];identity(api('actions/runs/'+str(RUN)),api('actions/jobs/'+str(JOBS[case])),case)
    folder=out/case;folder.mkdir()
    asset(pin['summary'],folder/'source-summary.json');report=json.loads((folder/'source-summary.json').read_text());summary(report,pin)
    asset(pin['parts']['asset'],folder/'source-parts.json');manifest=json.loads((folder/'source-parts.json').read_text());manifest_valid(manifest,pin)
    tag='cloud-results-'+str(RUN)+'-1-cdr500-v58-loaded-'+case
    release=api('releases/tags/'+tag)
    assert release['tag_name']==tag and release['target_commitish']==HEAD and not release['draft']
    assert api('git/ref/tags/'+tag)['object']==dict(sha=HEAD,type='commit',url=API_URL_COMMIT+HEAD)
    assets={x['name']:x for x in release['assets']};assert len(assets)==len(release['assets'])
    for part in manifest['parts']:
        meta=assets[part['name']];p=dict(id=meta['id'],name=part['name'],size=part['bytes'],digest='sha256:'+part['sha256'])
        asset(p,folder/part['name'])
    saved=folder/'restored';proof=restore(manifest,folder,saved,report,pin['summary']['digest'][7:])
    for part in manifest['parts']:(folder/part['name']).unlink()
    clock=validate_native(saved,report,requirements)
    t,d,capture=stream.read_streamed_wave(saved/'native/wave.raw',report['vectors'],rows.STOP,rows.STEP)
    validate_capture(capture,report)
    reproduction=rows.replay((ROOT/'scripts/cloud_cdr500_v58_loaded.py').read_text(),t,d,capture,report)
    (folder/'original-measurements-reproduced.json').write_text(json.dumps(reproduction,indent=2)+'\n')
    names=rows.selected_names(report,clock)
    selected=rows.cache(folder/'selected-native.bin',t,d,names)
    (folder/'selected-native.json').write_text(json.dumps(selected,indent=2)+'\n')
    diagnosis=rows.diagnose(t,d,report,clock,requirements)
    (folder/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2,allow_nan=False)+'\n')
    (folder/'ledger-index.json').write_text(json.dumps(rows.compact_index(diagnosis),indent=2,allow_nan=False)+'\n')
    evidence=dict(status=diagnosis['status'],case=case,source_head=HEAD,run=RUN,job=JOBS[case],
        restore=proof,original_measurement_keys=sorted(reproduction),original_rejection_preserved=True,
        raw_capture=capture,selected_cache=selected,clock_native_ids=sorted(clock),failed_native_ids=[59,60,71,72,87,88,111,112],
        new_simulation=False,cdr_accepted=False,full_phy_accepted=False,
        outputs={str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file() and 'restored' not in p.parts})
    # Remove only disposable restored copies after complete diagnosis/cache proof.
    del t,d
    shutil.rmtree(saved)
    return evidence

API_URL_COMMIT='https://api.github.com/repos/Melihakbulut221/nssoc/git/commits/'

def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=methods()
    if args.controls:
        from check_cdr_v58_current_ledger import controls
        print(json.dumps(controls(),indent=2));return
    assert args.readback and m['saved_capture_readback_authorized'] is True
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
    requirements=json.loads((ROOT/REQ).read_text())
    out=ROOT/'cloud-cdr-v58-current-ledger';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=RUN,cases=[],
        original_electrical_rejections_authoritative=True,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
    try:
        for pin in requirements['failed_cases']:result['cases'].append(run_case(pin,out,requirements))
        methods();result.update(status='PASS_EXACT_CURRENT_LEDGER_DIAGNOSTICS_ONLY',sources_unchanged=True)
    except BaseException as e:
        result.update(status='REJECTED_CURRENT_LEDGER_DIAGNOSTIC',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        raw=(out/'result.json').read_bytes()
        # Full detailed evidence is an Actions artifact; this compact receipt is logged.
        print(json.dumps(dict(status=result['status'],result_bytes=len(raw),result_sha256=hashlib.sha256(raw).hexdigest(),
            completed_cases=[x['case'] for x in result['cases']],new_simulation=False,cdr_accepted=False,full_phy_accepted=False)),flush=True)

if __name__=='__main__':main()
