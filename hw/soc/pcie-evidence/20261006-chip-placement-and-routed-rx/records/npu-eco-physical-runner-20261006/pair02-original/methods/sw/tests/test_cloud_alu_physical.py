# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The paired experiment may change logic, never constraints or macro geometry."""
import copy
import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import run_cloud_alu_physical as physical  # noqa: E402


def config():
    macros = {}
    for master in ('SP6TSRAM512x64', 'DP8TSRAMDP256x16'):
        macros[master] = {'instances': {master+'_'+str(i): {'location': [10+i, 20+i],
            'orientation': 'N' if i % 2 == 0 else 'FS'} for i in range(16)}}
    return dict(CLOCK_PERIOD=20, CLOCK_PORT=['clk_i', 'eth_rx_clk_i', 'eth_tx_clk_i'],
        PNR_SDC_FILE='/source.sdc', SIGNOFF_SDC_FILE='/source.sdc', VERILOG_FILES=['/old.v'],
        MACROS=macros, DIE_AREA=[0, 0, 3326.4, 2475.9], CORE_AREA=[60, 45.36, 3266.4, 2430.54],
        PL_TARGET_DENSITY_PCT=40)


def mapping(cfg):
    return {name: master for master, item in cfg['MACROS'].items() for name in item['instances']}


def write_table(path, headers, rows):
    path.write_text('\t'.join(headers)+'\n'+''.join('\t'.join(map(str, row))+'\n' for row in rows))


def geometry(root, cfg):
    (root/'dbu.txt').write_text('1000\n')
    write_table(root/'macros.tsv', ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status'],
        [[name, master, round(spec['location'][0]*1000), round(spec['location'][1]*1000),
          physical.ODB_ORIENTATION[spec['orientation']], 'LOCKED']
         for master, entry in cfg['MACROS'].items() for name, spec in entry['instances'].items()])
    write_table(root/'signal-pins.tsv', ['name', 'direction', 'signal_type', 'layer',
        'x0_dbu', 'y0_dbu', 'x1_dbu', 'y1_dbu', 'status'],
        [['p'+str(i), 'INPUT', 'SIGNAL', 'Metal2', i*100, 0, i*100+50, 50, 'FIRM'] for i in range(301)])
    write_table(root/'bounds.tsv', ['kind', 'x0_dbu', 'y0_dbu', 'x1_dbu', 'y1_dbu'],
        [[kind]+[round(v*1000) for v in cfg[key]] for kind, key in [('die', 'DIE_AREA'), ('core', 'CORE_AREA')]])


def witness(cfg):
    return dict(schema=1, dbu=1000, macros=[dict(logical=name, native=name, master=master,
        x_dbu=round(spec['location'][0]*1000), y_dbu=round(spec['location'][1]*1000),
        orientation=physical.ODB_ORIENTATION[spec['orientation']])
        for master, entry in cfg['MACROS'].items() for name, spec in entry['instances'].items()])


def test_config_keeps_every_existing_physical_and_clock_setting():
    old = config(); saved = copy.deepcopy(old)
    changed = physical.fresh_config(old, Path('/new.v'), Path('/pins.def'), mapping(old))
    assert old == saved
    assert {k: v for k, v in changed.items() if k in old and k != 'VERILOG_FILES'} == {
        k: v for k, v in old.items() if k != 'VERILOG_FILES'}
    assert changed['FP_TEMPLATE_MATCH_MODE'] == 'strict' and changed['FP_TEMPLATE_COPY_POWER_PINS'] is False


@pytest.mark.parametrize('fault', ['clock', 'sdc', 'master', 'missing_macro', 'competing_io'])
def test_changed_clocks_sdc_macro_mapping_or_pin_placer_rejected(fault):
    cfg = config(); mapped = mapping(cfg)
    if fault == 'clock': cfg['CLOCK_PERIOD'] = 25
    if fault == 'sdc': cfg['SIGNOFF_SDC_FILE'] = '/relaxed.sdc'
    if fault == 'master': mapped[next(iter(mapped))] = 'UNKNOWN'
    if fault == 'missing_macro': mapped.pop(next(iter(mapped)))
    if fault == 'competing_io': cfg['FP_PIN_ORDER_CFG'] = '/other.cfg'
    with pytest.raises(ValueError): physical.fresh_config(cfg, Path('/new.v'), Path('/pins.def'), mapped)


def test_native_geometry_uses_exact_equivalent_def_odb_orientation(tmp_path):
    cfg = config(); geometry(tmp_path, cfg)
    result = physical.geometry_check(tmp_path, cfg, witness(cfg))
    assert set(result) == set(physical.GEOMETRY)
    assert physical.ODB_ORIENTATION['N'] == 'R0' and physical.ODB_ORIENTATION['FS'] == 'MX'


