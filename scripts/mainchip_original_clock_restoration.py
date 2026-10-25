#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact original-clock record plan. No archive retrieval, CAD, repair or acceptance."""
import ast, hashlib, json, re, stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / 'scripts/mainchip-original-clock-restoration-methods.json'
DIAG = 'docs/evidence/mainchip-clock-diagnostic-first-native-full-result-20261025.json'
DIAG_SHA = '484c9a2ee19ed97a4501741774290c63810a6a69e702e21f905eb60b4f49fa80'
GATE = 'scripts/check_mainchip_route12_all_clocks.py'
GATE_SHA = 'ed5669d48a87ce30d00fc3213792f7f57001651d4907d9367ca2b705f945c74b'
FIXED = 'scripts/run_cloud_fixed_wire_control.py'
FIXED_SHA = 'a99924bc58503263a749e2f207eee075f0ac58ecfd4b946ddd743c2b2bc40d6b'
DONOR_SHA = '2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a'
RECIPIENT_SHA = '9cdf9a6fb32d49894a5b23bd12ae4e6f400e1a945a9d2601e728f2d4ec7e0ae8'
DEF_SHA = {'before':'f8e4c86346c8876fa04ff02ccd8d8f060f018e6fab36fdca834b986d07a4748c',
           'after':'031e61ff169d27dbc8f83c0bf630cd43de44483ec9605bf6a4e1d38ccfbe37a7'}
SNAPSHOT_SHA = {'before':'eed34ac9967c50ed28b2f4c95eda006d68f3c65e4cc3b0478ab7399c75aa8f89',
                'after':'a6d9b37c33d1e7df0cbd0a00ff3a2de341fd0221159aac3321452aa32c827568'}
ROUTE = re.compile(rb'(?m)^([ \t]*\+ )(ROUTED|FIXED|COVER)(?= )')

def digest(b):
    return hashlib.sha256(b).hexdigest()

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def regular(path):
    path = Path(path)
    assert path.is_absolute()
    for p in [path, *path.parents]:
        assert not p.is_symlink(), ('symlink', str(p))
    s = path.stat()
    assert stat.S_ISREG(s.st_mode), ('not regular', str(path))
    return path

