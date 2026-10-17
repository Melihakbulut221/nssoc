#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive one failed native probe unchanged; inspect only bounded failure evidence."""
import argparse
import csv
import math
import sys
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

import archive_hold_diagnostic as common

REPO, TAG = common.REPO, common.TAG
RUN = 36962503055
SOURCE = '08e9a6b0d89e1f76659922c628da6eb17489da89'
ARTIFACT = 11208307915
SIZE = 72449994
DIGEST = 'b89f4a4f818fcf6ba59e6eccd4b7477a73e7c3fa5a0d18cf3330b909f13e5266'
NAME = 'timing-targeted-hold-failure-20261002.zip'
COMMON_SHA = '04b89e92cee0bc60d68bc0f1d0d1f313231f622c56333547997108e65cea2c06'
MAX_SELECTED = 2*1024**2
EXPECTED_MEMBERS = 114
EXPECTED_EXPANDED = 156664221
MANIFEST = 'docs/evidence/timing-cloud-input-20260930.json'
STEP = 'run/01-openroad-resizertimingpostgrt/'
METHODS = common.METHODS + ('.github/workflows/timing-targeted-hold.yml',
    'scripts/run_cloud_targeted_hold.py','scripts/compare_full_hold_endpoints.py',
    'scripts/run_timing_experiments.py','scripts/timing_process_guard.py',
    'hw/soc/pnr/timing_targeted_hold_probe_step.tcl',
    'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl',
    'hw/soc/pnr/timing_repair_experiment.tcl','sw/tests/timing_hold_targeted_native.tcl')
SELECTED = ('result.json','native-diagnostic.log','worker.log','run/flow.log','run/error.log',
    STEP+'openroad-resizertimingpostgrt.log','source-manifest.json','source-config.json',
    'source-state.json','native-control-validation.json',STEP+'matched_before/native.json',
    STEP+'matched_before/endpoints.tsv',STEP+'matched_before/constraints.sdc')
CORNERS = ['nom_fast_1p32V_m40C','nom_slow_1p08V_125C','nom_typ_1p20V_25C']
GATE = 'NSSOC_TARGETED_NATIVE_GATE_PASS_BEFORE_C10_LOAD'
FAILURE = 'Matched-before census differs from known C10: endpoints=23527 negative=113 corners='
FORBIDDEN_MARKERS = ('NSSOC_TARGETED_HOLD_PROBE_REPAIR_BEGIN',
    'NSSOC_TARGETED_HOLD_PROBE_REPAIR_END','NSSOC_TARGETED_HOLD_PROBE_COMPLETE_NO_ADOPTION')


