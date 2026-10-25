# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small evidence-tamper controls, no Git history, network or native invocation."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import archive_coherent_vss_failure as archive
import run_coherent_io_lvs as producer
from test_extract_gds_hierarchy import library,cell,boundary,ref


def save(path,row):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row))


def identity():
    run = dict(id=archive.RUN,head_sha=archive.SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/coherent-io-lvs.yml',event='workflow_dispatch',status='completed',conclusion='failure',
        run_attempt=1,repository={'full_name':archive.REPO},head_repository={'full_name':archive.REPO})
    artifact = dict(id=archive.ARTIFACT,name='coherent-vss-lvs-attempt-1',expired=False,
        size_in_bytes=archive.SIZE,digest='sha256:'+archive.DIGEST,
        workflow_run={k:run[k] for k in ('id','head_sha','head_branch')})
    return run,artifact


@pytest.mark.parametrize('fault',[None,'source','fork','success','event','attempt','artifact','expired','size','digest','lineage'])
def test_exact_failed_source_and_artifact_required(fault):
    run,artifact = identity()
    if fault=='source':run['head_sha']='0'*40
    if fault=='fork':run['head_repository']['full_name']='wrong/repo'
    if fault=='success':run['conclusion']='success'
    if fault=='event':run['event']='push'
    if fault=='attempt':run['run_attempt']=2
    if fault=='artifact':artifact['id']+=1
    if fault=='expired':artifact['expired']=True
    if fault=='size':artifact['size_in_bytes']+=1
    if fault=='digest':artifact['digest']='sha256:'+'0'*64
    if fault=='lineage':artifact['workflow_run']['head_sha']='0'*40
    if fault is None:archive.identity(run,artifact)
    else:
        with pytest.raises(ValueError):archive.identity(run,artifact)


def test_inventory_covers_exact_65_native_input_output_members():
    names = archive.expected_members()
    assert len(names)==65
    assert len([n for n in names if n.startswith('controls/') and n!='controls/result.json'])==40
    assert len([n for n in names if n.startswith('comparison/inputs/')])==9
    assert {'comparison/deep/lvs.lvsdb.gz','comparison/flat/lvs.lvsdb.gz'}<=names


def case_fixture(tmp_path):
    result = {'cases':{}}
    lock = {'entrypoint':'deck.lvs'}
    for mode in ('deep','flat'):
        base = tmp_path/'comparison'/mode
        base.mkdir(parents=True)
        original = archive.OUTPUT/'comparison'/mode
        for name in archive.CASE_FILES:
            (base/name).write_text('original '+name+'\n')
        (base/'deck.log').write_text("ERROR : Netlists don't match\n")
        audit = producer.native.assess([dict(layout=archive.TOP,schematic=archive.TOP.upper(),status='NoMatch',
            layout_devices_recursive=5,schematic_devices_recursive=6)],archive.TOP,(base/'deck.log').read_text(),[])
        audit['inputs'] = {str(original/name):archive.file_pin(base/name) for name in ('lvs.lvsdb.gz','deck.log')}
        save(base/'audit.json',audit)
        command = producer.command(archive.PRODUCER_ROOT/archive.DECK/lock['entrypoint'],
                                    archive.OUTPUT/'comparison/inputs',original,mode)
        command[0] = str(archive.PRODUCER_ROOT/archive.APP)
        audit_command = [str(archive.PRODUCER_ROOT/archive.APP),'python',
            str(archive.PRODUCER_ROOT/'hw/soc/flow/audit_klayout_lvs.py'),str(original/'lvs.lvsdb.gz'),
            '--top',archive.TOP,'--deck-log',str(original/'deck.log'),'--output',str(original/'audit.json')]
        result['cases'][mode] = dict(status='FAIL',audit=audit,
            native=dict(command=command,returncode=0,address_space_limit_bytes=4*archive.common.GIB,
                        elapsed_watchdog=False,elapsed_seconds=1.0),
            audit_process=dict(command=audit_command,returncode=1,address_space_limit_bytes=4*archive.common.GIB,
                               elapsed_watchdog=False,elapsed_seconds=1.0),
            output_sha256={str(original/name):archive.common.sha(base/name) for name in archive.CASE_FILES})
    return result,lock


@pytest.mark.parametrize('fault',[None,'missing-flat','tap-waiver','port-waiver','native-crash','audit-pass',
                                  'changed-cir','changed-db','changed-deck','forged-pass','embedded-audit','extra-output'])
