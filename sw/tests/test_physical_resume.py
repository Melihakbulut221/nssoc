# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume must use the authenticated design and retain timing constraints."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import collect_physical_checkpoint as collector
import resume_physical as resume


@pytest.fixture
def archive(tmp_path):
    root = tmp_path/'repository with spaces'
    run = root/'hw/soc/pnr/runs/current-full'
    step = run/'37-sta'
    step.mkdir(parents=True)
    views = {}
    for key in ('odb', 'nl', 'sdc'):
        path = step/('soc_top.'+key)
        path.write_text('real view '+key)
        views[key] = str(path)
    views['metrics'] = {'timing__setup__wns': -4.2}
    (step/'state_out.json').write_text(json.dumps(views))
    bundle = root/'hw/soc/out/captured'
    collector.capture(root, run, bundle)
    source = root/'hw/soc/rtl/soc_top.v'
    source.parent.mkdir(parents=True)
    source.write_text('module soc_top(); endmodule')
    physical = root/'hw/soc/pnr/config-source.json'
    physical.write_text('{}')
    inventory = {'sources': {'hw/soc/rtl/soc_top.v': collector.digest(source)},
                 'implementation_files': {},
                 'physical_config': {'path': physical.name, 'sha256': collector.digest(physical)},
                 'boot_rom_sha256': hashlib.sha256(b'rom').hexdigest(),
                 'boot_image_sha256': hashlib.sha256(b'image').hexdigest(),
                 'netlist_sha256': hashlib.sha256(b'netlist').hexdigest()}
    members = {'out/checkpoint/'+str(p.relative_to(bundle)): p.read_bytes()
               for p in bundle.rglob('*') if p.is_file()}
    members.update({'out/current-full/inputs.json': json.dumps(inventory).encode(),
                    'out/current-full/synthesis/boot-rom/soc_logic_boot_rom.v': b'rom',
                    'out/current-full/synthesis/soc_top.netlist.v': b'netlist',
                    'out/current-full/firmware/test_soc.bin': b'image',
                    'pnr/config.resolved.json': json.dumps({'TIME_DERATING_CONSTRAINT': 5.0,
                        'CLOCK_PERIOD': 20, 'CLOCK_PORT': ['clk_i', 'eth_rx_clk_i', 'eth_tx_clk_i'],
                        'VERILOG_FILES': [str(root/'hw/soc/out/current-full/synthesis/boot-rom/soc_logic_boot_rom.v')]}).encode()})
    path = tmp_path/'source.zip'
    receipt = {'run_id': 123, 'config_member': 'pnr/config.resolved.json',
               'checkpoint_member': 'out/checkpoint', 'resume_from': 'OpenROAD.DetailedRouting'}

    def write():
        with zipfile.ZipFile(path, 'w') as z:
            for name, content in members.items():
                z.writestr(name, content)
        receipt.update(artifact_sha256=collector.digest(path),
                       config_sha256=hashlib.sha256(members['pnr/config.resolved.json']).hexdigest(),
                       checkpoint_manifest_sha256=hashlib.sha256(members['out/checkpoint/manifest.json']).hexdigest())
    write()
    return root, path, receipt, members, write


def test_restore_real_files_and_preserve_config(archive):
    root, path, receipt, _, _ = archive
    verified = resume.prepare(root, path, receipt, True)
    assert verified['source_files_verified'] == 2
    assert not (root/'hw/soc/out/route-resume').exists()
    result = resume.prepare(root, path, receipt)
    state = json.loads(Path(result['state']).read_text())
    assert Path(state['odb']).read_text() == 'real view odb'
    assert state['metrics']['timing__setup__wns'] == -4.2
    config = json.loads(Path(result['config']).read_text())
    assert type(config['TIME_DERATING_CONSTRAINT']) is float
    assert config['CLOCK_PERIOD'] == 20 and len(config['CLOCK_PORT']) == 3
    assert Path(config['VERILOG_FILES'][0]).read_text() == 'rom'
    with pytest.raises(ValueError, match='overwrite'):
        resume.prepare(root, path, receipt)


@pytest.mark.parametrize('mutation', ['archive', 'source', 'view', 'rom', 'derate', 'traversal'])
def test_reject_corruption_or_design_change(archive, mutation):
    root, path, receipt, members, write = archive
    if mutation == 'archive':
        path.write_bytes(path.read_bytes()+b'corruption')
    elif mutation == 'source':
        (root/'hw/soc/rtl/soc_top.v').write_text('changed')
    elif mutation == 'view':
        name = next(n for n in members if n.endswith('.odb'))
        members[name] = b'changed'
        write()
    elif mutation == 'rom':
        members['out/current-full/synthesis/boot-rom/soc_logic_boot_rom.v'] = b'changed'
        write()
    elif mutation == 'derate':
        members['pnr/config.resolved.json'] = b'{"TIME_DERATING_CONSTRAINT": 5}'
        write()
    elif mutation == 'traversal':
        manifest = json.loads(members['out/checkpoint/manifest.json'])
        manifest['files']['../../escape'] = {'sha256': '0'*64}
        members['out/checkpoint/manifest.json'] = json.dumps(manifest).encode()
        write()
    with pytest.raises(ValueError):
        resume.prepare(root, path, receipt)
    assert not (root/'hw/soc/out/route-resume').exists()
