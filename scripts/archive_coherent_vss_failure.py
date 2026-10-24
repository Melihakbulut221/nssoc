#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive immutable coherent Vss failure; replay evidence, never native extraction.

All ZIP members and producer pin inventories are checked. Strict assessment is
replayed from captured circuit rows and deck verdicts; the native database is
byte-verified, not re-compared. Runtime binary is outside the original artifact:
its recorded pin is checked against exact producer source, not rehashed here.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import urllib.request

import archive_hold_diagnostic as common

REPO, TAG = common.REPO, common.TAG
RUN = 36917255183
SOURCE = 'fb3f7492ea94c8e6a3c98cebbf4dbc4892cfe4f9'
ARTIFACT, SIZE = 11191090244, 27596825
DIGEST = 'b0527ae1fb9019181b97880581e33feb170aa9a8765cb3a1839607b965b78b2a'
NAME = 'coherent-vss-native-failure-20261002.zip'
MEMBERS, EXPANDED = 65, 149259318
COMMON_SHA = '04b89e92cee0bc60d68bc0f1d0d1f313231f622c56333547997108e65cea2c06'
PRODUCER_ROOT = PurePosixPath('/home/runner/work/nssoc/nssoc')
OUTPUT = PRODUCER_ROOT/'hw/soc/out/github-coherent-io-lvs'
LOCK = 'hw/soc/pnr/ihp-lvs.lock.json'
APP = 'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
DECK = 'hw/soc/tools/ihp-lvs-5e6d592'
TOP = 'sg13g2_IOPadVss'
UPSTREAM = '5e6d592e4002946a4616f798c357f0f3c06cf3b6'
METHODS = ('scripts/run_coherent_io_lvs.py','scripts/run_io_parent_lvs.py',
    'scripts/extract_gds_hierarchy.py','scripts/io_tap_topology_audit.py',
    'scripts/io_tap_contract_audit.py','hw/soc/flow/io_cell_schematic.py',
    'hw/soc/flow/transistor_schematic.py','hw/soc/flow/audit_klayout_lvs.py',
    'hw/soc/flow/prepare_ihp_drc.py','hw/soc/flow/prepare_ihp_lvs.py',
    'scripts/bootstrap_flow.py','scripts/fetch_evidence_assets.py',
    'sw/tests/io_parent_lvs_native.py','.github/workflows/coherent-io-lvs.yml')
INPUTS = ('preparation.json','schematic.cir','selected-source.cdl','sg13g2_io.cdl',
          'sg13g2_io.gds','sg13g2_io.lef','subset/receipt.json','subset/subset.gds','unpadded-source.gds')
CASE_FILES = ('run.log','extracted.cir','deck.log','audit.log','lvs.lvsdb.gz','audit.json')
CONTROL_FILES = ('layout.gds','hierarchy.l2n','hierarchy.txt','layout-netlist.txt','reference-netlist.txt')
CONTROL_CASES = {'connected':True,'same_name_open':False,'missing_via':False,'wrong_width':False,
    'wrong_length':False,'wrong_tap_perimeter':False,'wrong_tap_area':False,'reversed_tap_terminals':False}