def test_strict_fail_replay_and_complete_native_output_binding(tmp_path,fault):
    row,lock = case_fixture(tmp_path)
    deep = row['cases']['deep']
    if fault=='missing-flat':del row['cases']['flat']
    if fault=='tap-waiver':deep['native']['command'][-3]='disable_tap_extraction=true'
    if fault=='port-waiver':deep['native']['command'][-1]='ignore_top_ports_mismatch=true'
    if fault=='native-crash':deep['native']['returncode']=-6
    if fault=='audit-pass':deep['audit_process']['returncode']=0
    if fault in ('changed-cir','changed-db','changed-deck'):
        name={'changed-cir':'extracted.cir','changed-db':'lvs.lvsdb.gz','changed-deck':'deck.log'}[fault]
        (tmp_path/'comparison/deep'/name).write_text('changed bytes')
    if fault=='forged-pass':deep['status']='PASS'
    if fault=='embedded-audit':deep['audit']['circuits'][0]['status']='Match'
    if fault=='extra-output':deep['output_sha256']['/unexpected']='0'*64
    if fault is None:
        checked=archive.verify_cases(tmp_path,row,producer,lock)
        assert set(checked)=={'deep','flat'} and all(r['status']=='FAIL' for r in checked.values())
    else:
        with pytest.raises(ValueError):archive.verify_cases(tmp_path,row,producer,lock)


def subset_fixture(tmp_path):
    source = tmp_path/'unpadded-source.gds'
    source.write_bytes(library(cell('leaf',boundary()),cell('unused',boundary()),cell(archive.TOP,ref('leaf'))))
    receipt = producer.gds.extract(source,[archive.TOP],tmp_path/'subset')
    receipt['source']['path'] = str(archive.OUTPUT/'comparison/inputs/unpadded-source.gds')
    receipt['output']['path'] = str(archive.OUTPUT/'comparison/inputs/subset/subset.gds')
    save(tmp_path/'subset/receipt.json',receipt)
    return {'subset':receipt}


@pytest.mark.parametrize('fault',[None,'source-cell','output-cell','excluded','units','order','method','acceptance'])
def test_subset_reindexes_full_source_and_checks_original_record_bytes(tmp_path,fault):
    prep = subset_fixture(tmp_path)
    row = prep['subset']
    if fault=='source-cell':row['cells']['leaf']['source']['sha256']='0'*64
    if fault=='output-cell':row['cells']['leaf']['output']['sha256']='0'*64
    if fault=='excluded':row['excluded_cells']=[]
    if fault=='units':row['units_record_hex']='00'
    if fault=='order':row['roots']=['leaf']
    if fault=='method':row['script_sha256']='0'*64
    if fault=='acceptance':row['lvs_accepted']=True
    save(tmp_path/'subset/receipt.json',row)
    if fault is None:
        assert archive.verify_subset(tmp_path,producer,prep)==dict(source_cells=3,subset_cells=2,geometry_byte_preservation_verified=True)
    else:
        with pytest.raises(ValueError):archive.verify_subset(tmp_path,producer,prep)


def test_source_selection_uses_exact_historical_git_blob_only(tmp_path,monkeypatch):
    commands=[]
    def fake_blob(command):
        commands.append(command)
        return ('immutable '+command[-1]).encode()
    monkeypatch.setattr(archive.subprocess,'check_output',fake_blob)
    source,pins=archive.prepare_sources(tmp_path,tmp_path)
    assert len(commands)==16
    assert all(command[-1].startswith(archive.SOURCE+':') for command in commands)
    assert set(pins)==set(archive.METHODS)|{archive.LOCK,*archive.LICENSES}
    assert (source/'scripts/io_tap_contract_audit.py').read_bytes()==(
        'immutable '+archive.SOURCE+':scripts/io_tap_contract_audit.py').encode()