def identity(run,artifact):
    expected = dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work',
                    path='.github/workflows/timing-targeted-hold.yml',event='push',
                    status='completed',conclusion='failure',run_attempt=1)
    if any(run.get(k) != v for k,v in expected.items()):
        raise ValueError('Unexpected failed producer identity')
    if any(run.get(k,{}).get('full_name') != REPO for k in ('repository','head_repository')):
        raise ValueError('Unexpected source repository')
    if any(artifact.get(k) != v for k,v in dict(id=ARTIFACT,name='targeted-hold-final-1',
            expired=False,size_in_bytes=SIZE,digest='sha256:'+DIGEST).items()):
        raise ValueError('Unexpected original artifact identity')
    if any(artifact.get('workflow_run',{}).get(k) != v for k,v in dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work').items()):
        raise ValueError('Artifact source differs')


def download(path):
    child = subprocess.Popen(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip'],stdout=subprocess.PIPE)
    try:
        count,digest = 0,hashlib.sha256()
        with path.open('xb') as target:
            while chunk := child.stdout.read(1024**2):
                count += len(chunk)
                if count > SIZE: raise ValueError('Download exceeds exact byte budget')
                target.write(chunk);digest.update(chunk)
        if child.wait() or (count,digest.hexdigest()) != (SIZE,DIGEST):
            raise ValueError('Original ZIP byte verification failed')
    except BaseException:
        if child.poll() is None: child.kill()  # Our network reader, never native work.
        child.wait()
        raise
    finally:
        child.stdout.close()


def source_blob(name):
    """Exact immutable producer source; independent of shallow checkout history."""
    return subprocess.check_output(['gh','api','-H','Accept: application/vnd.github.raw+json',
        f'repos/{REPO}/contents/{name}?ref={SOURCE}'])


def source_pins(output,result):
    if set(result.get('method_files',{})) != set(METHODS):
        raise ValueError('Unexpected producer method closure')
    pins = {}
    for name in (*METHODS,MANIFEST):
        data = source_blob(name)
        pin = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        captured = output/('methods/'+name if name in METHODS else 'source-manifest.json')
        common.verify_file(captured,**dict(size=pin['bytes'],digest=pin['sha256']))
        if name in METHODS and result['method_files'][name] != pin:
            raise ValueError('Producer source pin differs: '+name)
        pins[name] = pin
    return pins


def replay_controls(output):
    # Only verified producer Python performs pure receipt validation. Never invoke
    # its worker/main or a native executable. Preserve its original rejection.
    code = r"""import json,sys
from pathlib import Path
out=Path(sys.argv[1]);sys.path.insert(0,str(out/'methods/scripts'))
import run_cloud_targeted_hold as producer
record=json.loads((out/'result.json').read_text())
base=producer.shared.validate_controls(out/'native-controls/result.json',record['method_files'])
assert tuple(producer.SOURCES)==tuple(json.loads(sys.argv[2]))
try: producer.validate_targeted_controls(out)
except ValueError as error:
    assert str(error)=='Targeted and base controls used different native executables',str(error)
    rejection=str(error)
else: raise AssertionError('Original targeted validator unexpectedly passed')
gate=json.loads((out/'native-controls/targeted/gate.json').read_text())
assert gate['status']=='PASS_TARGETED_NATIVE_GATE' and gate['returncode']==0
assert gate['fixture_sha256']==producer.FIXTURE_SHA and gate['recipe_sha256']==producer.RECIPE_SHA
producer.shared.verify_evidence_files(out/'native-controls/targeted',gate['files'])
assert set(producer.shared.file_inventory(out/'native-controls/targeted'))==set(gate['files'])|{'gate.json'}
for flag in ('timing_accepted','candidate_adopted','manufacturing_approval'):
    assert gate[flag] is False and base[flag] is False
log=(out/'native-controls/targeted/native.log').read_text()
for marker in producer.CONTROL_MARKERS:
    assert sum(line==marker or line.startswith(marker+' ') for line in log.splitlines())==1
for before in ('before.sdc','blocked-setup/before.sdc'):
    assert (out/'native-controls/targeted'/before).read_bytes()==(out/'native-controls/targeted'/before.replace('before','after')).read_bytes()
assert gate['selection']['corners']==['fast','slow','typical']
assert gate['selection']['global_buffer_budget']==gate['result']['actual_instance_growth']==1
assert gate['result']['remaining_buffer_budget']==0
assert gate['result']['calls'][1]['status']=='GLOBAL_BUFFER_BUDGET_EXHAUSTED'
assert gate['overrun']['actual_instance_growth']>gate['overrun']['global_buffer_budget']
print(json.dumps(dict(base_controls_replay='PASS',cases=base['cases'],targeted_gate_recorded_status=gate['status'],targeted_output_closure_verified=True,targeted_markers_verified=True,original_targeted_validator_rejected=True,original_targeted_validator_error=rejection,base_recorded_executable_sha256=base['native_executable_sha256'],targeted_recorded_executable_sha256=gate['executable_sha256'],native_binary_rehashed=False,native_reexecuted=False)))
"""
    child = subprocess.run([sys.executable,'-B','-c',code,str(output),json.dumps(METHODS)],
        capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=120,check=False)
    (output.parent/'pure-control-replay.stdout').write_text(child.stdout)
    (output.parent/'pure-control-replay.stderr').write_text(child.stderr)
    if child.returncode:
        raise ValueError('Original pure control receipt replay failed')
    return json.loads(child.stdout)


def inspect_failure(output,members):
    result = json.loads((output/'result.json').read_text())
    manifest = json.loads((output/'source-manifest.json').read_text())
    config = json.loads((output/'source-config.json').read_text())
    if (result.get('status') != 'FAILED_PRESERVED' or result.get('github_source_commit') != SOURCE
            or result.get('diagnostic_kind') != 'targeted_hold_probe'
            or result.get('selected_checkpoint_preserved') is not True):
        raise ValueError('Wrong failed result source/state')
    for key in ('candidate_adopted','timing_accepted','manufacturing_approval'):
        if result.get(key) is not False:raise ValueError('Failure cannot claim acceptance')
    pins = source_pins(output,result)
    if (result['manifest_sha256'] != pins[MANIFEST]['sha256']
            or result['runtime_sha256'] != manifest['runtime']['sha256']
            or result['bundle_sha256'] != manifest['archive']['sha256']):
        raise ValueError('Source manifest/runtime pin differs')
    for name,key in [('source-config.json','config'),('source-state.json','initial_state')]:
        pin=manifest['files'][manifest[key]]
        common.verify_file(output/name,pin['bytes'],pin['sha256'])
    log = (output/(STEP+'openroad-resizertimingpostgrt.log')).read_text()
    if log.splitlines().count(GATE) != 1 or FAILURE not in log or any(m in log for m in FORBIDDEN_MARKERS):
        raise ValueError('Expected pre-repair baseline guard failure is absent')
    if log.index(GATE)>log.index(FAILURE):raise ValueError('Native gate/failure markers reordered')
    if any(STEP+name in members for name in ('repair-invocation.json','targeted-hold-probe.json','hold-targeted-selection.tcldict')):
        raise ValueError('Unexpected chip repair evidence in pre-repair failure')
    if (result['native_runs']['native-controls']['returncode'] != 0
            or result['native_runs']['native-diagnostic']['returncode'] != 1):
        raise ValueError('Unexpected recorded native phase results')
    native=json.loads((output/(STEP+'matched_before/native.json')).read_text())
    with (output/(STEP+'matched_before/endpoints.tsv')).open(newline='') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if reader.fieldnames != ['endpoint','global_vertex_slack_seconds']:
            raise ValueError('Unexpected endpoint census columns')
        names=set();negative=0
        for row in reader:
            if None in row or row['endpoint'] in names or not row['endpoint']:
                raise ValueError('Duplicate or malformed endpoint census')
            names.add(row['endpoint']);value=row['global_vertex_slack_seconds']
            if value!='UNCONSTRAINED':
                value=float(value)
                if not math.isfinite(value) or abs(value)>=1e20:raise ValueError('Nonfinite endpoint slack')
                negative+=value<0
    if (len(names)!=23527 or negative!=113 or sorted(config['PNR_CORNERS'])!=CORNERS
            or sorted(c['name'] for c in native['corners'])!=CORNERS
            or any(native[k]!=23527 for k in ('endpoint_count','engine_endpoint_count','exported_endpoint_count'))
            or any(native[k]!=113 for k in ('negative_vertex_endpoints','engine_negative_vertex_endpoints'))
            or native['all_endpoint_coverage'] is not True):
        raise ValueError('Actual C10 baseline census differs')
    return dict(exact_producer_sources=pins,controls=replay_controls(output),
        matched_before_census=dict(endpoint_count=len(names),negative_vertex_endpoints=negative,corners=CORNERS),
        recorded_runtime_sha256=result['runtime_sha256'],native_binary_rehashed=False,
        native_repair_started=False,complete_native_diagnostic_verified=False,
        full_baseline_physical_path_replay=False,original_targeted_validator_passed=False)


def selected_failure(path,output):
    output = common.fresh(output)
    with zipfile.ZipFile(path) as z:
        members,expanded = common.inventory_zip(z)
        if (len(members),expanded)!=(EXPECTED_MEMBERS,EXPECTED_EXPANDED):
            raise ValueError('Original failure ZIP member census differs')
        if 'capture.json' not in members or members['capture.json'].file_size>MAX_SELECTED:
            raise ValueError('Missing or oversized capture inventory')
        capture_raw=z.read(members['capture.json']);capture=json.loads(capture_raw)
        if (capture.get('observation',{}).get('status')!='FAILED_PRESERVED'
                or any(capture.get(k) is not False for k in ('complete_diagnostic_evidence',
                    'restart_checkpoint_accepted','candidate_adopted','timing_accepted','manufacturing_approval'))):
            raise ValueError('Expected explicitly incomplete failed capture')
        if set(members)!=set(capture['files'])|{'capture.json'}:
            raise ValueError('ZIP membership differs from capture inventory')
        selected=set(SELECTED)|{'methods/'+name for name in METHODS}|{name for name in members if name.startswith('native-controls/')}
        if not selected<=set(members):raise ValueError('Missing selected failure evidence')
        (output/'capture.json').write_bytes(capture_raw)
        pins={}
        # Stream every compressed member through EOF: ZIP CRC, declared length
        # and captured SHA all checked, without expanding large geometry to disk.
        for name,item in members.items():
            if name=='capture.json':continue
            if name in selected and item.file_size>MAX_SELECTED:raise ValueError('Oversized selected evidence')
            parts=[];count=0;digest=hashlib.sha256()
            with z.open(item) as source:
                while chunk:=source.read(1024**2):
                    count+=len(chunk)
                    if count>item.file_size:raise ValueError('Excess member expansion')
                    digest.update(chunk)
                    if name in selected:parts.append(chunk)
            pin=capture['files'][name]
            if (count!=item.file_size or pin['bytes']!=count or pin['sha256']!=digest.hexdigest()
                    or pin.get('source_truncated_during_copy') is not False
                    or pin.get('observed_source_bytes')!=count):
                raise ValueError('Member does not match exact capture pin: '+name)
            pins[name]=dict(bytes=count,sha256=digest.hexdigest(),crc32=item.CRC)
            if name in selected:
                target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b''.join(parts))
        review=inspect_failure(output,members)
    return dict(zip_members=len(members),expanded_bytes=expanded,all_member_capture_pins_verified=True,
        all_member_crc_verified=True,member_inventory=pins,selected_files=sorted(selected),**review)


def publish(path,review):
    common.verify_file(path,SIZE,DIGEST)
    release = common.api(f'releases/tags/{TAG}')
    matches = [a for a in release['assets'] if a['name'] == NAME]
    if len(matches) > 1: raise ValueError('Ambiguous release asset')
    if not matches:
        subprocess.run(['gh','release','upload',TAG,str(path),'--repo',REPO],check=True)
        release = common.api(f'releases/tags/{TAG}')
        matches = [a for a in release['assets'] if a['name'] == NAME]
    if len(matches) != 1: raise ValueError('Missing immutable release asset')
    asset = matches[0];url = f'https://github.com/{REPO}/releases/download/{TAG}/{NAME}'
    if (asset['size'],asset.get('digest'),asset['browser_download_url']) != (SIZE,'sha256:'+DIGEST,url):
        raise ValueError('Refusing conflicting release bytes')
    common.save(review/'release-asset.json',asset)
    actual = common.command_hash(['gh','api',f'repos/{REPO}/releases/assets/{asset["id"]}',
                                  '-H','Accept: application/octet-stream'],SIZE)
    if actual != (SIZE,DIGEST): raise ValueError('Authenticated roundtrip differs')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'nssoc-evidence-verifier'}),timeout=120) as stream:
        if common.stream_hash(stream,SIZE) != (SIZE,DIGEST): raise ValueError('Anonymous roundtrip differs')
    common.verify_file(path,SIZE,DIGEST)
    return dict(name=NAME,asset_id=asset['id'],url=url,bytes=SIZE,sha256=DIGEST,original_zip_unchanged=True,
                github_api_digest_verified=True,authenticated_roundtrip_verified=True,anonymous_roundtrip_verified=True)