LICENSES = ('LICENSES/Apache-2.0.txt',)
OWN = ('scripts/archive_coherent_vss_failure.py','scripts/archive_hold_diagnostic.py',
       '.github/workflows/coherent-vss-failure-archive.yml','sw/tests/test_archive_coherent_vss_failure.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def file_pin(path):
    return dict(bytes=path.stat().st_size,sha256=common.sha(path))


def identity(run, artifact):
    expected = dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/coherent-io-lvs.yml',event='workflow_dispatch',status='completed',
        conclusion='failure',run_attempt=1)
    require(all(run.get(k)==v for k,v in expected.items()),'Unexpected failed producer identity')
    require(all(run.get(k,{}).get('full_name')==REPO for k in ('repository','head_repository')),
            'Unexpected producer repository')
    expected_artifact = dict(id=ARTIFACT,name='coherent-vss-lvs-attempt-1',expired=False,
                            size_in_bytes=SIZE,digest='sha256:'+DIGEST)
    require(all(artifact.get(k)==v for k,v in expected_artifact.items()),'Unexpected original artifact')
    require(all(artifact.get('workflow_run',{}).get(k)==v for k,v in
        dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work').items()),'Artifact lineage differs')


def download(path):
    child = subprocess.Popen(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip'],stdout=subprocess.PIPE)
    try:
        count,digest = 0,hashlib.sha256()
        with path.open('xb') as sink:
            while chunk := child.stdout.read(1024**2):
                count += len(chunk)
                require(count<=SIZE,'Original archive exceeds pinned size')
                sink.write(chunk);digest.update(chunk)
        require(child.wait()==0 and (count,digest.hexdigest())==(SIZE,DIGEST),'Original archive differs')
    except BaseException:
        if child.poll() is None:
            child.kill()  # Only our network reader, never a native process.
        child.wait()
        raise
    finally:
        child.stdout.close()


def expected_members():
    return ({'comparison/result.json','comparison.log','controls/result.json','controls.log'}
        | {'comparison/inputs/'+name for name in INPUTS}
        | {f'comparison/{mode}/{name}' for mode in ('deep','flat') for name in CASE_FILES}
        | {f'controls/{case}/{name}' for case in CONTROL_CASES for name in CONTROL_FILES})


def verify_controls(capture, source, producer):
    row = load(capture/'controls/result.json')
    method = 'sw/tests/io_parent_lvs_native.py'
    require(row.get('status')=='PASS_NATIVE_PARENT_CONTEXT_CONTROLS','Native controls incomplete')
    require(row.get('manufacturing_approval') is False,'Controls claim acceptance')
    require(row.get('method_sha256')=={method:common.sha(source/method)},'Control method differs')
    require(set(row.get('cases',{}))==set(CONTROL_CASES),'Control inventory differs')
    outputs = {}
    for name,expected in CONTROL_CASES.items():
        case = row['cases'][name]
        require(case.get('actual_match') is expected and case.get('expected_match') is expected,'Wrong native control verdict')
        require(case.get('device_counts')=={'NMOS4':2,'TAP':1}
            and case.get('extraction_diagnostics')==[]
            and set(case.get('hierarchical_circuits',[]))=={'CHILD','TOP'}
            and case.get('tap_terminal_order')==['TIE','WELL']
            and case.get('tap_parameters')=={'A':0.75 if name=='wrong_tap_area' else 1.0,
                                           'P':5.0 if name=='wrong_tap_perimeter' else 4.0},
            'Control primitive or strict tap contract differs')
        drains = 2 if name in ('same_name_open','missing_via') else 1
        require(case.get('distinct_drain_nets_after_parent_extraction')==drains
            and len(case.get('drain_cluster_ids',[]))==2
            and len(set(case['drain_cluster_ids']))==drains,'Control parent connectivity differs')
        pins = {name_file:common.sha(capture/'controls'/name/name_file) for name_file in CONTROL_FILES}
        require(case.get('files')==pins,'Control raw file closure differs')
        outputs.update({str(OUTPUT/'controls'/name/k):v for k,v in pins.items()})
    inputs = {str(PRODUCER_ROOT/method):common.sha(source/method),
              str(PRODUCER_ROOT/APP):producer.native.APP_SHA256}
    require(row.get('input_sha256')==inputs and row.get('output_sha256')==outputs,'Control input/output inventory differs')
    require(row.get('klayout_version')=='0.30.7','Unexpected recorded native binding version')
    namespace = row.get('runtime_namespace_sha256',{})
    require(namespace=={
        '/nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/bin/python3.13':
            '6089315ff298ff5ef084e0ef5bf693cf3e60bc5782c4a0294612fe51b44f278a',
        '/nix/store/c8mymw0gckkiw7lqwnm2l6mqnd99xmzy-klayout-0.30.7/lib/pymod/klayout/dbcore.cpython-313-x86_64-linux-gnu.so':
            '30c78decb4a10e1042bcb387c07e2381d001edcab5bb564e3ed7200428ad6758'},'Recorded runtime namespace differs')
    require(row.get('native_bindings')=={
        'path':'/nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/lib/python3.13/site-packages/klayout/dbcore.cpython-313-x86_64-linux-gnu.so',
        'sha256':'30c78decb4a10e1042bcb387c07e2381d001edcab5bb564e3ed7200428ad6758'},'Native binding pin differs')
    return row,inputs|outputs


def verify_cases(capture, result, producer, lock):
    require(set(result.get('cases',{}))=={'deep','flat'},'Missing strict mode')
    summaries = {}
    for mode in ('deep','flat'):
        case = result['cases'][mode]
        base = capture/'comparison'/mode
        original = OUTPUT/'comparison'/mode
        expected_command = producer.command(PRODUCER_ROOT/DECK/lock['entrypoint'],
                                            OUTPUT/'comparison/inputs',original,mode)
        # Imported source lives in the review tree; restore only the recorded executable path.
        expected_command[0] = str(PRODUCER_ROOT/APP)
        audit_command = [str(PRODUCER_ROOT/APP),'python',str(PRODUCER_ROOT/'hw/soc/flow/audit_klayout_lvs.py'),
                         str(original/'lvs.lvsdb.gz'),'--top',TOP,'--deck-log',str(original/'deck.log'),
                         '--output',str(original/'audit.json')]
        for label,expected,code in (('native',expected_command,0),('audit_process',audit_command,1)):
            execution = case[label]
            require(execution.get('command')==expected and execution.get('returncode')==code
                and execution.get('address_space_limit_bytes')==4*common.GIB
                and execution.get('elapsed_watchdog') is False,'Strict native invocation differs')
        audit = load(base/'audit.json')
        require(case.get('audit')==audit and case.get('status')=='FAIL','Original native FAIL changed')
        replay = producer.native.assess(audit['circuits'],TOP,(base/'deck.log').read_text(),audit.get('extraction_diagnostics',[]))
        require(replay['status']=='FAIL' and replay['reasons']
            and all(audit.get(k)==v for k,v in replay.items()),'Strict FAIL cannot be replayed')
        require(audit.get('inputs')=={str(original/name):file_pin(base/name) for name in ('lvs.lvsdb.gz','deck.log')},
                'Audit database/deck binding differs')
        require(case.get('output_sha256')=={str(original/name):common.sha(base/name) for name in CASE_FILES},
                'Native output inventory differs')
        require(all((base/name).stat().st_size>0 for name in CASE_FILES),'Empty native failure evidence')
        summaries[mode] = dict(status='FAIL',native_returncode=0,audit_returncode=1,
                              audit=replay,native_elapsed_seconds=case['native']['elapsed_seconds'])
    return summaries


def verify_subset(inputs, producer, preparation):
    gds = producer.gds
    with (inputs/'unpadded-source.gds').open('rb') as stream:
        original = gds.index_stream(stream)
    with (inputs/'subset/subset.gds').open('rb') as stream:
        subset = gds.index_stream(stream)
    selected = gds.closure(original['cells'],[TOP])
    names = [name for name in original['cells'] if name in selected]
    receipt = load(inputs/'subset/receipt.json')
    require(receipt==preparation['subset'],'Embedded subset receipt differs')
    require(receipt.get('status')=='BYTE_PRESERVED_HIERARCHY_SUBSET' and receipt.get('roots')==[TOP],
            'Subset provenance differs')
    for key,index,path in (('source',original,'unpadded-source.gds'),('output',subset,'subset/subset.gds')):
        require(receipt[key]==dict(path=str(OUTPUT/'comparison/inputs'/path),bytes=index['bytes'],
            sha256=index['sha256'],cell_count=len(index['cells'])),'Subset indexed identity differs')
    require(set(subset['cells'])==selected and list(subset['cells'])==names,'Subset closure or source order differs')
    require(receipt['cells']=={name:dict(source=original['cells'][name],output=subset['cells'][name]) for name in names},
            'Subset cell byte evidence differs')
    for name in names:
        require(all(original['cells'][name][key]==subset['cells'][name][key] for key in ('bytes','sha256','references')),
                'Selected geometry bytes changed')
    require(original['header']==subset['header']==receipt['library_header']
        and original['units_record_hex']==subset['units_record_hex']==receipt['units_record_hex']
        and original['endlib']['sha256']==subset['endlib']['sha256']==receipt['endlib_sha256'],
        'Library header/units/footer changed')
    require(receipt['excluded_cells']==[name for name in original['cells'] if name not in selected],
            'Excluded cell inventory differs')
    require(receipt.get('script_sha256')==common.sha(Path(producer.gds.__file__)),'Subset method differs')
    for key in ('geometry_records_modified','missing_references','cycles','lvs_accepted','manufacturing_approval'):
        require(receipt.get(key) is False,'Subset unsupported acceptance/mutation')
    return dict(source_cells=len(original['cells']),subset_cells=len(names),geometry_byte_preservation_verified=True)


def verify_preparation(capture, producer, temporary):
    inputs = capture/'comparison/inputs'
    prep = load(inputs/'preparation.json')
    require(prep.get('commit')==UPSTREAM and prep.get('status')=='PREPARED_COHERENT_VSS_NATIVE_LVS_PENDING',
            'Preparation source/state differs')
    require(set(prep.get('views',{}))=={'gds','cdl','lef'},'Coherent view inventory differs')
    for kind in ('gds','cdl','lef'):
        metadata = producer.metadata(kind)
        identity = producer.topology.verify_view(inputs/f'sg13g2_io.{kind}',metadata,UPSTREAM,kind)
        require(prep['views'][kind]==dict(metadata=metadata,identity=identity),'Original coherent view differs')
    raw = producer.read_io_cdl_text(inputs/'sg13g2_io.cdl')
    contract = producer.topology.audit(raw,producer.read_io_cdl_text(inputs/'sg13g2_io.lef'))
    require(prep.get('reference_contract')==contract and contract['status']=='REFERENCE_TOPOLOGY_MATCH',
            'Named reference topology differs')
    selected_raw,selected,changes,cells,globals_ = producer.vss_reference(raw)
    require((inputs/'selected-source.cdl').read_bytes()==selected_raw.encode()
        and (inputs/'schematic.cir').read_bytes()==selected.encode(),'Selected CDL adapter changed')
    require(prep['dialect_changes']==changes and prep['selected_subcircuits']==cells
        and prep['explicit_globals']==globals_ and prep['dialect_line_scope']=='selected-source.cdl',
        'Reference dependency/global contract differs')
    prefix = temporary/'unpadded.gds'
    padding = producer.unpad_coherent_gds(inputs/'sg13g2_io.gds',prefix)
    require(padding==prep['padding_transport_adapter'] and common.sha(prefix)==common.sha(inputs/'unpadded-source.gds'),
            'Original/prefix zero-padding-only transformation differs')
    prefix.unlink()  # Fresh verifier derivative, never original captured bytes.
    require(prep.get('ordered_pin_contract')==dict(current_formals=['vdd','vss','iovdd','iovss'],
        old_formals=['iovdd','iovss','vdd','vss'],old_actual_indices_for_new_order=[2,3,0,1],
        old_callers_changed=False,parent_wrapper_added=False),'Port-order contract differs')
    for key in ('globals_inferred','geometry_changed','tap_parameters_changed','full_chip_lvs_accepted','manufacturing_approval'):
        require(prep.get(key) is False,'Preparation changes physical/acceptance scope')
    return prep,verify_subset(inputs,producer,prep)


def prepare_sources(repo, review):
    source = common.fresh(review/'producer-source')
    pins = {}
    for name in (*METHODS,LOCK,*LICENSES):
        raw = subprocess.check_output(['git','-C',str(repo),'show',f'{SOURCE}:{name}'])
        target = source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o444)
        pins[name] = file_pin(target)
    return source,pins


def verify_capture(capture, source, review, inventory, fetch_deck=True):
    require(set(inventory['files'])==expected_members(),'Original member inventory differs')
    # The producer module and every imported method come from immutable producer Git blobs.
    sys.path[:0] = [str(source/'scripts'),str(source/'hw/soc/flow')]
    producer = importlib.import_module('run_coherent_io_lvs')
    require(Path(producer.__file__).resolve()==(source/'scripts/run_coherent_io_lvs.py').resolve(),
            'Wrong producer module import')
    require(tuple(producer.METHODS)==METHODS and producer.COMMIT==UPSTREAM,'Producer method/deck contract differs')
    result = load(capture/'comparison/result.json')
    require(all(result.get(k)==v for k,v in dict(schema=1,status='FAIL_COHERENT_VSS_LVS',source_sha=SOURCE,
        run_id=str(RUN),upstream_commit=UPSTREAM,top=TOP).items()),'Original comparison identity differs')
    for key in ('cell_lvs_accepted','full_chip_lvs_accepted','manufacturing_approval','active_pdk_updated','original_layout_changed'):
        require(result.get(key) is False,'Original failure claims acceptance or mutation')
    controls,control_pins = verify_controls(capture,source,producer)
    require(result.get('controls')==controls,'Embedded control result differs')
    lock = load(source/LOCK)
    require(common.sha(source/LOCK)==producer.native.LOCK_SHA256,'Native deck lock differs')
    producer.native.validate_lock(lock)
    require(lock['commit']==UPSTREAM,'Deck/view revisions differ')
    expected = {str(PRODUCER_ROOT/name):common.sha(source/name) for name in METHODS}
    expected.update(control_pins)
    expected[str(OUTPUT/'controls/result.json')] = common.sha(capture/'controls/result.json')
    expected[str(PRODUCER_ROOT/LOCK)] = common.sha(source/LOCK)
    for row in lock['files']:
        expected[str(PRODUCER_ROOT/DECK/row['path'])] = row['sha256']
        if fetch_deck:
            target = review/'upstream-deck'/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
            url = f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{UPSTREAM}/{row["path"]}'
            with urllib.request.urlopen(url,timeout=120) as stream, target.open('xb') as sink:
                raw = stream.read(row['bytes']+1);sink.write(raw)
            common.verify_file(target,row['bytes'],row['sha256'])
    expected.update({str(OUTPUT/'comparison/inputs'/name):common.sha(capture/'comparison/inputs'/name) for name in INPUTS})
    require(result.get('input_sha256')==expected,'Complete producer input pin inventory differs')
    temporary = common.fresh(review/'temporary')
    prep,subset = verify_preparation(capture,producer,temporary)
    temporary.rmdir()
    require(result.get('preparation')==prep,'Embedded preparation differs')
    cases = verify_cases(capture,result,producer,lock)
    return dict(status='VERIFIED_IMMUTABLE_COHERENT_VSS_FAILURE',source_commit=SOURCE,source_run=RUN,
        native_controls=8,strict_native_cases=cases,coherent_views_commit=UPSTREAM,
        complete_input_pin_count=len(expected),subset=subset,deck_files_verified=len(lock['files']) if fetch_deck else 0,
        recorded_runtime_pin_verified=True,runtime_binary_rehashed=False,native_extraction_reexecuted=False,
        native_database_recompared=False,strict_assessment_replayed=True,cell_lvs_accepted=False,
        full_chip_lvs_accepted=False,manufacturing_approval=False,
        scope='All captured bytes/pins and source transformations checked. Strict FAIL replay uses captured circuit rows and deck verdict; database bytes are bound, no fresh extraction/comparison or runtime binary rehash.')


def publish(archive,review):
    common.verify_file(archive,SIZE,DIGEST)
    release = common.api(f'releases/tags/{TAG}')
    matches = [asset for asset in release['assets'] if asset['name']==NAME]
    reused = bool(matches)
    require(len(matches)<=1,'Ambiguous release asset')
    if not matches:
        subprocess.run(['gh','release','upload',TAG,str(archive),'--repo',REPO],check=True)
        matches = [asset for asset in common.api(f'releases/tags/{TAG}')['assets'] if asset['name']==NAME]
    require(len(matches)==1,'Missing immutable release asset')
    asset = matches[0];url = f'https://github.com/{REPO}/releases/download/{TAG}/{NAME}'
    require((asset['size'],asset.get('digest'),asset['browser_download_url'])==(SIZE,'sha256:'+DIGEST,url),
            'Refusing conflicting release bytes')
    common.save(review/'release-asset.json',asset)
    require(common.command_hash(['gh','api',f'repos/{REPO}/releases/assets/{asset["id"]}',
        '-H','Accept: application/octet-stream'],SIZE)==(SIZE,DIGEST),'Authenticated roundtrip differs')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'nssoc-evidence-verifier'}),timeout=120) as stream:
        require(common.stream_hash(stream,SIZE)==(SIZE,DIGEST),'Anonymous roundtrip differs')
    common.verify_file(archive,SIZE,DIGEST)
    return dict(name=NAME,asset_id=asset['id'],url=url,bytes=SIZE,sha256=DIGEST,
        original_zip_unchanged=True,reused_existing_matching_asset=reused,
        github_api_digest_verified=True,authenticated_roundtrip_verified=True,anonymous_roundtrip_verified=True)