def controls_fixture(tmp_path):
    source=tmp_path/'source';capture=tmp_path/'capture'
    method='sw/tests/io_parent_lvs_native.py'
    (source/method).parent.mkdir(parents=True)
    (source/method).write_text('original control method')
    row=dict(status='PASS_NATIVE_PARENT_CONTEXT_CONTROLS',manufacturing_approval=False,
        method_sha256={method:archive.common.sha(source/method)},cases={},klayout_version='0.30.7',
        native_bindings={'path':'/nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/lib/python3.13/site-packages/klayout/dbcore.cpython-313-x86_64-linux-gnu.so',
                        'sha256':'30c78decb4a10e1042bcb387c07e2381d001edcab5bb564e3ed7200428ad6758'},
        runtime_namespace_sha256={
            '/nix/store/ffl2vg3m80k0p74pyffnmai83fnv38mf-python3-3.13.9-env/bin/python3.13':
                '6089315ff298ff5ef084e0ef5bf693cf3e60bc5782c4a0294612fe51b44f278a',
            '/nix/store/c8mymw0gckkiw7lqwnm2l6mqnd99xmzy-klayout-0.30.7/lib/pymod/klayout/dbcore.cpython-313-x86_64-linux-gnu.so':
                '30c78decb4a10e1042bcb387c07e2381d001edcab5bb564e3ed7200428ad6758'},
        input_sha256={str(archive.PRODUCER_ROOT/method):archive.common.sha(source/method),
                      str(archive.PRODUCER_ROOT/archive.APP):producer.native.APP_SHA256},output_sha256={})
    for name,expected in archive.CONTROL_CASES.items():
        base=capture/'controls'/name;base.mkdir(parents=True)
        for filename in archive.CONTROL_FILES:(base/filename).write_text(name+filename)
        pins={filename:archive.common.sha(base/filename) for filename in archive.CONTROL_FILES}
        drains=2 if name in ('same_name_open','missing_via') else 1
        row['cases'][name]=dict(actual_match=expected,expected_match=expected,device_counts={'NMOS4':2,'TAP':1},
            extraction_diagnostics=[],hierarchical_circuits=['CHILD','TOP'],tap_terminal_order=['TIE','WELL'],
            tap_parameters={'A':.75 if name=='wrong_tap_area' else 1.,'P':5. if name=='wrong_tap_perimeter' else 4.},
            distinct_drain_nets_after_parent_extraction=drains,drain_cluster_ids=[1,drains],files=pins)
        row['output_sha256'].update({str(archive.OUTPUT/'controls'/name/f):digest for f,digest in pins.items()})
    save(capture/'controls/result.json',row)
    return capture,source,row


@pytest.mark.parametrize('fault',[None,'missing-case','open-passes','area-waiver','terminals','short','extra-output','method','runtime','raw-file'])
def test_all_eight_physical_controls_and_forty_raw_files_required(tmp_path,fault):
    capture,source,row=controls_fixture(tmp_path)
    if fault=='missing-case':del row['cases']['same_name_open']
    if fault=='open-passes':row['cases']['same_name_open']['actual_match']=True
    if fault=='area-waiver':row['cases']['wrong_tap_area']['tap_parameters']['A']=1.
    if fault=='terminals':row['cases']['connected']['tap_terminal_order'].reverse()
    if fault=='short':row['cases']['same_name_open']['drain_cluster_ids']=[1,1]
    if fault=='extra-output':row['output_sha256']['/unexpected']='0'*64
    if fault=='method':row['method_sha256']['sw/tests/io_parent_lvs_native.py']='0'*64
    if fault=='runtime':row['input_sha256'][str(archive.PRODUCER_ROOT/archive.APP)]='0'*64
    if fault=='raw-file':(capture/'controls/missing_via/layout.gds').write_text('different geometry')
    save(capture/'controls/result.json',row)
    if fault is None:
        checked,pins=archive.verify_controls(capture,source,producer)
        assert checked==row and len(pins)==42
    else:
        with pytest.raises(ValueError):archive.verify_controls(capture,source,producer)


@pytest.mark.parametrize('fault',['duplicate','wrong-size','wrong-digest','wrong-url'])
def test_immutable_publication_conflicts_never_upload_or_overwrite(tmp_path,monkeypatch,fault):
    asset=dict(id=123,name=archive.NAME,size=archive.SIZE,digest='sha256:'+archive.DIGEST,
        browser_download_url=f'https://github.com/{archive.REPO}/releases/download/{archive.TAG}/{archive.NAME}')
    assets=[asset]
    if fault=='duplicate':assets.append(dict(asset))
    if fault=='wrong-size':asset['size']+=1
    if fault=='wrong-digest':asset['digest']='sha256:'+'0'*64
    if fault=='wrong-url':asset['browser_download_url']='https://example.invalid/other'
    monkeypatch.setattr(archive.common,'verify_file',lambda *args:None)
    monkeypatch.setattr(archive.common,'api',lambda *args:{'assets':assets})
    def forbidden(*args,**kwargs):raise AssertionError('Immutable conflict must never upload or download')
    monkeypatch.setattr(archive.subprocess,'run',forbidden)
    monkeypatch.setattr(archive.common,'command_hash',forbidden)
    with pytest.raises(ValueError):archive.publish(tmp_path/'not-read.zip',tmp_path)