def file_sha(path):
    with regular(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def source_gate():
    m = json.loads(regular(METHOD).read_bytes())
    for p, expected in m['protected'].items():
        assert file_sha(ROOT/p) == expected, ('source hash', p)
    assert file_sha(ROOT/GATE) == GATE_SHA
    assert file_sha(ROOT/FIXED) == FIXED_SHA
    return m

def diagnosis(raw):
    assert digest(raw) == DIAG_SHA, 'actual diagnostic source hash'
    r = json.loads(raw)
    return diagnosis_fields(r)

def diagnosis_fields(r):
    assert (r['run_id'], r['run_attempt'], r['source_head']) == (
        40213042958, 1, 'ed3e96c368867f1c3ad0bbbae794d4e15344ba89')
    assert r['status'] == 'COMPLETE_DIAGNOSTIC_ORIGINAL_ALL_CLOCK_GATE_STILL_FAILED'
    assert r['native_returncode'] == 1 and r['original_clock_gate_passed'] is False
    assert r['accepted'] is False and r['inputs_unchanged'] is True
    d = r['diagnosis']
    assert d['before_nets'] == d['after_nets'] == 1691
    assert d['changed_nets'] == d['statements_changed'] == len(d['changes']) == 218
    assert d['attached_geometry_changed'] == d['connection_prefixes_changed'] == 0
    assert d['original_equality_passed'] is False
    assert d['snapshot_sha256'] == SNAPSHOT_SHA
    assert r['derivation']['original_sha256'] == GATE_SHA
    return r

def parse_def(raw):
    """Preserve every byte, including whitespace between records; reject unsupported syntax."""
    assert isinstance(raw, bytes) and b'\0' not in raw and b'\r' not in raw
    matches = list(re.finditer(rb'(?m)^NETS ([0-9]+) ;\n', raw))
    assert len(matches) == 1, 'exactly one NETS section'
    m = matches[0]
    ends = list(re.finditer(rb'(?m)^END NETS[ \t]*\n', raw))
    assert len(ends) == 1 and ends[0].start() >= m.end(), 'NETS end'
    end = ends[0].start()
    spans = {}; start = None; name = None; cursor = m.end()
    for line in raw[m.end():end].splitlines(keepends=True):
        hit = re.match(rb'^[ \t]*- ([^\s]+)(?=\s)', line)
        if hit:
            assert start is None, 'unterminated NETS record'
            start = cursor; name = hit.group(1).decode('ascii')
            assert name not in spans, 'duplicate NETS record'
        if start is None:
            assert not line.strip(), 'unowned NETS text'
        elif b';' in line:
            assert line.count(b';') == 1 and not line.split(b';',1)[1].strip(), 'record terminator'
            spans[name] = (start, cursor+len(line))
            start = None; name = None
        cursor += len(line)
    assert start is None and cursor == end and len(spans) == int(m.group(1)), 'NETS census'
    return {'raw':raw, 'spans':spans,
            'records':{n:raw[a:b] for n,(a,b) in spans.items()},
            'section':(m.start(), ends[0].end())}

def replace_records(raw, replacements):
    p = parse_def(raw)
    assert replacements and set(replacements) <= p['spans'].keys(), 'replacement owner'
    chunks = []; cursor = 0
    for n,(a,b) in p['spans'].items():
        chunks.extend([raw[cursor:a], replacements.get(n,raw[a:b])]); cursor=b
    chunks.append(raw[cursor:])
    out = b''.join(chunks)
    q = parse_def(out)
    assert list(q['records']) == list(p['records']), 'NETS order/name'
    for n,v in replacements.items():
        assert q['records'][n] == v and v.split()[1].decode('ascii') == n, 'replacement name'
    return out

def prefix(record):
    tokens = record.split()
    assert tokens[0] == b'-' and tokens[-1] == b';'
    return tokens[:tokens.index(b'+')] if b'+' in tokens else tokens[:-1]

def classes(record):
    hits = list(ROUTE.finditer(record))
    # Current admitted export has one wire clause, possibly many NEW paths.
    # Mixed/unsupported clauses are not silently interpreted.
    assert len(hits) == 1, 'exactly one supported encoded wire clause'
    return hits[0].group(2).decode('ascii')

def route_class(record, target):
    assert target in ('ROUTED','FIXED','COVER')
    classes(record)
    return ROUTE.sub(lambda m:m.group(1)+target.encode(), record)

def make_plan(before, after, snapshots, report):
    """Actual inputs only; synthetic planning is isolated in the checker."""
    for label, raw in [('before',before),('after',after)]:
        assert digest(raw) == DEF_SHA[label], ('actual DEF', label)
        assert digest(canonical(snapshots[label])) == SNAPSHOT_SHA[label], ('actual snapshot', label)
    return plan_records(before, after, snapshots, report['diagnosis']['changes'], 1691, 218)

def plan_records(before, after, snapshots, changes, clock_count, changed_count):
    """Structural seam; production enters only through the fixed-hash make_plan admission."""
    a,b = parse_def(before),parse_def(after)
    clocks = set(snapshots['before'])
    assert len(clocks) == clock_count and clocks == set(snapshots['after'])
    assert 'clknet_3_5_0_pcie_clk_i' in clocks and clocks <= a['records'].keys() & b['records'].keys()
    assert len(changes)==changed_count and set(changes)<=clocks
    for n in clocks:
        x,y = snapshots['before'][n],snapshots['after'][n]
        assert x['statement'] == a['records'][n].decode().split()
        assert y['statement'] == b['records'][n].decode().split()
        assert x['instances'] == y['instances'], ('attached instance',n)
        assert prefix(a['records'][n]) == prefix(b['records'][n]), ('connection prefix',n)
        if n in changes:
            assert changes[n]['before']==x and changes[n]['after']==y
            assert x!=y and classes(a['records'][n])==classes(b['records'][n])=='ROUTED'
        else:
            assert x==y, ('unreported clock difference',n)
    replacements={n:a['records'][n] for n in changes}
    expected=replace_records(after,replacements)
    return expected,dict(changed_names=sorted(changes), all_clock_names=sorted(clocks),
        changed_names_sha256=digest(canonical(sorted(changes))),
        all_clock_names_sha256=digest(canonical(sorted(clocks))),
        expected_def_sha256=digest(expected), original_classes={n:classes(a['records'][n]) for n in changes},
        recipient_def_sha256=digest(after), accepted=False)

def verify_exact(expected, actual):
    assert actual == expected, 'full native DEF differs from exact recipient-plus-donor-record plan'
    return {'full_def_byte_exact':True, 'sha256':digest(actual)}

def extract_qualified(name):
    """Use the qualified function bytes with no imported historical controller main."""
    raw=regular(ROOT/FIXED).read_bytes()
    assert digest(raw)==FIXED_SHA
    module=ast.parse(raw)
    nodes=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(nodes)==1 and name=='omit_patch_connections'
    ns={'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),FIXED,'exec'),ns)
    return ns[name]

def patch_def(reference, records):
    p=parse_def(reference)
    assert records and set(records)<=p['records'].keys()
    lines=[]
    for key in (b'VERSION',b'DIVIDERCHAR',b'BUSBITCHARS',b'DESIGN',b'UNITS DISTANCE MICRONS'):
        found=re.findall(rb'(?m)^'+key+rb' [^\n]+ ;$',reference)
        assert len(found)==1, ('DEF header',key)
        lines.extend(found)
    body=b''.join(records[n] for n in p['records'] if n in records).decode('ascii')
    # Exact qualified connection omission; callers first prove original prefix.
    body,removed=extract_qualified('omit_patch_connections')(body)
    assert removed>0
    result=b'\n'.join(lines)+b'\nNETS '+str(len(records)).encode()+b' ;\n'+body.encode()+b'END NETS\nEND DESIGN\n'
    q=parse_def(result)
    assert set(q['records'])==set(records)
    return result,removed

def fixed_overlay(restored, all_clock_names):
    p=parse_def(restored); changes={}; original={}
    assert len(all_clock_names)==len(set(all_clock_names))
    for n in all_clock_names:
        record=p['records'][n]
        # An unwired selected member is recorded, never treated as routed.
        if not ROUTE.search(record):
            assert not re.search(rb'\+\s+(ROUTED|FIXED|COVER)\b',record), 'unsupported wire syntax'
            original[n]=None
            continue
        original[n]=classes(record)
        changes[n]=route_class(record,'FIXED')
    assert changes
    expected=replace_records(restored,changes)
    return expected,original

def restore_classes(fixed, originals):
    p=parse_def(fixed);replacements={}
    for n,kind in originals.items():
        if kind is None:
            assert not ROUTE.search(p['records'][n]), ('new wire on unwired selected net',n)
        else:
            assert classes(p['records'][n])=='FIXED'
            replacements[n]=route_class(p['records'][n],kind)
    return replace_records(fixed,replacements)

def validate_encoded(records, expected):
    assert set(records)==set(expected), 'encoded net census'
    for n,kind in expected.items():
        r=records[n]
        assert set(r)=={'wire_present','metadata','paths'}, ('encoded schema',n)
        if kind is None:
            assert r['wire_present'] is False and r['paths']==[], ('unexpected wire',n)
        else:
            assert r['wire_present'] is True and r['paths'] and r['metadata']==kind
            assert all(x==kind for x in r['paths']), ('encoded path class',n)
    return True

def validate_metadata_transition(actual, baseline, target):
    """Independent native metadata intent; encoded route observations must not move."""
    assert set(actual)==set(baseline)==set(target), 'metadata transition census'
    for n,before in baseline.items():
        after=actual[n]
        assert set(after)==set(before)=={'wire_present','metadata','paths'}
        assert after['wire_present']==before['wire_present'] and after['paths']==before['paths'], ('metadata step changed encoded wire',n)
        assert after['metadata']==target[n], ('metadata setter not retained',n)
    return True
