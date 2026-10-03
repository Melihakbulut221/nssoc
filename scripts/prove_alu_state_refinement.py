#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Refine only preserved timeout observations, with every original input symbolic."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import zipfile

import prove_alu_state_partitions as part

state = part.state
ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-state-refinement-input.lock.json'
OWN = ('scripts/prove_alu_state_refinement.py', 'sw/tests/test_alu_state_refinement.py',
       '.github/workflows/timing-alu-state-refinement.yml', LOCK)
PINS = {**part.PINS,
    'scripts/prove_alu_state_partitions.py': 'c548c9c436a074ff13e978d14dbf6dd9edfa6f107854ea1eaab9dd8766cea7b8',
    'sw/tests/test_alu_state_partitions.py': '9625cef3b41047ab1fb2be2ab46fff8887de70962a619707c6a27715b3602cc4',
    '.github/workflows/timing-alu-state-partitions.yml': '5bf83968bb5cca722a30d20a5c20b46a28221b6a180620a135d0f8a52ad03542'}


def load_lock():
    row = json.loads((ROOT/LOCK).read_text())
    state.require(row['schema'] == 1 and row['source_run'] == 37019936771
        and row['source_commit'] == '1c557fb442f546ed56a059d30a6b0ca9e6a2ddeb' and row['source_conclusion'] == 'failure'
        and row['proved_groups'] == 250 and row['counterexamples'] == 0 and row['original_groups'] == 269
        and row['original_input_bits'] == 10828 and row['original_output_bits'] == 34321
        and row['refinement_width'] == 16 and len(set(row['timed_out_groups'])) == 19
        and set(row['artifacts']) == {'common','verdict','shard0','shard1','shard2','shard3'}, 'Unreviewed refinement input')
    return row


def prior_verdict(plan, rows, expected_timeouts=None):
    result = part.aggregate(plan, rows)
    groups = [g for row in rows for g in row['groups']]
    state.require(all(g['verdict'] in {'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS', 'TIMEOUT_UNPROVED'}
                      and g['native_returncode'] == 0 for g in groups),
                  'Original counterexample/tool failure cannot be hidden by refinement')
    timeouts = sorted(g['id'] for g in groups if g['verdict'] == 'TIMEOUT_UNPROVED')
    state.require(timeouts and len(timeouts) < len(groups), 'Expected both preserved PASS and unproved groups')
    if expected_timeouts is not None: state.require(timeouts == expected_timeouts, 'Changed original timeout set')
    return result, timeouts


