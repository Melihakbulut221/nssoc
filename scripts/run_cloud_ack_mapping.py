#!/usr/bin/env python3
"""Same-input hosted baseline/ACK mapping and unplaced three-corner screening."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()



def physical_recipe(inputs, manifest, output, profile, status):
    """Restore the actual RX-return-metadata synthesis source, not WAKE1."""
    prefix = manifest['old_root'] + '/hw/soc/out/pcie-rx-return-metadata-20261012'
    packed = output / 'physical-source.tar.gz'
    url = 'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-20261012-000/batch-000013.tar.gz'
    subprocess.run(['curl','--fail','--location','--retry','4',url,'-o',str(packed)],check=True)
    assert packed.stat().st_size == 54741514
    assert sha(packed) == 'e55c3b18997b7ee871cca6dfd21400f66ecab824c038f7dcd385c09f2ac67313'
    with tarfile.open(packed) as archive:
        def member(name, digest):
            raw = archive.extractfile('hw/soc/out/pcie-rx-return-metadata-20261012/' + name).read()
            assert hashlib.sha256(raw).hexdigest() == digest, name
            return raw
        physical = json.loads(member('physical-result19.json','616eee906f67d937bb29fa23b586626f7cb7df9f11c5103257fd22323ade7d17'))
        assert physical['returncode']==0 and physical['unchanged']
        audit = json.loads(member('map-audit14.json',physical['inputs'][prefix+'/map-audit14.json']))
        assert audit['status'].startswith('PASS'), audit['status']
        mapping = json.loads(member('map-result10.json','2866e1ef87f865b375e114a921f9e36dd639dc8d0fe194814856e6677cad64c1'))
        # The initial mapping audit failed with KeyError(209); preserve that
        # history. The separately source-bound map-audit14 is the later audit.
        assert mapping['returncode']==0 and mapping['unchanged']
        recipe = member('map10/soc_top_syn.ys',mapping['inputs'][prefix+'/map10/soc_top_syn.ys']).decode()
        expected = {os.path.normpath(k):v for k,v in mapping['inputs'].items()}
        content = {}
        # Source data only; no archived executable is run.
        for item in archive.getmembers():
            if item.isfile() and item.size < 2000000 and item.name.endswith(('.v','.vh','.lib','.constr')):
                raw = archive.extractfile(item).read()
                content[hashlib.sha256(raw).hexdigest()] = raw
    packed.unlink()
    for name, pin in manifest['files'].items():
        path=inputs/name
        assert sha(path)==pin['sha256']
        if path.suffix in ('.v','.vh','.lib','.constr'):
            content[pin['sha256']]=path.read_bytes()
    selected={}
    for line in recipe.splitlines():
        if not line.startswith(('read_verilog ','read_liberty ','dfflibmap ','abc ')):
            continue
        for token in shlex.split(line)[1:]:
            if not token.startswith('/'):
                continue
            old=os.path.normpath(token)
            if old.startswith(manifest['old_root']+'/'):
                local=inputs/'root'/old[len(manifest['old_root'])+1:]
            elif old.startswith(manifest['old_pdk']+'/'):
                local=inputs/'pdk'/old[len(manifest['old_pdk'])+1:]
            else:
                raise AssertionError(('unbound absolute source',old))
            digest=expected.get(old)
            if digest is None:
                assert not line.startswith('read_verilog '), ('RTL missing source hash',old)
                assert local.is_file(),old
                digest=sha(local) # Already pinned capsule library/ABC input.
            if not local.is_file() or sha(local)!=digest:
                raw=content.get(digest)
                if raw is None and old.startswith(manifest['old_root']+'/'):
                    canonical=ROOT/old[len(manifest['old_root'])+1:]
                    if canonical.is_file() and sha(canonical)==digest:
                        raw=canonical.read_bytes()
                assert raw is not None,('missing exact physical source',old,digest)
                assert hashlib.sha256(raw).hexdigest()==digest
                local.parent.mkdir(parents=True,exist_ok=True)
                # Never overwrite a differing pinned capsule member.
                assert not local.exists(),('capsule source conflict',old)
                local.write_bytes(raw)
            assert sha(local)==digest
            selected[old]=dict(path=str(local),sha256=digest)
    replay=manifest['old_root']+'/hw/soc/out/pcie-replay-successor-register-20261012/candidate01/soc_pcie_replay_tx.v'
    assert selected[replay]['sha256']=='ca334ee560f34a0d7484467d8a09ccbe7fc7b2113360f4bee7308f39bbac8e85'
    assert selected[manifest['old_root']+'/hw/soc/rtl/soc_top.v']['sha256']=='b782a7fbe7b9ad5abb0db67bd132907d71e1ef43c9451b9befa2f356b77d4847'
    credit=manifest['old_root']+'/hw/soc/out/pcie-metadata-late-select-20261010/candidate02/soc_pcie_credit_tx.v'
    assert selected[credit]['sha256']=='ba8adb6fe529df4480a1b526d57a7d75b34a6c74ceed2e4a85ab8777521de7b9'
    proof_path=output/'source-bound-proof.json'
    proof_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38465877636-1-replay-idle/replay-idle-38465877636-1.json'
    subprocess.run(['curl','--fail','--location','--retry','4',proof_url,'-o',str(proof_path)],check=True)
    assert sha(proof_path)=='554699985261db8de530b8eb1aeb0846deded73a7a506abf5616788da8f681d9'
    proof=json.loads(proof_path.read_text())
    assert proof['status']=='PASS_OBSERVABLE_REPLAY_EQUIVALENCE_AND_COMPLETE_PORT_CONTROLS_NOT_TIMING'
    assert proof['source_profile']=='physical_replay'
    assert proof['proofs'][0]['passed'] and proof['proofs'][1]['negative_rejected']
    assert proof['source_sha256']==selected[replay]['sha256']
    if profile in ('physical_idle','physical_idle_credit','physical_idle_credit_eop','physical_idle_credit_window','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
        from run_cloud_replay_idle import candidate
        altered=candidate(Path(selected[replay]['path']).read_text())
        target=output/'candidate-soc_pcie_replay_tx.v'
        target.write_text(altered)
        assert sha(target)==proof['candidate_sha256']=='1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc'
        assert recipe.count(replay)==1
        recipe=recipe.replace(replay,str(target))
    if profile in ('physical_idle_credit','physical_idle_credit_eop','physical_idle_credit_window','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
        from run_cloud_credit_late_verdict import candidate as credit_candidate
        credit_proof_path=output/'credit-source-bound-proof.json'
        credit_proof_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38471835755-1-credit-late-verdict/credit-late-verdict-38471835755-1.json'
        subprocess.run(['curl','--fail','--location','--retry','4',credit_proof_url,'-o',str(credit_proof_path)],check=True)
        assert sha(credit_proof_path)=='658337c2e7cb3455e29a88248a8d738489013b4848925e7688dfc0c49a3cda35'
        credit_proof=json.loads(credit_proof_path.read_text())
        assert credit_proof['status']=='PASS_PHYSICAL_CREDIT_VERDICT_EQUIVALENCE_AND_COMPLETE_CONTROLS_NOT_TIMING'
        assert credit_proof['direct_proofs'][0]['passed'] and credit_proof['direct_proofs'][1]['negative_rejected']
        assert all(p['returncode']==0 for p in credit_proof['reference_proofs'])
        assert [p['actual_tests'] for p in credit_proof['ports']]==[
            dict(passed=5,failed=0,skipped=0),dict(passed=5,failed=0,skipped=0),dict(passed=0,failed=5,skipped=0)]
        assert credit_proof['source_binding']['source_sha256']==selected[credit]['sha256']
        target=output/'candidate-soc_pcie_credit_tx.v'
        target.write_text(credit_candidate(Path(selected[credit]['path']).read_text()))
        assert sha(target)==credit_proof['source_binding']['candidate_sha256']=='7fc31891f0ae48a8df5247b6df72388ff12cf2603de9f9dc9654b30a0256d38a'
        assert recipe.count(credit)==1
        recipe=recipe.replace(credit,str(target))
        status['credit_verdict_binding']=dict(proof_run=38471835755,
            proof_sha256=sha(credit_proof_path),source_sha256=selected[credit]['sha256'],
            candidate_path=str(target),candidate_sha256=sha(target),
            scope='Isolated credit-verdict change on the same proved replay-idle physical RTL baseline; fresh paired mapping, not an adopted layout.')
    if profile in ('physical_idle_credit_eop','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
        from run_cloud_advert_eop import candidate as eop_candidate
        eop_path=output/'eop-source-bound-proof.json'
        eop_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38476888145-1-advert-eop/advert-eop-38476888145-1.json'
        subprocess.run(['curl','--fail','--location','--retry','4',eop_url,'-o',str(eop_path)],check=True)
        assert sha(eop_path)=='58c6fb6035fa5018d220138e003b12669e42ae2e9e22443b9dbffe1a9a9ee37c'
        eop=json.loads(eop_path.read_text())
        assert eop['status']=='PASS_ACTUAL_ADVERTISER_ARBITER_REGION_EQUIVALENCE_AND_BUFFERED_PORTS_NOT_TIMING'
        assert [p['refresh_cycles'] for p in eop['proofs']]==[128,0,1,128]
        assert all(p['passed'] for p in eop['proofs'][:3]) and eop['proofs'][3]['negative_rejected']
        assert eop['proofs'][3]['counterexample_sha256']=='6649b87f34c57bc8173152f1c582dc22b2b679f72f153b257177842cd1781ef6'
        assert [p['actual_tests'] for p in eop['ports']]==[
            dict(passed=5,failed=0,skipped=0),dict(passed=5,failed=0,skipped=0),dict(passed=0,failed=5,skipped=0)]
        paths={Path(old).name:(old,pin) for old,pin in selected.items() if Path(old).name.startswith('soc_pcie_')}
        assert len(paths)==21
        for name,(old,pin) in paths.items():
            actual=(output/('candidate-'+name)) if name in ('soc_pcie_replay_tx.v','soc_pcie_credit_tx.v') else Path(pin['path'])
            assert sha(actual)==eop['source_binding']['selected'][name]['sha256'],name
        parent,pin=paths['soc_pcie_buffered_flow_packets.v']
        assert pin['sha256']==eop['source_binding']['source_sha256']
        # The exact top instantiation overrides APB_TIMEOUT only; the native
        # parent default FC_REFRESH_CYCLES=128 is within the proved cases.
        top=Path(selected[manifest['old_root']+'/hw/soc/rtl/soc_top.v']['path']).read_text()
        assert 'soc_pcie_buffered_flow_packets #(.APB_TIMEOUT(APB_TIMEOUT)) u_pcie (' in top
        assert 'RX_SLOTS_PER_CLASS=2,FC_REFRESH_CYCLES=128' in Path(pin['path']).read_text()
        target=output/'candidate-soc_pcie_buffered_flow_packets.v'
        target.write_text(eop_candidate(Path(pin['path']).read_text()))
        assert sha(target)==eop['source_binding']['candidate_sha256']=='27168904071b6b66087fbbfc532e12a1ade1dcf1fd6b9078b0ad01472e17d942'
        assert recipe.count(parent)==1
        recipe=recipe.replace(parent,str(target))
        status['eop_owner_binding']=dict(proof_run=38476888145,proof_sha256=sha(eop_path),
            candidate_path=str(target),candidate_sha256=sha(target),
            scope='Actual reset-reachable producer/arbiter/egress proof and all frozen buffered port tests. EOP ready transformation; combined study also applies separately proved ACK-window logic. Fresh paired unplaced screen; not final timing.')
    if profile in ('physical_idle_credit_window','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
        from run_cloud_ack_window import candidate as window_candidate
        window_path=output/'ack-window-source-bound-proof.json'
        window_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38479260742-1-ack-window/ack-window-38479260742-1.json'
        subprocess.run(['curl','--fail','--location','--retry','4',window_url,'-o',str(window_path)],check=True)
        assert sha(window_path)=='77e3d9cbd7682bc2ae485d6b30d6105a4a83163ff4ce4e784997de6a2b4ffd64'
        window=json.loads(window_path.read_text())
        assert window['status']=='PASS_ALL_INPUT_ACK_WINDOW_AND_PHYSICAL_REPLAY_CONTROLS_NOT_TIMING'
        assert [(p['cw'],p['negative']) for p in window['algebra']]==[(cw,bad) for cw in (2,3,4,5) for bad in (False,True)]
        assert all(p['negative_rejected'] if p['negative'] else p['passed'] for p in window['algebra'])
        assert window['proofs'][0]['passed'] and window['proofs'][1]['negative_rejected']
        assert [p['actual_tests'] for p in window['ports']]==[
            dict(passed=7,failed=0,skipped=0),dict(passed=4,failed=0,skipped=0),
            dict(passed=7,failed=0,skipped=0),dict(passed=4,failed=0,skipped=0),
            dict(passed=1,failed=6,skipped=0)]
        paths={Path(old).name:(old,pin) for old,pin in selected.items() if Path(old).name.startswith('soc_pcie_')}
        assert len(paths)==21
        for name,(old,pin) in paths.items():
            actual=(output/('candidate-'+name)) if name in ('soc_pcie_replay_tx.v','soc_pcie_credit_tx.v') else Path(pin['path'])
            assert sha(actual)==window['source_binding']['selected'][name]['sha256'],name
        baseline=output/'candidate-soc_pcie_replay_tx.v'
        assert sha(baseline)==window['source_binding']['source_sha256']
        target=output/'candidate-window-soc_pcie_replay_tx.v'
        target.write_text(window_candidate(baseline.read_text()))
        assert sha(target)==window['source_binding']['candidate_sha256']=='5a65cd18f765120555a193e1bacddb61e0bd5eb175350b41502c678a5ff5b47a'
        assert recipe.count(str(baseline))==1
        recipe=recipe.replace(str(baseline),str(target))
        status['ack_window_binding']=dict(proof_run=38479260742,proof_sha256=sha(window_path),
            candidate_path=str(target),candidate_sha256=sha(target),
            scope='Direct bounded modulo ACK membership, proven for all CW2..5 encodings and exact physical replay with complete port controls. Compare against physical_idle_credit. EOP is included only in the explicit combined hypothesis; neither isolated candidate was timing-adopted. Not final timing.')

    if profile=='physical_idle_credit_window_eop_refresh':
        from run_cloud_fc_refresh import verify as verify_refresh
        fc_old,fc_pin=paths['soc_pcie_fc_tx.v']
        crc_old,crc_pin=paths['soc_pcie_crc16_byte.v']
        target,refresh_proof=verify_refresh(fc_pin['path'],crc_pin['path'],
                                            output/'refresh-partition-proof')
        assert refresh_proof['status']=='PASS_MODULE_REFRESH_PARTITION_EQUIVALENCE_NOT_TIMING'
        assert recipe.count(fc_old)==1
        recipe=recipe.replace(fc_old,str(target))
        status['refresh_partition_binding']=refresh_proof
    if profile=='physical_idle_credit_window_eop_snapshot':
        from run_cloud_fc_snapshot import verify as verify_snapshot
        fc_old,fc_pin=paths['soc_pcie_fc_tx.v']
        crc_old,crc_pin=paths['soc_pcie_crc16_byte.v']
        target,snapshot_proof=verify_snapshot(fc_pin['path'],crc_pin['path'],
                                              output/'snapshot-decode-proof')
        assert snapshot_proof['status']=='PASS_MODULE_SNAPSHOT_DECODE_EQUIVALENCE_NOT_TIMING'
        assert recipe.count(fc_old)==1
        recipe=recipe.replace(fc_old,str(target))
        status['snapshot_decode_binding']=snapshot_proof
    if profile=='physical_idle_credit_window_body':
        import run_cloud_advert_body as body_proof
        body_proof.OUT=output/'body-owner-proof'
        body_proof.main()
        body=json.loads((body_proof.OUT/'result.json').read_text())
        assert body['status']=='PASS_ACTUAL_ADVERTISER_BODY_OWNER_REGION_AND_BUFFERED_PORTS_NOT_TIMING'
        parent,pin=paths['soc_pcie_buffered_flow_packets.v']
        assert body['source_binding']['source_sha256']==pin['sha256']
        assert all(p['passed'] for p in body['proofs'][:3]) and body['proofs'][3]['negative_rejected']
        target=body_proof.OUT/'candidate-rtl/soc_pcie_buffered_flow_packets.v'
        previous=output/'candidate-soc_pcie_buffered_flow_packets.v'
        assert recipe.count(str(previous))==1
        recipe=recipe.replace(str(previous),str(target))
        body['candidate_path']=str(target)
        body['candidate_sha256']=sha(target)
        body['helper_sha256']=sha(Path(body_proof.__file__))
        assert body['candidate_sha256']==body['source_binding']['candidate_sha256']
        status['body_owner_binding']=body
    if profile=='physical_idle_credit_window_reset':
        import run_cloud_advert_reset as body_proof
        body_proof.OUT=output/'reset-dominance-proof'
        body_proof.main()
        body=json.loads((body_proof.OUT/'result.json').read_text())
        assert body['status']=='PASS_ACTUAL_ADVERTISER_RESET_DOMINANCE_REGION_AND_BUFFERED_PORTS_NOT_TIMING'
        parent,pin=paths['soc_pcie_buffered_flow_packets.v']
        assert body['source_binding']['source_sha256']==pin['sha256']
        assert all(p['passed'] for p in body['proofs'][:3]) and body['proofs'][3]['negative_rejected']
        target=body_proof.OUT/'candidate-rtl/soc_pcie_buffered_flow_packets.v'
        previous=output/'candidate-soc_pcie_buffered_flow_packets.v'
        assert recipe.count(str(previous))==1
        recipe=recipe.replace(str(previous),str(target))
        body['candidate_path']=str(target)
        body['candidate_sha256']=sha(target)
        body['helper_sha256']=sha(Path(body_proof.__file__))
        assert body['candidate_sha256']==body['source_binding']['candidate_sha256']
        status['reset_dominance_binding']=body
    if profile=='physical_idle_credit_window_factored':
        import run_cloud_advert_factored as body_proof
        body_proof.OUT=output/'factored-owner-proof'
        body_proof.main()
        body=json.loads((body_proof.OUT/'result.json').read_text())
        assert body['status']=='PASS_ACTUAL_ADVERTISER_FACTORED_EOP_REGION_AND_BUFFERED_PORTS_NOT_TIMING'
        parent,pin=paths['soc_pcie_buffered_flow_packets.v']
        assert body['source_binding']['source_sha256']==pin['sha256']
        assert all(p['passed'] for p in body['proofs'][:3]) and body['proofs'][3]['negative_rejected']
        target=body_proof.OUT/'candidate-rtl/soc_pcie_buffered_flow_packets.v'
        previous=output/'candidate-soc_pcie_buffered_flow_packets.v'
        assert recipe.count(str(previous))==1
        recipe=recipe.replace(str(previous),str(target))
        body['candidate_path']=str(target)
        body['candidate_sha256']=sha(target)
        body['helper_sha256']=sha(Path(body_proof.__file__))
        assert body['candidate_sha256']==body['source_binding']['candidate_sha256']
        status['factored_owner_binding']=body
    if profile in ('physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):

        # Each isolated transformation is proved at its complete module boundary.
        # Exercise their composition on the exact mapped source set before STA.
        from cocotb_results import count_results
        iverilog=shutil.which('iverilog')
        assert iverilog
        status['joint_controls']=[]
        for case in ('baseline','combined'):
            rtl=output/('joint-rtl-'+case)
            rtl.mkdir()
            for name,(old,pin) in paths.items():
                actual=Path(pin['path'])
                if name in ('soc_pcie_replay_tx.v','soc_pcie_credit_tx.v'):
                    actual=output/('candidate-'+name)
                if case=='combined' and name=='soc_pcie_replay_tx.v':
                    actual=output/'candidate-window-soc_pcie_replay_tx.v'
                if case=='combined' and name=='soc_pcie_buffered_flow_packets.v':
                    actual=output/'candidate-soc_pcie_buffered_flow_packets.v'
                if case=='combined' and profile=='physical_idle_credit_window_eop_refresh' and name=='soc_pcie_fc_tx.v':
                    actual=output/'refresh-partition-proof/soc_pcie_fc_tx.v'
                if case=='combined' and profile=='physical_idle_credit_window_eop_snapshot' and name=='soc_pcie_fc_tx.v':
                    actual=output/'snapshot-decode-proof/soc_pcie_fc_tx.v'
                if case=='combined' and profile=='physical_idle_credit_window_body' and name=='soc_pcie_buffered_flow_packets.v':
                    actual=output/'body-owner-proof/candidate-rtl/soc_pcie_buffered_flow_packets.v'
                if case=='combined' and profile=='physical_idle_credit_window_reset' and name=='soc_pcie_buffered_flow_packets.v':
                    actual=output/'reset-dominance-proof/candidate-rtl/soc_pcie_buffered_flow_packets.v'
                if case=='combined' and profile=='physical_idle_credit_window_factored' and name=='soc_pcie_buffered_flow_packets.v':
                    actual=output/'factored-owner-proof/candidate-rtl/soc_pcie_buffered_flow_packets.v'
                shutil.copyfile(actual,rtl/name)
            before={p.name:sha(p) for p in rtl.glob('*.v')}
            assert len(before)==21
            for script,top,expected_tests in (
                ('check_pcie_replay.py','soc_pcie_replay_tx',7),
                ('check_pcie_replay.py','soc_pcie_reliable_packets',4),
                ('check_pcie_rx_flow.py','soc_pcie_buffered_flow_packets',5)):
                out=output/('joint-ports-'+case+'-'+top)
                log=output/('joint-ports-'+case+'-'+top+'.log')
                with log.open('x') as stream:
                    result=subprocess.run([sys.executable,ROOT/'scripts'/script,
                        '--top',top,'--out',out,'--rtl-dir',rtl,
                        '--iverilog-dir',Path(iverilog).parent],
                        stdout=stream,stderr=subprocess.STDOUT)
                record=json.loads((out/'result.json').read_text())
                xml=out/'results.xml'
                counts=count_results([xml]) if xml.is_file() else None
                status['joint_controls'].append(dict(case=case,top=top,
                    returncode=result.returncode,source_sha256=before,
                    expected_tests=expected_tests,actual_tests=dict(zip(('passed','failed','skipped'),counts)) if counts is not None else None,
                    result_sha256=sha(out/'result.json'),xml_sha256=sha(xml) if xml.is_file() else None,
                    log_sha256=sha(log)))
                assert result.returncode==0 and counts==(expected_tests,0,0)
                assert before=={p.name:sha(p) for p in rtl.glob('*.v')}
        status['combined_scope']='Source-bound component formal equivalences plus fresh baseline/combined32 public-port cases; refresh or snapshot profile additionally proves the exact FC module state at nine parameter values. Mapping hypothesis only: neither isolated candidate was timing-accepted; combined physical timing and full-SoC equivalence remain unproven.'

    status['physical_source_binding']=dict(
        physical_result_sha256='616eee906f67d937bb29fa23b586626f7cb7df9f11c5103257fd22323ade7d17',
        original_mapping_status=mapping['status'], corrected_mapping_audit_status=audit['status'],
        recipe_sha256=expected[prefix+'/map10/soc_top_syn.ys'],
        original_physical_netlist_sha256=physical['inputs'][prefix+'/map10/soc_top.netlist.v'],
        selected=selected, proof_sha256=sha(proof_path), proof_run=38465877636,
        scope='Exact source recipe of current physical profile, before subsequent physical ECOs. Fresh paired synthesis/unplaced STA only; does not reuse old placed instances or prove final timing.')
    return recipe, prefix+'/map10'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['baseline', 'ack', 'physical_baseline', 'physical_idle', 'physical_idle_credit', 'physical_idle_credit_eop', 'physical_idle_credit_window', 'physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'], required=True)
    args = parser.parse_args()
    output = ROOT / 'cloud-ack-map' / args.profile
    output.mkdir(parents=True, exist_ok=False)
    status = dict(status='RUNNING', profile=args.profile, adopted=False,
                  scope='Unplaced comparison only. Vendor SRAM models, original clocks. No routed timing, full PHY, qualified RC or production signoff.')
    def save():
        (output / 'result.json').write_text(json.dumps(status, indent=2) + '\n')
    save()
    try:
        spec = json.loads((ROOT / 'docs/evidence/pcie-ack-map-cloud-input-20261012.json').read_text())
        archive = ROOT / spec['archive']
        assert sha(archive) == spec['sha256']
        inputs = output / 'inputs'
        with tarfile.open(archive) as tar:
            tar.extractall(inputs, filter='data')
        manifest = json.loads((inputs / 'manifest.json').read_text())
        for name, pin in manifest['files'].items():
            assert sha(inputs / name) == pin['sha256']
        mapping = output / 'map'
        mapping.mkdir()
        oldroot = manifest['old_root']
        oldpdk = manifest['old_pdk']
        oldoutput = oldroot + '/hw/soc/out/pcie-npu-wake-20261012/map16'
        recipe = (inputs / manifest['recipe']).read_text()
        if args.profile.startswith('physical_'):
            recipe, oldoutput = physical_recipe(inputs, manifest, output, args.profile, status)
        if args.profile == 'ack':
            old = oldroot + '/hw/soc/out/pcie-replay-successor-register-20261012/candidate01/soc_pcie_replay_tx.v'
            new = oldroot + '/hw/soc/out/pcie-ack-delta-lookahead-20261012/candidate01/soc_pcie_replay_tx.v'
            assert recipe.count(old) == 1
            recipe = recipe.replace(old, new)
        recipe = recipe.replace(oldoutput, str(mapping)).replace(oldroot, str(inputs / 'root')).replace(oldpdk, str(inputs / 'pdk'))
        if args.profile == 'physical_idle_credit_window_eop_d2000':
            # Tighten only combinational mapping. Original clocks, port delays,
            # uncertainty, SRAM views and all STA corners remain unchanged.
            abc_lines=[line for line in recipe.splitlines() if line.startswith('abc ')]
            assert len(abc_lines)==1 and '-liberty ' in abc_lines[0] and '-constr ' in abc_lines[0]
            before=abc_lines[0]
            assert re.search(r' -D 4000$',before), before
            assert '-dff' not in before and '-retime' not in before
            after=re.sub(r' -D 4000$', ' -D 2000', before)
            assert before != after and recipe.count(before)==1
            recipe=recipe.replace(before,after)
            status['mapping_delay_target']=dict(baseline_ps=4000,candidate_ps=2000,
                original_abc_command=before,candidate_abc_command=after,
                reference='https://yosyshq.readthedocs.io/projects/yosys/en/0.40/cmd/abc.html',
                scope='Exact EOP+ACK-window physical RTL, original FF mapping and ABC constraints. Only combinational ABC target changes. No -dff/retime, SDC exception, clock-period change, source logic modification or timing acceptance.')
        if args.profile == 'physical_idle_credit_window_eop_slowmap':
            # Optimize the failing setup corner without changing flop mapping,
            # clocks, loads or the independent three-corner STA.
            abc_lines = [line for line in recipe.splitlines() if line.startswith('abc ')]
            assert len(abc_lines) == 1
            before = abc_lines[0]
            assert re.search(r' -D 4000$', before) and '-constr ' in before
            assert '-dff' not in before and '-retime' not in before
            typical_name = 'sg13g2_stdcell_typ_1p20V_25C.lib'
            slow_name = 'sg13g2_stdcell_slow_1p08V_125C.lib'
            assert before.count(typical_name) == 1
            after = before.replace(typical_name, slow_name)
            lib_match = re.search(r'-liberty (\S+)', after)
            assert lib_match
            slow_lib = Path(lib_match.group(1))
            assert sha(slow_lib) == 'ed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d'
            assert recipe.count(before) == 1
            recipe = recipe.replace(before, after)
            status['mapping_corner_study'] = dict(
                original_abc_command=before, candidate_abc_command=after,
                slow_lib_sha256=sha(slow_lib), target_ps=4000,
                scope='Only combinational ABC Liberty changes from typical to slow. Original sequential mapping, RTL, SDC, drive/load constraints and all STA corners remain. Unplaced experiment; not adopted or signoff.')
        script = mapping / 'synthesis.ys'
        script.write_text(recipe)
        if args.profile.startswith('physical_'):
            status['physical_source_binding']['relocated_recipe_sha256'] = sha(script)
            save()
        yosys = shutil.which('yosys')
        assert yosys
        status['runtime'] = subprocess.check_output([yosys, '-V'], text=True).strip()
        if args.profile == 'physical_idle_credit_window_eop_d2000':
            help_text=subprocess.check_output([yosys,'-Q','-T','-p','help abc'],text=True)
            assert '-D <picoseconds>' in help_text
            (output/'native-abc-help.log').write_text(help_text)
            status['mapping_delay_target']['native_help_sha256']=sha(output/'native-abc-help.log')
        status['archive_sha256'] = spec['sha256']
        save()
        with (mapping / 'synthesis.log').open('w') as log:
            subprocess.run([yosys, '-s', str(script)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        mapped = json.loads((mapping / 'soc_top.mapped.json').read_text())['modules']['soc_top']
        macros = dict(collections.Counter(c['type'] for c in mapped['cells'].values() if c['type'].startswith('RM_IHPSG13')))
        assert sum(macros.values()) == 20
        status['macros'] = macros
        status['ports'] = {n: [p['direction'], len(p['bits'])] for n, p in mapped['ports'].items()}
        status['parameters'] = mapped['parameter_default_values']
        status['mapped_cells'] = len(mapped['cells'])
        save()
        constraints = output / 'constraints'
        subprocess.run([sys.executable, str(ROOT / 'scripts/pcie_soc_constraints.py'),
                        '--mapped-json', str(mapping / 'soc_top.mapped.json'), '--out', str(constraints)], check=True)
        template = (inputs / 'root/hw/soc/out/pcie-ack-delta-lookahead-20261012/read05.py').read_text()
        changes = {
            "b=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012'": f'b=Path({str(output)!r})',
            "app=root/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'": f'app=Path({os.environ["CLOUD_APPIMAGE"]!r})',
            "net=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012/map04/soc_top.netlist.v'": f'net=Path({str(mapping / "soc_top.netlist.v")!r})',
            "sdc=root/'hw/soc/out/pcie-ack-delta-lookahead-20261012/constraints04/development.sdc'": f'sdc=Path({str(constraints / "development.sdc")!r})',
            oldpdk: str(inputs / 'pdk'),
        }
        for old, new in changes.items():
            assert template.count(old) == 1, old
            template = template.replace(old, new)
        screen = output / 'screen.py'
        screen.write_text(template)
        subprocess.run([sys.executable, str(screen)], check=True)
        result = json.loads((output / 'screen05/result.json').read_text())
        assert result['status'] == 'COMPLETE_UNPLACED_REPAIR_REQUIRES_GRAPH_AND_PORT_PROOF'
        assert all(sha(inputs / name) == pin['sha256'] for name, pin in manifest['files'].items())
        if args.profile.startswith('physical_'):
            assert all(sha(Path(pin['path']))==pin['sha256'] for pin in status['physical_source_binding']['selected'].values())
        if args.profile in ('physical_idle_credit','physical_idle_credit_eop','physical_idle_credit_window','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
            pin=status['credit_verdict_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile in ('physical_idle_credit_eop','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
            pin=status['eop_owner_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile in ('physical_idle_credit_window','physical_idle_credit_window_eop','physical_idle_credit_window_eop_refresh','physical_idle_credit_window_eop_snapshot','physical_idle_credit_window_body','physical_idle_credit_window_factored','physical_idle_credit_window_reset','physical_idle_credit_window_eop_d2000','physical_idle_credit_window_eop_slowmap'):
            pin=status['ack_window_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile=='physical_idle_credit_window_eop_refresh':
            pin=status['refresh_partition_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile=='physical_idle_credit_window_eop_snapshot':
            pin=status['snapshot_decode_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile=='physical_idle_credit_window_body':
            pin=status['body_owner_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile=='physical_idle_credit_window_reset':
            pin=status['reset_dominance_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        if args.profile=='physical_idle_credit_window_factored':
            pin=status['factored_owner_binding']
            assert sha(Path(pin['candidate_path']))==pin['candidate_sha256']
        status['status'] = 'COMPLETE_UNPLACED_SCREEN_NOT_TIMING_CLOSURE'
        status['screen_result'] = result
    except BaseException as error:
        status.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
