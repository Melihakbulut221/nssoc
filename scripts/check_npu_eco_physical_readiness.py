#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Offline prerequisite gate for one ALU/NPU physical experiment, never signoff.

Reuse the independently accepted, source-pinned cloud binary proof. Do not claim
a new local read of its original full graphs. Join that relation to the exact
Boolean ECO and completed native SRAM mapping, then require a separately
completed successful strict vendor-model boot of those same ECO bytes.
Historical verifiers and failed receipts are neither imported nor modified.
"""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = Path('hw/soc/out/heartbeat-20261003-1347/abc-audit')
MAPPING = Path('hw/soc/out/npu-eco-mapping-20261006')
STARTUP = Path('hw/soc/out/npu-init-delivery-20261006/cloud-recovery-startup01')
PROOF_DOCUMENT = 'docs/evidence/closure-raw-audits-20261003-1347.json'
PROOF_SHA = '1691583c68b4c79198e5aa1671e685e7b9588f8d788a9b8ee02572b6272cdd72'
MAPPING_FREEZE_SHA = '51d4524f8d020a2acf01aca7f2712fabf32b4f88cdc2056760675a4be28ac54e'
MAPPING_PEER_SHA = '2b7e3bfd2b2ee84fc6fa155971770f8241c161a2035c1747fcad3237b83d848b'
STARTUP_SHA = 'be525d10014f55f055861eb7971a44cea8e86e7924644a110485e6861010aa7e'
ECO_METHOD_SHA = 'af33478671d278b959c44a7623e9408370415c5c8f369cb18e5dd67332c74980'
BOOT_RUN = 37403350883
BOOT_COMMIT = 'c82d1280052c0da65281d87cda9af3b1c6177291'
PROOF_COMMIT = 'a2e562699fcb24a338d6b7d3cf5d516db07bbd9d'
PAIR = {
    'original': {'bytes': 10274923, 'sha256': '5d05a3bc48cdd8c92dd51e61f1cff81f52e7ffcb973c2a8256f21b6648857fd8'},
    'candidate': {'bytes': 10370597, 'sha256': 'ff0fa54dac1855c21c43e3c463042ff21eefa3be65f8481ba79701742c5f796c'},
}
FACTORED = {'bytes': 10370852, 'sha256': '26b3deaa9126d5d01361e75033b199a58bc111c508e50cab8c68a93c81c02696'}
PHYSICAL_INPUT = {'bytes': 10840297, 'sha256': 'dcf832474aaa639ee48b3cbcbec6e6daf70569f856d15dffae6c34b483119060'}
HARD = {('__mapped_state_equiv_ff_d', 738), ('__mapped_state_equiv_ff_d', 5732),
        ('__mapped_state_equiv_gate_enable', 0), ('__mapped_state_equiv_gate_next', 0)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def document(path, expected=None):
    if expected is not None:
        actual = pin(path)
        require(actual == expected if isinstance(expected, dict) else actual['sha256'] == expected,
                'Pinned evidence differs: ' + str(path))
    return json.loads(Path(path).read_text())


def identities(rows):
    require(all(isinstance(r, list) and len(r) == 2 and isinstance(r[0], str)
                and type(r[1]) is int and r[1] >= 0 for r in rows), 'Invalid equation identity')
    result = {tuple(r) for r in rows}
    require(len(result) == len(rows), 'Duplicate equation identity')
    return result


def validate_union(catalog, final, batches):
    """Recount disjoint original identities, including the four hard equations."""
    prior = identities(catalog['preserved_proved'])
    hard = identities([r['original'] for r in catalog['hard']])
    remaining = identities([r['original'] for r in catalog['untested']])
    require((len(prior), len(hard), len(remaining), catalog['original_bits']) == (33517, 4, 800, 34321),
            'Incomplete original equation sets')
    require(hard == HARD, 'Different four hard equations')
    require(not (prior & hard or prior & remaining or hard & remaining), 'Overlapping equation sets')
    require(len(prior | hard | remaining) == 34321, 'Narrowed original relation')
    require(len(batches) == 64 and {r['key'] for r in batches} == {(s, b) for s in range(16) for b in range(4)},
            'Missing or duplicate native batch')
    observed = []
    for r in batches:
        require(r['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'
                and r['inputs'] == 10828 and r['latches'] == 0 and r['assumptions'] == 0
                and r['native_abc_exitcode'] == 0, 'Failed or narrowed native batch')
        observed.extend(r['original_ids'])
    require(identities(observed) == remaining, 'Native batches do not cover the exact 800 equations')
    require(final['status'] == 'COMPLETE_BINARY_BOUNDARY_RELATION_PROVED'
            and final['state_bijection_proved'] is True
            and (final['original_bits'], final['preserved_prior'], final['independently_proved_hard'],
                 final['new_800_proved'], final['total_unique_proved']) == (34321, 33517, 4, 800, 34321)
            and not final['unproved_original_bits'] and not final['actual_counterexample_original_bits']
            and identities(final['proved_800_original_bits']) == remaining,
            'Final proof is incomplete or disagrees with original identities')
    return {'prior': len(prior), 'separate_hard': len(hard), 'grouped_new': len(remaining),
            'total': len(prior | hard | remaining), 'symbolic_inputs': 10828, 'batches': 64}


def verify_binary(root):
    accepted = document(root / PROOF_DOCUMENT, PROOF_SHA)['grouped_abc']['independent_review']
    audit = document(root / accepted['local_path'], {k: accepted[k] for k in ('bytes', 'sha256')})
    require(audit == accepted['document'] and audit['state_relation_proved'] is True
            and audit['source'] == PROOF_COMMIT and audit['run'] == 37108360597,
            'Wrong accepted historical proof')
    base = root / AUDIT
    for name, expected in audit['outputs'].items():
        require(pin(base / name) == expected, 'Historical audit member differs: ' + name)
    common = base / 'common-selected'
    prepared = document(common / 'result.json', audit['prepared_result'])
    require(prepared['github_source_commit'] == PROOF_COMMIT and prepared['complete_inputs_rechecked'] is True,
            'Incomplete historical preparation')
    for name, expected in prepared['methods'].items():
        require(pin(common / 'methods' / name) == expected, 'Historical source method differs: ' + name)
    source = common / 'methods/scripts/prove_alu_mapped_state.py'
    # Read the source-bound input pair without executing historical producer code.
    pair_nodes = [n.value for n in ast.parse(source.read_text()).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'PAIR' for t in n.targets)]
    require(len(pair_nodes) == 1, 'Missing original input pair')
    declared = {ast.literal_eval(k): {kw.arg: ast.literal_eval(kw.value) for kw in v.keywords}
                for k, v in zip(pair_nodes[0].keys, pair_nodes[0].values)}
    require(declared == PAIR, 'Binary proof has different source netlists')
    catalog = document(common / 'catalog.json', prepared['catalog'])
    final = document(base / 'batches/alu-abc-verdict-1/capture/alu-abc-verdict.json', audit['final_verdict'])
    require(final['prepared_result'] == pin(common / 'result.json')
            and final['github_source_commit'] == PROOF_COMMIT, 'Final proof source differs')
    batches = []
    for shard in range(16):
        row = document(base / f'shard-{shard:02d}.json')
        require(row['shard'] == shard and row['exact_input_count'] == 10828, 'Wrong shard interface')
        for b in row['batches']:
            directory = base / f'batches/alu-abc-batch-{shard}-{b["batch"]}-1/capture'
            result = document(directory / 'result.json', b['result'])
            require(pin(directory / 'abc.log') == b['raw_log']
                    and result['proof']['verdict'] == b['verdict']
                    and final['batch_results'][f'{shard}:{b["batch"]}'] == b['result'], 'Native batch binding differs')
            batches.append({**b, 'key': (shard, b['batch'])})
    return {'counts': validate_union(catalog, final, batches), 'accepted_audit': pin(base / 'independent-review.json'),
            'prepared': pin(common / 'result.json'), 'source_netlists': PAIR,
            'original_full_graphs_replayed_locally': False,
            'scope': 'Reused accepted source-pinned cloud proof; original full graphs and prior raw proofs remain their recorded cloud scope.'}


def verify_mapping(root):
    base = root / MAPPING
    frozen = document(base / 'source-freeze01.json', MAPPING_FREEZE_SHA)
    peer = document(base / 'saved-native-peer-pll.json', MAPPING_PEER_SHA)
    require(peer['status'] == 'PASS_SAVED_MATCHED_NPU_MAPPING_GRAPH_AND_THREE_ACTUAL_GRAPH_MUTANTS'
            and peer['findings'] == [], 'Native mapping peer is not accepted')
    row = document(base / 'native01/result.json', peer['native_result'])
    require(row['source_freeze'] == peer['source_freeze'] == pin(base / 'source-freeze01.json')
            and row['status'] == 'PASS_MATCHED32SRAM_MAPPING_AND_EXACT_ECO_BRIDGE_BOOT_PHYSICAL_PENDING',
            'Incomplete or different mapping')
    for name, expected in frozen['inputs'].items():
        require(pin(name) == expected, 'Mapping input differs: ' + name)
    for label, stage in row['stages'].items():
        require(stage['status'] == 'PASS_MAPPING_CONTRACT' and stage['returncode'] == 0,
                'Native mapping stage incomplete')
        for name, expected in stage['outputs'].items():
            require(pin(base / 'native01' / label / name) == expected, 'Native mapping output differs')
        macros = stage['mapping_contract']['macros']
        require(stage['mapping_contract']['top_ports'] == 79
                and Counter(macros.values()) == {'SP6TSRAM512x64': 16, 'DP8TSRAMDP256x16': 16},
                'Changed SRAM or port boundary')
    require(set(row['stages']) == {'original', 'candidate', 'factored'}, 'Missing native mapping variant')
    require(row['exact_combinational_bridge'] == peer['recomputed_exact_bridge']
            and row['exact_combinational_bridge']['unchanged_cells'] == 76714
            and row['exact_combinational_bridge']['all_other_cell_equations_preserved'] is True,
            'Missing complete mapped equation bridge')
    for label, expected in PAIR.items():
        require(pin(frozen['netlists'][label]) == expected, 'Proof-to-mapping source mismatch')
    require(pin(frozen['netlists']['factored']) == FACTORED
            and row['stages']['factored']['netlist'] == PHYSICAL_INPUT, 'Wrong factored physical input')
    method = root / 'scripts/prepare_npu_reconvergence_eco.py'
    require(pin(method)['sha256'] == ECO_METHOD_SHA, 'Unreviewed Boolean ECO method')
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(method.read_text()).body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in {'OLD', 'NEW', 'PREDECESSOR'}}
    before = Path(frozen['netlists']['candidate']).read_text()
    after = Path(frozen['netlists']['factored']).read_text()
    require(before.count(constants['OLD']) == before.count(constants['PREDECESSOR']) == 1
            and before.replace(constants['OLD'], constants['NEW']) == after
            and after.replace(constants['NEW'], constants['OLD']) == before, 'Nonlocal ECO source change')
    for bits in range(16):
        a, b, c, d = [(bits >> i) & 1 for i in range(4)]
        require((1 ^ ((a | b) & (1 ^ (a & c & d)))) == ((c & d) if a else (1 ^ b)),
                'Boolean factoring is not equivalent')
    return {'source_freeze': pin(base / 'source-freeze01.json'), 'saved_peer': pin(base / 'saved-native-peer-pll.json'),
            'native_result': pin(base / 'native01/result.json'), 'factored_vendor_netlist': FACTORED,
            'physical_input': PHYSICAL_INPUT, 'unchanged_mapped_cell_equations': 76714,
            'matched_original': row['stages']['original']['netlist'],
            'matched_original_path': str(base / 'native01/original/soc_top.netlist.v'),
            'binary_cases': 16, 'physical_input_path': str(base / 'native01/factored/soc_top.netlist.v')}


def validate_boot(row, startup, run, artifact, raw_log):
    require(run.get('id') == BOOT_RUN and run.get('head_sha') == BOOT_COMMIT
            and run.get('run_attempt') == 1 and run.get('status') == 'completed'
            and run.get('conclusion') == 'success', 'Strict boot run is not the exact completed success')
    require(artifact.get('name') == 'npu-init-eco-final-1'
            and artifact.get('workflow_run', {}).get('id') == BOOT_RUN
            and artifact['workflow_run'].get('head_sha') == BOOT_COMMIT
            and type(artifact.get('id')) is int and artifact['id'] > 0
            and re.fullmatch(r'sha256:[0-9a-f]{64}', artifact.get('digest', '')),
            'Unbound final boot artifact')
    require(row.get('status') == 'PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY'
            and row.get('github_source_commit') == BOOT_COMMIT
            and row.get('variant') == 'candidate' and row.get('memory') == 'vendor'
            and row.get('cycle_bound') == 3000000, 'Boot is pending, failed, or has a changed workload')
    # All source/model/firmware/compile/method fields match the exact archived startup.
    for key in startup.keys() - {'status', 'scope', 'outputs'}:
        require(row.get(key) == startup[key], 'Boot startup binding changed: ' + key)
    require(row['eco']['original'] == PAIR['candidate'] and row['eco']['candidate'] == FACTORED,
            'Boot tested another ECO')
    ex = row.get('boot_execution', {})
    require(ex.get('returncode') == 0 and ex.get('command') == startup['boot_command'],
            'Native boot process did not complete successfully')
    require(len(re.findall(r'(?m)^QUALIFICATION_MBIST PASS cycles=\d+$', raw_log)) == 1
            and len(re.findall(r'(?m)^LOGICROM_GL PASS checks=28$', raw_log)) == 1
            and re.search(r'(?im)(?:\bFATAL:|\bERROR:|Assertion failed|%Fatal|%Error)', raw_log) is None,
            'Strict native MBIST/28-check boot log failed')
    return {'run': BOOT_RUN, 'source_commit': BOOT_COMMIT, 'artifact_id': artifact['id'],
            'vendor_eco_netlist': FACTORED, 'cycle_bound': 3000000, 'firmware_checks': 28}


def verify_boot(root, archive, run_path, artifact_path):
    require(all(p is not None for p in (archive, run_path, artifact_path)),
            'Completed strict boot archive/run/API artifact metadata are required; running or missing boot blocks readiness')
    startup = document(root / STARTUP / 'result.json', STARTUP_SHA)
    run, artifact = document(run_path), document(artifact_path)
    require(pin(archive) == {'bytes': artifact['size_in_bytes'], 'sha256': artifact['digest'][7:]},
            'Boot archive does not match the API digest')
    with zipfile.ZipFile(archive) as z:
        files = [i for i in z.infolist() if not i.is_dir()]
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate boot archive member')
        require(sum(i.file_size for i in files) <= 2 * 1024**3, 'Boot capture expansion too large')
        for item in z.infolist():
            path = PurePosixPath(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                    and not stat.S_ISLNK(item.external_attr >> 16), 'Unsafe boot archive member')
        row = json.loads(z.read('result.json'))
        result = validate_boot(row, startup, run, artifact, z.read('boot.log').decode())
        require(set(row['outputs']) | {'result.json'} == {i.filename for i in files}, 'Incomplete boot capture')
        for name, expected in row['outputs'].items():
            with z.open(name) as stream:
                actual = {'bytes': z.getinfo(name).file_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
            require(actual == expected, 'Changed boot capture member: ' + name)
        for name, expected in startup['outputs'].items():
            require(row['outputs'].get(name) == expected, 'Startup artifact member changed: ' + name)
        require(row['outputs']['eco/soc_top.netlist.v'] == FACTORED, 'Wrong raw boot netlist')
    return {**result, 'archive': pin(archive), 'startup': pin(root / STARTUP / 'result.json'),
            'api_run': pin(run_path), 'api_artifact': pin(artifact_path), 'full_member_readback': True}


def check(root=ROOT, *, archive=None, run_path=None, artifact_path=None):
    result = {'status': 'BLOCKED', 'physical_flow_executed': False, 'timing_accepted': False,
              'physical_signoff': False, 'historical_failure_records_unchanged': True,
              'readiness_method': pin(__file__)}
    try:
        result['binary_relation'] = verify_binary(root)
        result['mapped_bridge'] = verify_mapping(root)
        result['strict_boot'] = verify_boot(root, archive, run_path, artifact_path)
        result['status'] = 'READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY'
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        result['blocker'] = f'{type(error).__name__}: {error}'
    result['limitations'] = [
        'Binary relation assumes equal corresponding initial FF/latch state and identical opaque SRAM behavior.',
        'Historical original full-graph replay remains the accepted cloud scope; no new native proof is claimed.',
        'Vendor-model boot is tied through the exact SRAM mapping contract, not a transistor proof of the 32 physical SRAMs.',
        'Readiness permits only a separately reviewed experiment. Constraints, placement, CTS, route, all timing classes, physical verification and post-ECO equivalence remain required.',
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot-archive', type=Path)
    parser.add_argument('--boot-run-json', type=Path)
    parser.add_argument('--boot-artifact-json', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = check(archive=args.boot_archive, run_path=args.boot_run_json, artifact_path=args.boot_artifact_json)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    raise SystemExit(0 if result['status'] == 'READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY' else 1)


if __name__ == '__main__':
    main()
