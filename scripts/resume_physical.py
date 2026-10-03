#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify the pinned physical archive and restore its last completed state.

No RTL synthesis or floorplan regeneration is performed. The saved resolved
configuration is retained, including disabled foundry decks; separate deck
acceptance is still required. Verification never treats interim metrics as PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from collect_physical_checkpoint import digest, restore

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT/'docs/evidence/physical-route-checkpoint-20260922.json'


def prepare(root, archive, receipt, verify_only=False):
    root = root.resolve()
    if digest(archive) != receipt['artifact_sha256']:
        raise ValueError('Archive digest mismatch')
    out = root/'hw/soc/out/route-resume'
    config_path = root/'hw/soc/pnr/config.resolved.route-resume.json'
    if not verify_only and (out.exists() or config_path.exists()):
        raise ValueError('Refusing to overwrite resume outputs')
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('Duplicate archive members')
        prefix = receipt['checkpoint_member']+'/'

        def checked(name, expected):
            with z.open(name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('Archive member digest mismatch: '+name)

        checked(prefix+'manifest.json', receipt['checkpoint_manifest_sha256'])
        manifest = json.loads(z.read(prefix+'manifest.json'))
        if manifest['status'] != 'CAPTURED':
            raise ValueError('Incomplete checkpoint')
        checked(prefix+'state.relative.json', manifest['relative_state_sha256'])
        checked(prefix+'state.original.json', manifest['source_state_sha256'])
        for name, item in manifest['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Unsafe checkpoint member')
            checked(prefix+name, item['sha256'])
        checked(receipt['config_member'], receipt['config_sha256'])
        config = json.loads(z.read(receipt['config_member']))
        # Use the original resolved input, not a step snapshot which serializes
        # native 5.0 to integer 5 and can disable LibreLane's timing derate.
        if type(config['TIME_DERATING_CONSTRAINT']) is not float or config['TIME_DERATING_CONSTRAINT'] != 5.0:
            raise ValueError('Expected native 5.0 timing derate')
        inputs = json.loads(z.read('out/current-full/inputs.json'))
        inventory = {**inputs['sources'], **inputs['implementation_files']}
        inventory['hw/soc/pnr/'+inputs['physical_config']['path']] = inputs['physical_config']['sha256']
        for name, expected in inventory.items():
            path = (root/name).resolve()
            if not path.is_relative_to(root) or not path.is_file() or digest(path) != expected:
                raise ValueError('Prepared source changed or missing: '+name)
        rom_member = 'out/current-full/synthesis/boot-rom/soc_logic_boot_rom.v'
        checked(rom_member, inputs['boot_rom_sha256'])
        checked('out/current-full/firmware/test_soc.bin', inputs['boot_image_sha256'])
        checked('out/current-full/synthesis/soc_top.netlist.v', inputs['netlist_sha256'])
        old_root = manifest['source_state'].split('/hw/soc/pnr/runs/')[0]

        def relocate(value):
            if isinstance(value, dict):
                return {k: relocate(v) for k, v in value.items()}
            if isinstance(value, list):
                return [relocate(v) for v in value]
            if isinstance(value, str) and value.startswith(old_root+'/'):
                relative = value[len(old_root)+1:]
                if relative == 'hw/soc/'+rom_member:
                    return str(out/'soc_logic_boot_rom.v')
                return str(root/relative)
            return value

        config = relocate(config)
        result = {'status': 'VERIFIED', 'scope': 'Restart integrity only; no layout acceptance',
                  'source_run': receipt['run_id'], 'archive_sha256': digest(archive),
                  'source_files_verified': len(inventory), 'checkpoint_views_verified': len(manifest['files']),
                  'resume_from': receipt['resume_from'], 'config': str(config_path)}
        if verify_only:
            return result
        out.mkdir(parents=True)
        bundle = out/'checkpoint'
        for name in ['manifest.json', 'state.relative.json', 'state.original.json', *manifest['files']]:
            target = bundle/name
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(prefix+name) as src, target.open('xb') as dest:
                shutil.copyfileobj(src, dest)
        (out/'soc_logic_boot_rom.v').write_bytes(z.read(rom_member))
        result['state'] = str(restore(bundle))
        config_path.write_text(json.dumps(config, indent=2)+'\n')
        result['restored_config_sha256'] = digest(config_path)
        (out/'restore.json').write_text(json.dumps(result, indent=2)+'\n')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT, args.archive, json.loads(RECEIPT.read_text()), args.verify_only), indent=2))


if __name__ == '__main__':
    main()