@pytest.mark.parametrize('fault', ['location', 'orientation', 'macro_missing', 'pin_missing', 'pin_duplicate', 'bounds'])
def test_actual_native_geometry_cannot_move_omit_or_duplicate_objects(tmp_path, fault):
    cfg = config(); geometry(tmp_path, cfg)
    path = tmp_path/('macros.tsv' if fault in {'location', 'orientation', 'macro_missing'} else
                     'bounds.tsv' if fault == 'bounds' else 'signal-pins.tsv')
    lines = path.read_text().splitlines()
    if fault == 'location': lines[1] = lines[1].replace('\t10000\t', '\t11000\t', 1)
    if fault == 'orientation': lines[1] = lines[1].replace('\tR0\t', '\tMX\t')
    if fault in {'macro_missing', 'pin_missing'}: lines.pop()
    if fault == 'pin_duplicate': lines.append(lines[-1])
    if fault == 'bounds': lines[1] = lines[1].replace('3326400', '3326401')
    path.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError): physical.geometry_check(tmp_path, cfg, witness(cfg))


def test_full_physical_is_cloud_only(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError): physical.run('candidate', tmp_path/'out', tmp_path/'work')
    assert not (tmp_path/'out').exists()


def test_exact_32_native_name_witness_preserves_bracket_escapes(tmp_path):
    captured = json.loads((physical.ROOT/physical.MACRO_WITNESS).read_text())
    cfg = config(); cfg['MACROS'] = {}
    for row in captured['macros']:
        cfg['MACROS'].setdefault(row['master'], {'instances': {}})['instances'][row['logical']] = dict(
            location=[row['x_dbu']/1000, row['y_dbu']/1000], orientation={'R0': 'N', 'MX': 'FS'}[row['orientation']])
    geometry(tmp_path, cfg)
    path = tmp_path/'macros.tsv'; raw = path.read_text()
    for row in captured['macros']:
        assert '\\[' in row['native'] and '[' in row['logical'] and '\\' not in row['logical']
        raw = raw.replace(row['logical']+'\t', row['native']+'\t')
    path.write_text(raw)
    assert len(physical.macro_contract(cfg, 1000, captured)) == 32
    physical.geometry_check(tmp_path, cfg)
    # An unwitnessed extra escape must not be erased by blanket normalization.
    path.write_text(raw.replace('u_eth.', 'u_\\eth.', 1))
    with pytest.raises(ValueError): physical.geometry_check(tmp_path, cfg)


def test_absent_proof_blocks_before_network_or_native_work(tmp_path, monkeypatch):
    monkeypatch.setattr(physical, 'PROOF_BINDING', None)
    monkeypatch.setattr(physical, 'api', lambda *_: pytest.fail('Network before proof binding'))
    with pytest.raises(ValueError, match='No independently accepted'): physical.proof_gate(tmp_path, tmp_path)


def binding():
    return dict(schema=1, run_id=123, source_commit='a'*40, run_attempt=1, artifacts={
        k: dict(id=i+1, name='alu-partition-common-1' if k == 'common' else 'alu-partition-verdict-1' if k == 'verdict'
                else 'alu-partition-shard-'+k[-1]+'-1', bytes=100, sha256='b'*64)
        for i, k in enumerate(sorted(physical.PROOF_ARTIFACT_KEYS))})


def test_actual_four_state_boot_failure_blocks_even_with_complete_formal_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(physical, 'PROOF_BINDING', binding())
    monkeypatch.setattr(physical, 'api', lambda *_: pytest.fail('Network before boot blocker'))
    assert physical.BOOT_FAILURE['artifact_id'] == 11233351913
    assert physical.BOOT_FAILURE['artifact']['sha256'] == 'f94d5e9046a71adf536de24db530bc12d9435c8e72b6fe3bddc9cba71e57d3cb'
    with pytest.raises(ValueError, match='four-state boot failure'):
        physical.proof_gate(tmp_path, tmp_path)


@pytest.mark.parametrize('fault', ['missing_shard', 'duplicate_id', 'wrong_name', 'wrong_source', 'unbounded_blob'])
def test_proof_binding_requires_exact_complete_source_artifacts(fault):
    row = binding(); assert physical.validate_proof_binding(row) == row
    if fault == 'missing_shard': row['artifacts'].pop('shard3')
    if fault == 'duplicate_id': row['artifacts']['shard3']['id'] = row['artifacts']['shard2']['id']
    if fault == 'wrong_name': row['artifacts']['common']['name'] = 'alu-state-repair-1'
    if fault == 'wrong_source': row['source_commit'] = 'not-a-commit'
    if fault == 'unbounded_blob': row['artifacts']['common']['bytes'] = 2**40
    with pytest.raises(ValueError): physical.validate_proof_binding(row)


