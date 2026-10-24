#!/usr/bin/env python3
"""Read-only V25 preliminary contract/source audit; never runs producers or HDL."""
from pathlib import Path
import ast
import hashlib
import json
import re

ROOT = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = ROOT / 'hw/soc/out/pcie-integrity-v25-20261006'
OUT = B / 'rx-contract-review01'


def pin(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def check(record):
    actual = pin(record['path'])
    assert actual['sha256'] == record['sha256'], record['path']
    if 'bytes' in record:
        assert actual['bytes'] == record['bytes'], record['path']
    return actual


def section(text, first, last):
    start = text.index(first)
    end = text.index(last, start) + len(last)
    return text[start:end]


def main():
    contract = json.loads((B / 'architecture-contract02.json').read_text())
    integration = json.loads((B / 'integration-audit02.json').read_text())
    bridge = json.loads((B / 'source-bridge-initial01.json').read_text())
    bindings = [check(row) for row in contract['inputs'] + integration['inputs']]
    check(integration['contract02'])
    baseline_pin = check(bridge['baseline'])
    candidate_pin = check(bridge['candidate'])
    old = Path(baseline_pin['path']).read_text()
    new = Path(candidate_pin['path']).read_text()
    forward = old
    assert len(bridge['edits']) == 14
    for change in bridge['edits']:
        assert forward.count(change['before']) == change['count']
        forward = forward.replace(change['before'], change['after'])
    assert forward == new
    backward = new
    for change in reversed(bridge['edits']):
        assert backward.count(change['after']) == change['count']
        backward = backward.replace(change['after'], change['before'])
    assert backward == old

    generator_path = ROOT / 'scripts/generate_pcie_integrity_command_v25.py'
    generator = generator_path.read_text()
    constants = {}
    for node in ast.parse(generator).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant):
                constants[node.targets[0].id] = node.value.value
    assert constants['BASE_SHA'] == baseline_pin['sha256']
    assert constants['OLD_WRITES'] in old and constants['OLD_WRITES'] not in new
    for name in ('DECLARATIONS', 'CAPTURE', 'APPLY'):
        assert constants[name] in new

    markers = [
        ('V17_STATIC_READ', ' // BEGIN V17 STATIC BALANCED KNOWN-ELIGIBILITY PAYLOAD TREE',
         ' // END V17 STATIC BALANCED KNOWN-ELIGIBILITY PAYLOAD TREE'),
        ('V21_AVAILABILITY', ' // BEGIN V21 REGISTERED RETIRE AVAILABILITY',
         ' // END V21 REGISTERED RETIRE AVAILABILITY'),
        ('CAPACITY_AND_PUBLIC_HANDSHAKES', ' wire [PW:0] space_after_retire=',
         ' assign overflow_o=overflow_sticky && rst_ni && !flush_i && !stream_start_i;'),
        ('PARSER_BODY', ' integer j;\n always @* begin',
         ' // BEGIN V6 SHARED OLD VERDICT READS'),
        ('V23_ACCEPTED_TAIL', ' // BEGIN V23 ACCEPTED STREAM PREDECESSOR',
         ' // END V23 ACCEPTED STREAM PREDECESSOR'),
        ('V10_BANKS', ' // BEGIN V10 QUARANTINED BANK WRITER',
         ' // END V10 QUARANTINED BANK WRITER'),
        ('V21_CAPTURE', ' // BEGIN V21 ATOMIC RETIRE PAYLOAD CAPTURE',
         ' // END V21 ATOMIC RETIRE PAYLOAD CAPTURE'),
        ('V21_OUTPUT', '       // BEGIN V21 DESCRIPTOR OWNERSHIP AND OUTPUT TRANSFER',
         '       // END V21 DESCRIPTOR OWNERSHIP AND OUTPUT TRANSFER'),
    ]
    unchanged = []
    for label, begin, end in markers:
        before = section(old, begin, end)
        after = section(new, begin, end)
        assert before == after, label
        unchanged.append(dict(name=label, bytes=len(after.encode()),
                              sha256=hashlib.sha256(after.encode()).hexdigest()))
    assert 'state_n=state;commit_n=commit_ptr;' in new
    assert 'wire [PW-1:0] occupied=write_ptr-read_ptr;' in new
    assert 'wire [PW-1:0] committed=visible_commit_ptr-read_ptr;' in new

    writers = {}
    for name in ('slot_data', 'slot_keep', 'slot_sop', 'slot_eop', 'slot_dllp',
                 'slot_sequence', 'slot_tag', 'slot_verdict', 'verdict'):
        # One source statement per array; loops elaborate the physical writers.
        rows = [line.strip() for line in new.splitlines()
                if re.search(r'(?<![A-Za-z0-9_])' + name + r'\[.*\]\s*<=', line)]
        assert len(rows) == 1, (name, rows)
        writers[name] = rows[0]
    for name in ('slot_data', 'slot_keep', 'slot_sop', 'slot_eop', 'slot_dllp',
                 'slot_sequence', 'slot_tag'):
        assert 'command_address+command_lane' in writers[name]
    assert 'command_verdict_tags' in writers['verdict']
    assert 'enabled && active_o && command_valid' in writers['slot_verdict']

    OUT.mkdir(exist_ok=False)
    captured = []
    for path in [B / 'architecture-contract02.json', B / 'integration-audit02.json',
                 B / 'source-bridge-initial01.json', generator_path,
                 Path(candidate_pin['path']), ROOT / 'sw/tests/test_pcie_gen3_integrity_v25_command.py']:
        payload = path.read_bytes()
        destination = OUT / (path.name + '.snapshot.txt')
        destination.write_bytes(payload)
        captured.append(dict(source=pin(path), snapshot=pin(destination)))
        assert path.read_bytes() == payload, f'Concurrent source change: {path}'
    receipt = dict(
        status='REVIEWED_V25_CONTRACT_AND_INITIAL_SOURCE_PENDING_COMPLETE_CONTROLS',
        source_approval_granted=False,
        contract=pin(B / 'architecture-contract02.json'),
        prior_contract_peer=pin(B / 'architecture-source-peer-vco01.json'),
        integration=pin(B / 'integration-audit02.json'),
        initial_bridge=pin(B / 'source-bridge-initial01.json'),
        baseline=baseline_pin, candidate=candidate_pin, checked_inputs=bindings,
        complete_forward_inverse_edits=14, unchanged_blocks=unchanged,
        array_writer_inventory=writers, captured_drafts=captured,
        known_state_review=[
            'All seven slot arrays, verdict writes and cache old/new-tag inputs use the same command fields; no original immediate slot writer remains.',
            'Parser commit_n defaults to original commit_ptr and occupancy reserves pending addresses; only retirement committed frontier is delayed.',
            'Main apply is inside original active/fault priority and outside step, so an old command applies during an ordinary bubble or ending drain.',
            'Visible frontier applies with slot/verdict writes; same-edge retirement observes the previous frontier through nonblocking semantics.',
            'Cache-only fault-edge writes remain deliberately unqualified; inaccessible state equality is not claimed, and fresh epoch overwrite must be tested.',
            'Original preedge public valid/ready permits a transfer on a prospective fault edge; candidate scoreboard must count it before epoch discard.',
            'No confirmed known-state architecture blocker found in this preliminary review; complete implementation and controls are not yet frozen.'
        ],
        unresolved_scope_question={
            'condition': 'active_o=1, command_valid=1, stream_abort_i=X, other external controls known inactive',
            'draft_semantics': 'enabled=X skips old-command APPLY while the else-active command-valid branch clears ownership; this is not an established external-control four-state relation.',
            'requested_resolution': 'Specify legal external-control domain separately from literal payload/tag/verdict four-state behavior, or test and define the intended external-control relation explicitly.',
            'classification': 'Open test/claim-domain question, not a demonstrated known-state product failure.'
        },
        required_full_freeze_review=[
            'Versioned independent public transaction scoreboard, preserving old cycle miter as historical evidence.',
            'Nominal ready=1 +1 first/last payload witnesses and sustained accepted-block/parser-beat throughput; no fixed cycle claim under arbitrary stalls/faults.',
            'Pending idle/ending application; zero-keep drain with held output; simultaneous apply/replace; adjacent-command old-verdict dependence.',
            'Actual same-tag conflicting verdict writes and reversed-priority mutant, with named intended diagnostic.',
            'Pending ownership witnesses for reset/start/flush/abort/parser fault/bad block/overflow, including actual fault-edge accepted keep bytes.',
            'Minimum supported ring, repeated extended-tag wrap, full-capacity stalls, old SOP reuse and no unread-data overwrite.',
            'Meaningful complete-product mutants for early frontier, stale epoch, step-only/final-apply suppression, replay, tag/data mispairing and bypass.',
            'Full frozen helper/oracle/launcher source and actual source-control saved results before any mapped or timing acceptance.'
        ],
        scope='Read-only source/JSON/hash review and exact text reconstruction only; no reviewed producer, compiler, simulator, mapper, EDA, test, or native process executed. Preliminary draft observations are not a source launch gate, functional equivalence proof, timing result, or adoption approval.',
        method=pin(__file__))
    (OUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(result=pin(OUT / 'result.json'),
                          checked_inputs=len(bindings), inverse_edits=14,
                          unchanged_blocks=len(unchanged), native_executed=False), indent=2))


if __name__ == '__main__':
    main()