def run(output,repo,publish_requested):
    output = common.fresh(output);review = output/'review';review.mkdir()
    record = dict(status='PREPARING',source_run=RUN,source_commit=SOURCE,source_artifact=ARTIFACT,
        archive_source_commit=os.environ.get('GITHUB_SHA'),method_sha256=common.sha(Path(__file__)),
        helper_sha256=common.sha(Path(common.__file__)),publication_requested=publish_requested,
        cell_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False,
        native_extraction_reexecuted=False,runtime_binary_rehashed=False)
    common.save(review/'result.json',record)
    try:
        require(record['helper_sha256']==COMMON_SHA,'Shared archival helper changed')
        require(shutil.disk_usage(output).free>=SIZE+2*EXPANDED+common.DISK_RESERVE,'Insufficient cloud disk reserve')
        run_row = common.api(f'actions/runs/{RUN}');artifact = common.api(f'actions/artifacts/{ARTIFACT}')
        common.save(review/'producer-run.json',run_row);common.save(review/'producer-artifact.json',artifact)
        identity(run_row,artifact)
        archive = output/NAME;download(archive);common.verify_file(archive,SIZE,DIGEST)
        capture = output/'capture';inventory = common.extract(archive,capture,EXPANDED,MEMBERS)
        common.save(review/'member-inventory.json',inventory)
        source,source_pins = prepare_sources(repo,review)
        common.save(review/'producer-source-pins.json',source_pins)
        summary = verify_capture(capture,source,review,inventory)
        common.save(review/'summary.json',summary)
        for name,pin in inventory['files'].items():
            common.verify_file(capture/name,pin['bytes'],pin['sha256'])
        require({str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}==set(inventory['files']),
                'Original capture membership changed')
        for name,pin in source_pins.items():
            common.verify_file(source/name,pin['bytes'],pin['sha256'])
        for name in (*OWN,*LICENSES):
            target = review/'archive-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,target)
        for name in ('comparison/result.json','controls/result.json','comparison/inputs/preparation.json','comparison/inputs/subset/receipt.json'):
            target = review/'selected'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(capture/name,target)
        record.update(status='PASS_VERIFIED_IMMUTABLE_NATIVE_FAILURE',member_count=MEMBERS,expanded_bytes=EXPANDED,
                      archive_bytes=SIZE,archive_sha256=DIGEST,summary=summary)
        if publish_requested:
            record['asset'] = publish(archive,review);record['status'] = 'PASS_PUBLISHED_IMMUTABLE_NATIVE_FAILURE'
        record['review_files'] = {str(p.relative_to(review)):file_pin(p) for p in sorted(review.rglob('*'))
                                 if p.is_file() and p!=review/'result.json'}
        common.save(review/'result.json',record)
        print(json.dumps(record,indent=2));return 0
    except Exception as error:
        record.update(status='FAILED_PRESERVED',error=repr(error));common.save(review/'result.json',record)
        print(str(error),file=sys.stderr);return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--publish',action='store_true')
    args = parser.parse_args()
    return run(args.output,args.repo.resolve(),args.publish)


if __name__=='__main__':
    raise SystemExit(main())