def proof_fixture(tmp_path):
    part = physical.partitions
    common = tmp_path/'common'; common.mkdir(); methods = {}
    for name in physical.PROOF_METHOD_PINS:
        source = physical.ROOT/name; dest = common/'methods'/name
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, dest); methods[name] = physical.pin(dest)
    module = dict(ports={'inputs': dict(direction='input', bits=[1]*10828),
                         'outputs': dict(direction='output', bits=[1]*34321)})
    plan = part.make_plan(module, module); physical.common.save(common/'plan.json', plan)
    (common/'common-miter.il').write_text('Unit fixture, no actual native chip proof')
    prepared = dict(github_source_commit='a'*40, status='COMMON_MITER_PREPARED_NOT_PROVED', complete_inputs_rechecked=True,
        methods=methods, runtime=json.loads((physical.ROOT/physical.MANIFEST).read_text())['runtime'],
        native_interface=dict(symbolic_inputs={'in_inputs': 10828}, symbolic_input_bits=10828, native_groups=269),
        original_graph=part.replay.MEMBERS['original-lifted.json'], corrected_graph=part.TIMEOUT_MEMBERS['corrected-candidate-lifted.json'],
        reconstruction_checks=dict(graph_object_equal=True, labels_object_equal=True,
            proposal_exact_serialized_pin=part.TIMEOUT_MEMBERS['corrected-state-proposal.json']),
        common_miter=physical.pin(common/'common-miter.il'), plan=physical.pin(common/'plan.json'))
    prepared['outputs'] = {str(p.relative_to(common)): physical.pin(p) for p in common.rglob('*') if p.is_file()}
    physical.common.save(common/'result.json', prepared)
    dirs = []; rows = []
    for i in range(4):
        directory = tmp_path/('shard'+str(i)); directory.mkdir(); dirs.append(directory)
        text = '\n'.join('NSSOC_GROUP_BEGIN '+g['id']+'\nFinal constraint equation: { } = { }\n'
            'SAT proof finished - no model found: SUCCESS!\nNSSOC_GROUP_END '+g['id']+' 0'
            for g in plan['groups'] if g['shard'] == i)+'\nNSSOC_ALL_ASSIGNED_GROUPS_VISITED\n'
        (directory/'partitions.log').write_text(text)
        groups = part.parse_shard(text, plan, i, directory)
        row = dict(shard=i, groups=groups, status='ALL_ASSIGNED_GROUPS_VISITED', complete_inputs_rechecked=True,
            github_source_commit='a'*40, execution=dict(returncode=0), common_miter=prepared['common_miter'],
            plan=prepared['plan'], methods=methods)
        row['outputs'] = {p.name: physical.pin(p) for p in directory.iterdir() if p.is_file()}
        physical.common.save(directory/'result.json', row); rows.append(row)
    verdict = part.aggregate(plan, rows)
    verdict.update(github_source_commit='a'*40, common_miter=prepared['common_miter'], plan=prepared['plan'],
        shard_results={str(i): physical.pin(d/'result.json') for i, d in enumerate(dirs)})
    dest = tmp_path/'verdict.json'; physical.common.save(dest, verdict)
    return common, dirs, dest


def test_every_group_is_reparsed_before_physical_gate_accepts_binary_relation(tmp_path):
    common, dirs, verdict = proof_fixture(tmp_path)
    result = physical.validate_partition_evidence(common, dirs, verdict, 'a'*40)
    assert result['complete_groups'] == 269 and result['complete_output_obligation_bits'] == 34321
    assert result['symbolic_input_bits'] == 10828 and result['native_execution'] is False


@pytest.mark.parametrize('fault', ['runtime', 'graph', 'relation', 'method', 'missing_group', 'native_log', 'interface',
                                  'narrowed_aggregate', 'assumptions', 'source'])
def test_false_or_incomplete_partition_acceptance_is_rejected(tmp_path, fault):
    common, dirs, verdict = proof_fixture(tmp_path)
    prepared = json.loads((common/'result.json').read_text()); final = json.loads(verdict.read_text())
    if fault == 'runtime': prepared['runtime']['sha256'] = '0'*64
    if fault == 'graph': prepared['corrected_graph']['sha256'] = '0'*64
    if fault == 'relation': prepared['reconstruction_checks']['graph_object_equal'] = False
    if fault == 'method': prepared['methods'].pop(next(iter(prepared['methods'])))
    if fault == 'interface': prepared['native_interface']['symbolic_inputs']['in_inputs'] -= 1
    if fault == 'missing_group':
        path = dirs[0]/'result.json'; row = json.loads(path.read_text()); row['groups'].pop(); physical.common.save(path, row)
    if fault == 'native_log': (dirs[0]/'partitions.log').write_text('native timeout; no success')
    if fault == 'narrowed_aggregate': final['complete_output_obligation_bits'] -= 1
    if fault == 'assumptions': final['no_internal_assumptions'] = False
    if fault == 'source': final['github_source_commit'] = 'b'*40
    physical.common.save(common/'result.json', prepared); physical.common.save(verdict, final)
    with pytest.raises(ValueError): physical.validate_partition_evidence(common, dirs, verdict, 'a'*40)