def refinement_plan(plan, timeouts, width=16):
    part.validate_plan(plan)
    parents = {g['id']: g for g in plan['groups'] if g['id'] in timeouts}
    state.require(len(parents) == len(set(timeouts)) == len(timeouts), 'Unknown or duplicate timeout parent')
    state.require(type(width) is int and width > 0, 'Invalid refinement width')
    obligations = [[name, bit] for name in sorted(parents) for bit in range(len(parents[name]['obligations']))]
    refined = dict(schema=1, symbolic_inputs=dict(plan['symbolic_inputs']),
        output_widths={name:len(g['obligations']) for name,g in parents.items()},
        symbolic_input_bits=plan['symbolic_input_bits'], total_output_bits=len(obligations), chunk_width=width, shards=4,
        groups=[dict(id=f'{part.PREFIX}{i//width:04d}', obligations=obligations[i:i+width], shard=(i//width)%4)
                for i in range(0,len(obligations),width)])
    validate_refinement(plan, refined, timeouts)
    return refined


def validate_refinement(original, refined, timeouts):
    part.validate_plan(original); part.validate_plan(refined)
    parents = {g['id']: g for g in original['groups']}
    state.require(refined['symbolic_inputs'] == original['symbolic_inputs'], 'Refinement changed symbolic inputs')
    state.require(refined['output_widths'] == {n:len(parents[n]['obligations']) for n in timeouts},
                  'Refinement omits or adds original output observations')
    mapped = [tuple(parents[name]['obligations'][bit]) for g in refined['groups'] for name,bit in g['obligations']]
    expected = [tuple(pair) for name in sorted(timeouts) for pair in parents[name]['obligations']]
    state.require(mapped == expected and len(mapped) == len(set(mapped)), 'Refinement duplicates or skips an original bit')
    return mapped


def wrapper(plan, refined, timeouts):
    validate_refinement(plan, refined, timeouts)
    all_names = list(plan['symbolic_inputs']) + list(timeouts) + [g['id'] for g in refined['groups']]
    state.require(all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', n) for n in all_names), 'Unsafe wrapper signal name')
    # Separate loop keeps each original ordered observation bit explicit.
    declarations = [f'input wire [{w-1}:0] in_{n}' for n,w in plan['symbolic_inputs'].items()]
    for g in refined['groups']:
        declarations.append(f'output wire cmp_{g["id"]}')
        declarations.extend(f'output wire [{len(g["obligations"])-1}:0] {p}_{g["id"]}' for p in ('gold','gate'))
    lines = ['module miter('+',\n'.join(declarations)+');']
    parents = {g['id']:g for g in plan['groups']}
    for name in sorted(timeouts):
        for p in ('gold','gate'): lines.append(f'wire [{len(parents[name]["obligations"])-1}:0] observed_{p}_{name};')
    connections = [f'.in_{n}(in_{n})' for n in plan['symbolic_inputs']]
    for name in sorted(timeouts):
        connections.extend(f'.{p}_{name}(observed_{p}_{name})' for p in ('gold','gate'))
    lines.append('nssoc_preserved_miter preserved('+',\n'.join(connections)+');')
    for group in refined['groups']:
        name = group['id']
        for p in ('gold','gate'):
            bits = [f'observed_{p}_{parent}[{bit}]' for parent,bit in reversed(group['obligations'])]
            lines.append(f'assign {p}_{name} = '+'{'+', '.join(bits)+'};')
        lines.append(f'assign cmp_{name} = gold_{name} == gate_{name};')
    return '\n'.join(lines+['endmodule',''])


def build_script(original, observed, output, interface):
    return f'''read_rtlil {state.quoted(original)}
rename miter nssoc_preserved_miter
read_verilog {state.quoted(observed)}
prep -top miter -flatten
opt -full
check -assert
select -assert-none t:nssoc_preserved_miter
stat
write_rtlil {state.quoted(output)}
write_json {state.quoted(interface)}
'''


def combined_verdict(original, old_rows, refined, new_rows, timeouts):
    prior, actual_timeouts = prior_verdict(original, old_rows, timeouts)
    closed_bits = validate_refinement(original, refined, actual_timeouts)
    current = part.aggregate(refined, new_rows)
    parents = {g['id']:g for g in original['groups']}
    proven = [tuple(bit) for row in old_rows for group in row['groups']
              if group['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' for bit in parents[group['id']]['obligations']]
    all_bits = {tuple(bit) for group in original['groups'] for bit in group['obligations']}
    state.require(len(proven)+len(closed_bits) == len(all_bits) and set(proven).isdisjoint(closed_bits)
                  and set(proven)|set(closed_bits) == all_bits, 'Combined proof does not cover every original output bit exactly once')
    passed = current['state_bijection_proved']
    return dict(status='PROVED_COMPLETE_REFINED_BINARY_RELATION' if passed else 'REFINEMENT_INCOMPLETE_OR_COUNTEREXAMPLE',
        state_bijection_proved=passed, original_groups=len(original['groups']), preserved_proved_groups=prior['proved_groups'],
        refined_parent_groups=len(timeouts), refined_groups=current['complete_groups'], refined_proved_groups=current['proved_groups'],
        symbolic_input_bits=original['symbolic_input_bits'], complete_original_output_bits=len(all_bits),
        no_internal_assumptions=True, prior_timeouts_preserved=True, original_counterexample_preserved=True,
        candidate_adopted=False, full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False,
        unresolved_four_state_boot_failure=True)


def native_controls(runtime, library, directory):
    left,_ = state.lift(state.fixture(), ['ff0','ff1'])
    wrong = copy.deepcopy(left); wrong['ports'][state.PREFIX+'ff_clk']['bits'][0] = '0'
    wrong_output = copy.deepcopy(left); wrong_output['ports']['output_q']['bits'][0] = '0'
    result = {}
    for name,right in [('equal',left),('wrong_clock',wrong),('wrong_output',wrong_output)]:
        out = directory/name; out.mkdir()
        original_plan = part.make_plan(left,right,2)
        timeouts = [g['id'] for g in original_plan['groups'][:-1]]
        refined = refinement_plan(original_plan,timeouts,1)
        for tag,module in [('left',left),('right',right)]:
            state.common.save(out/(tag+'.json'), dict(modules=dict(soc_top=part.alias_outputs(module,original_plan))))
        script = out/'original.ys'
        script.write_text(part.build_script(out/'left.json',out/'right.json',library,out/'original.il',out/'original.json'))
        state.require(state.execute(runtime,script,out,'original',60)['returncode'] == 0, 'Tiny original miter failed')
        observed = out/'observations.v'; observed.write_text(wrapper(original_plan,refined,timeouts))
        script = out/'refinement.ys'; script.write_text(build_script(out/'original.il',observed,out/'refined.il',out/'interface.json'))
        state.require(state.execute(runtime,script,out,'refinement',60)['returncode'] == 0, 'Tiny refinement build failed')
        part.validate_interface(json.loads((out/'interface.json').read_text())['modules']['miter'],refined)
        rows=[]
        for shard in range(4):
            script=out/(str(shard)+'.tcl');script.write_text(part.shard_script(out/'refined.il',refined,shard,out,10))
            state.require(part.execute_tcl(runtime,script,out,'shard'+str(shard))['returncode']==0,'Tiny refined traversal failed')
            rows.append(dict(shard=shard,groups=part.parse_shard((out/('shard'+str(shard)+'.log')).read_text(),refined,shard,out)))
        verdict=part.aggregate(refined,rows)
        state.require(verdict['state_bijection_proved'] == (name=='equal'),'Wrong native refined verdict')
        state.common.save(out/'plan.json',refined);state.common.save(out/'groups.json',rows);result[name]=verdict
        if name == 'equal':
            for fault in ('omitted', 'duplicate'):
                bad = copy.deepcopy(rows)
                if fault == 'omitted': bad[0]['groups'].pop()
                else: bad[0]['groups'].append(copy.deepcopy(bad[0]['groups'][0]))
                try: part.aggregate(refined, bad)
                except ValueError: verdict[fault+'_native_receipt_rejected'] = True
                else: raise ValueError('Incomplete native refined receipt was accepted')
    return result


def snapshot_methods(output):
    methods = {}
    for name in (*PINS, *OWN):
        if name in PINS: state.require(state.common.sha(ROOT/name) == PINS[name], 'Frozen source changed')
        dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes()); methods[name] = state.archived.pin(dest)
    return methods


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', 'repos/Melihakbulut221/nssoc/'+path], text=True))


def fetch_originals(lock, output, work):
    run = api('actions/runs/'+str(lock['source_run']))
    state.require(run['head_sha'] == lock['source_commit'] and run['event'] == 'push'
        and run['status'] == 'completed' and run['conclusion'] == lock['source_conclusion']
        and run['run_attempt'] == 1, 'Original partition producer identity changed')
    downloaded = {}
    for name, entry in lock['artifacts'].items():
        meta = api('actions/artifacts/'+str(entry['id']))
        state.require(meta['id'] == entry['id'] and meta['name'] == entry['name'] and not meta['expired']
            and meta['size_in_bytes'] == entry['bytes'] and meta['digest'] == 'sha256:'+entry['sha256']
            and meta['workflow_run']['id'] == lock['source_run']
            and meta['workflow_run']['head_sha'] == lock['source_commit'], 'Original artifact identity changed')
        archive = work/(name+'.zip')
        with archive.open('xb') as dest:
            subprocess.run(['gh', 'api', 'repos/Melihakbulut221/nssoc/actions/artifacts/'+str(entry['id'])+'/zip'],
                           stdout=dest, check=True)
        state.common.verify_file(archive, entry)
        restore(archive, output/name)
        downloaded[name] = dict(artifact=entry, verified_original_zip=state.archived.pin(archive))
    return downloaded


def restore(archive, destination):
    destination.mkdir()
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        state.require(len(entries) == len({i.filename for i in entries}) and len(entries) < 2000
                      and sum(i.file_size for i in entries) < 2*1024**3, 'Unexpected original archive inventory')
        for info in entries:
            name = state.common.safe_relative(info.filename.rstrip('/'))
            mode = info.external_attr >> 16
            state.require(not stat.S_ISLNK(mode) and not (mode and stat.S_IFMT(mode)
                and not (stat.S_ISDIR(mode) or stat.S_ISREG(mode))), 'Non-regular original archive member')
            target = destination/name
            if info.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open('xb') as dst: shutil.copyfileobj(src, dst, 1024**2)
            state.require(target.stat().st_size == info.file_size, 'Truncated original archive member')


def manifest():
    return state.common.validate_manifest(json.loads((ROOT/state.archived.MANIFEST).read_text()))


def verify_prior(bundle, lock):
    common = bundle/'common'
    state.common.verify_file(common/'result.json', lock['common_result'])
    row = json.loads((common/'result.json').read_text())
    state.require(row['github_source_commit'] == lock['source_commit']
        and row['status'] == 'COMMON_MITER_PREPARED_NOT_PROVED' and row['complete_inputs_rechecked'] is True
        and row['runtime'] == manifest()['runtime'] and set(row['methods']) == set(PINS), 'Unbound original common miter')
    part.verify_inventory(common, row['outputs'])
    for name, expected in row['methods'].items():
        state.require(expected['sha256'] == PINS[name], 'Original method differs from reviewed producer')
        state.common.verify_file(common/'methods'/name, expected)
        state.common.verify_file(ROOT/name, expected)
    for name, key in [('plan.json','plan'), ('common-miter.il','common_miter')]:
        state.require(row[key] == lock[key], 'Original common input record differs')
        state.common.verify_file(common/name, lock[key])
    plan = part.validate_plan(json.loads((common/'plan.json').read_text()))
    state.require((plan['symbolic_input_bits'], plan['total_output_bits'], len(plan['groups'])) ==
        (lock['original_input_bits'],lock['original_output_bits'],lock['original_groups']), 'Original boundary census differs')
    rows = []
    for shard in range(4):
        directory = bundle/('shard'+str(shard))
        state.common.verify_file(directory/'result.json', lock['shard_results'][str(shard)])
        found = json.loads((directory/'result.json').read_text())
        state.require(found['shard'] == shard and found['status'] == 'ALL_ASSIGNED_GROUPS_VISITED'
            and found['complete_inputs_rechecked'] is True and found['execution']['returncode'] == 0
            and found['github_source_commit'] == lock['source_commit'] and found['methods'] == row['methods']
            and found['common_miter'] == lock['common_miter'] and found['plan'] == lock['plan'], 'Original shard identity differs')
        part.verify_inventory(directory, found['outputs'])
        parsed = part.parse_shard((directory/'partitions.log').read_text(), plan, shard, directory, write_logs=False)
        state.require(parsed == found['groups'], 'Original raw native verdict differs')
        rows.append(found)
    verdict, _ = prior_verdict(plan, rows, lock['timed_out_groups'])
    captured = bundle/'verdict'/'alu-partition-verdict.json'
    state.common.verify_file(captured, lock['aggregate_result'])
    old = json.loads(captured.read_text())
    state.require(all(old[k] == v for k,v in verdict.items()) and old['github_source_commit'] == lock['source_commit']
        and old['common_miter'] == lock['common_miter'] and old['plan'] == lock['plan']
        and old['shard_results'] == lock['shard_results'] and verdict['proved_groups'] == lock['proved_groups'],
        'Original aggregate cannot be reproduced')
    return row, plan, rows


def inventory(output):
    return {str(p.relative_to(output)): state.archived.pin(p) for p in sorted(output.rglob('*'))
            if p.is_file() and p != output/'result.json'}


def prepare(output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full refinement build is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_REFINEMENT', github_source_commit=os.environ.get('GITHUB_SHA'),
               state_bijection_proved=False, candidate_adopted=False, unresolved_four_state_boot_failure=True)
    try:
        row['methods'] = snapshot_methods(output); state.common.save(output/'result.json', row)
        lock = load_lock(); prior = output/'prior'; prior.mkdir()
        row['original_archives'] = fetch_originals(lock, prior, work)
        old, plan, old_rows = verify_prior(prior, lock)
        refined = refinement_plan(plan, lock['timed_out_groups'], lock['refinement_width'])
        state.require(len(refined['groups']) == 152 and refined['total_output_bits'] == 2432, 'Unexpected refinement census')
        state.common.save(output/'plan.json', refined)
        row['preserved_original_verdict'] = part.aggregate(plan, old_rows)
        runtime = work/'runtime.AppImage'; state.common.download(old['runtime'], runtime); runtime.chmod(0o755)
        library_lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        library_bundle = work/'library'; state.archived.restore(ROOT/library_lock['archive']['path'], library_bundle, library_lock)
        library = library_bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        tiny = output/'controls'; tiny.mkdir(); row['controls'] = native_controls(runtime, library, tiny)
        observed = output/'observations.v'; observed.write_text(wrapper(plan, refined, lock['timed_out_groups']))
        script = output/'build.ys'; common = output/'common-miter.il'; interface = work/'interface.json'
        script.write_text(build_script(prior/'common'/'common-miter.il', observed, common, interface))
        execution = state.execute(runtime, script, output, 'build', 900)
        state.require(execution['returncode'] == 0, 'Native refinement wrapper failed')
        row['native_interface'] = part.validate_interface(json.loads(interface.read_text())['modules']['miter'], refined)
        verify_prior(prior, lock)
        for name, pin in row['methods'].items(): state.common.verify_file(output/'methods'/name, pin)
        for name, pin in library_lock['files'].items(): state.common.verify_file(library_bundle/name, pin)
        state.common.verify_file(runtime, old['runtime'])
        row.update(status='REFINED_MITER_PREPARED_NOT_PROVED', common_miter=state.archived.pin(common),
            plan=state.archived.pin(output/'plan.json'), native_build=execution, runtime=old['runtime'],
            original_lock=state.archived.pin(ROOT/LOCK), original_common_miter=lock['common_miter'],
            complete_inputs_rechecked=True)
    except BaseException as exc:
        row.update(status='REFINEMENT_PREPARATION_FAILED', error=repr(exc)); raise
    finally:
        row['outputs'] = inventory(output); state.common.save(output/'result.json', row)
    return row


def verify_common(bundle):
    row = json.loads((bundle/'result.json').read_text())
    state.require(row['status'] == 'REFINED_MITER_PREPARED_NOT_PROVED' and row['complete_inputs_rechecked'] is True
        and row['github_source_commit'] == os.environ.get('GITHUB_SHA') and row['runtime'] == manifest()['runtime']
        and set(row['methods']) == set(PINS)|set(OWN), 'Incomplete or changed refined preparation')
    part.verify_inventory(bundle, row['outputs'])
    for name, expected in row['methods'].items():
        state.common.verify_file(ROOT/name, expected); state.common.verify_file(bundle/'methods'/name, expected)
        if name in PINS: state.require(expected['sha256'] == PINS[name], 'Frozen producer changed')
    lock = load_lock(); state.common.verify_file(ROOT/LOCK, row['original_lock'])
    state.require(row['original_common_miter'] == lock['common_miter'], 'Changed original common graph')
    _, original, old_rows = verify_prior(bundle/'prior', lock)
    state.common.verify_file(bundle/'common-miter.il', row['common_miter'])
    state.common.verify_file(bundle/'plan.json', row['plan'])
    plan = part.validate_plan(json.loads((bundle/'plan.json').read_text()))
    state.require(plan == refinement_plan(original, lock['timed_out_groups'], lock['refinement_width']), 'Refinement plan changed')
    state.require((bundle/'observations.v').read_text() == wrapper(original, plan, lock['timed_out_groups']), 'Wrapper observations changed')
    return row, plan, original, old_rows, lock


def run_shard(bundle, shard, output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full refinement proof is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_REFINED_SHARD', shard=shard, github_source_commit=os.environ.get('GITHUB_SHA'))
    try:
        prepared, plan, _, _, _ = verify_common(bundle)
        row.update(common_miter=prepared['common_miter'], plan=prepared['plan'], methods=prepared['methods'],
                   original_common_miter=prepared['original_common_miter'], original_lock=prepared['original_lock'])
        runtime = work/'runtime.AppImage'; state.common.download(prepared['runtime'], runtime); runtime.chmod(0o755)
        script = output/'partitions.tcl'; script.write_text(part.shard_script(bundle/'common-miter.il', plan, shard, output))
        execution = part.execute_tcl(runtime, script, output, 'partitions')
        state.require(execution['returncode'] == 0, 'Native refined traversal incomplete')
        groups = part.parse_shard((output/'partitions.log').read_text(), plan, shard, output)
        state.common.verify_file(bundle/'common-miter.il', prepared['common_miter'])
        state.common.verify_file(runtime, prepared['runtime'])
        verified_after, _, _, _, _ = verify_common(bundle)
        state.require(verified_after == prepared, 'Prepared evidence changed during native refinement')
        row.update(status='ALL_REFINED_GROUPS_VISITED', groups=groups, execution=execution,
            complete_inputs_rechecked=True, all_assigned_groups_proved=all(
                g['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' for g in groups))
    except BaseException as exc:
        row.update(status='REFINED_SHARD_FAILED_OR_INCOMPLETE', error=repr(exc)); raise
    finally:
        row['outputs'] = inventory(output); state.common.save(output/'result.json', row)
    return row


def aggregate_directories(bundle, directories, output):
    prepared, plan, original, old_rows, lock = verify_common(bundle)
    rows = []
    for directory in directories:
        row = json.loads((directory/'result.json').read_text())
        state.require(row['status'] == 'ALL_REFINED_GROUPS_VISITED' and row['complete_inputs_rechecked'] is True
            and row['execution']['returncode'] == 0 and all(row[k] == prepared[k] for k in
                ('github_source_commit','common_miter','plan','methods','original_common_miter','original_lock')),
            'Unmatched or incomplete refined shard')
        part.verify_inventory(directory, row['outputs'])
        parsed = part.parse_shard((directory/'partitions.log').read_text(), plan, row['shard'], directory, write_logs=False)
        state.require(parsed == row['groups'], 'Refined group verdict differs from raw native log')
        rows.append(row)
    result = combined_verdict(original, old_rows, plan, rows, lock['timed_out_groups'])
    result.update(github_source_commit=prepared['github_source_commit'], common_miter=prepared['common_miter'],
        plan=prepared['plan'], original_common_miter=lock['common_miter'], original_lock=prepared['original_lock'],
        prior_source_run=lock['source_run'], prior_source_commit=lock['source_commit'],
        preserved_proved_group_ids=sorted(g['id'] for r in old_rows for g in r['groups'] if g['verdict']=='PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'),
        refined_parent_group_ids=lock['timed_out_groups'],
        shard_results={str(r['shard']):state.archived.pin(d/'result.json') for r,d in zip(rows,directories)},
        scope='Every original binary storage-boundary equation, with equal initial corresponding state and identical opaque SRAM behavior. No reset reachability, four-state, CDC, memory-internal, boot or physical acceptance.')
    state.common.save(output, result)
    state.require(result['state_bijection_proved'], 'Refined original equations remain unproved or have counterexamples')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare','shard','aggregate'])
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--work', type=Path)
    parser.add_argument('--bundle', type=Path); parser.add_argument('--shard', type=int)
    parser.add_argument('--shard-dir', type=Path, action='append'); args = parser.parse_args()
    if args.phase == 'prepare': row = prepare(args.output.resolve(), args.work.resolve())
    elif args.phase == 'shard': row = run_shard(args.bundle.resolve(), args.shard, args.output.resolve(), args.work.resolve())
    else: row = aggregate_directories(args.bundle.resolve(), args.shard_dir, args.output.resolve())
    print(row['status'])


if __name__ == '__main__': main()
