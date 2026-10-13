#!/usr/bin/env python3
"""Same-input hosted baseline/ACK mapping and unplaced three-corner screening."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
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
    if profile=='physical_idle':
        from run_cloud_replay_idle import candidate
        altered=candidate(Path(selected[replay]['path']).read_text())
        target=output/'candidate-soc_pcie_replay_tx.v'
        target.write_text(altered)
        assert sha(target)==proof['candidate_sha256']=='1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc'
        assert recipe.count(replay)==1
        recipe=recipe.replace(replay,str(target))
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
    parser.add_argument('--profile', choices=['baseline', 'ack', 'physical_baseline', 'physical_idle'], required=True)
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
        script = mapping / 'synthesis.ys'
        script.write_text(recipe)
        if args.profile.startswith('physical_'):
            status['physical_source_binding']['relocated_recipe_sha256'] = sha(script)
            save()
        yosys = shutil.which('yosys')
        assert yosys
        status['runtime'] = subprocess.check_output([yosys, '-V'], text=True).strip()
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
        status['status'] = 'COMPLETE_UNPLACED_SCREEN_NOT_TIMING_CLOSURE'
        status['screen_result'] = result
    except BaseException as error:
        status.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