def run(output):
    output = common.fresh(output);review = output/'review';review.mkdir()
    record = dict(status='PREPARING',source_run=RUN,source_commit=SOURCE,source_artifact=ARTIFACT,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,native_reexecuted=False,
        full_native_output_validation=False,method_sha256=common.sha(Path(__file__)),helper_sha256=common.sha(Path(common.__file__)))
    common.save(review/'result.json',record)
    try:
        if record['helper_sha256'] != COMMON_SHA: raise ValueError('Shared archival helper changed')
        if shutil.disk_usage(output).free <= SIZE+128*1024**2: raise ValueError('Insufficient cloud disk reserve')
        source = common.api(f'actions/runs/{RUN}');artifact = common.api(f'actions/artifacts/{ARTIFACT}')
        common.save(review/'producer-run.json',source);common.save(review/'producer-artifact.json',artifact)
        identity(source,artifact)
        path = output/NAME;download(path);common.verify_file(path,SIZE,DIGEST)
        record['failure_evidence'] = selected_failure(path,review/'selected')
        common.save(review/'result.json',record)
        root = Path(__file__).resolve().parents[1]
        for name in ('scripts/archive_targeted_hold_failure.py','scripts/archive_hold_diagnostic.py',
                     '.github/workflows/timing-targeted-hold-failure-archive.yml','LICENSES/Apache-2.0.txt'):
            target = review/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
        record['assets'] = [publish(path,review)]
        record['review_files'] = {str(item.relative_to(review)): dict(bytes=item.stat().st_size,sha256=common.sha(item))
                                 for item in sorted(review.rglob('*')) if item.is_file() and item != review/'result.json'}
        record.update(status='PASS_ARCHIVED_FAILED_NATIVE_EVIDENCE',release_tag=TAG,
                      release_url=f'https://github.com/{REPO}/releases/tag/{TAG}',
                      scope='Unchanged original failure ZIP; every member CRC/size/captured SHA and exact producer source checked. Selected control and baseline receipts replayed; original targeted-validator rejection preserved. No native rerun, binary rehash, repair, complete diagnostic or accepted checkpoint.')
        common.save(review/'result.json',record)
        print(json.dumps(record,indent=2));return 0
    except Exception as error:
        record.update(status='FAILED_PRESERVED',error=repr(error));common.save(review/'result.json',record)
        print(str(error));return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    return run(parser.parse_args().output)


if __name__ == '__main__':
    raise SystemExit(main())
