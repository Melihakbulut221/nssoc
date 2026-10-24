# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte/AST review only; never import the reviewed spool."""
import ast
import hashlib
import json
import lzma
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = Path(__file__).resolve().parent
F = B/'core-source-freeze02.json'


def pin(p):
    p=Path(p)
    with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


def j(p):return json.loads(p.read_text())


def save(p,record):
    with p.open('x')as f:json.dump(record,f,indent=2);f.write('\n')


assert pin(F)==dict(bytes=122911,sha256='30147bb41f6d4c43d6af75054d5ecd75409a90acdecb709ed654024adbbe536c')
freeze=j(F);inputs={}
for key in ('sources','inputs','preserved_old_sources','actual_fixture_files'):
    for row in freeze[key]:
        expected={k:row[k]for k in ('bytes','sha256')}
        assert pin(row['path'])==expected,row['path']
        inputs[row['path']]=expected
source=R/'scripts/durable_pcie_spool_v1.py'
tests=R/'sw/tests/test_pcie_durable_spool_v1.py'
old=(B/'core-before02/durable_pcie_spool_v1.py').read_text()
current=source.read_text()
before="        fresh_bytes(self.root / 'native-terminal.json', encoded(terminal))"
after="        terminal_bytes = encoded(terminal)\n        self.check(len(terminal_bytes))\n        fresh_bytes(self.root / 'native-terminal.json', terminal_bytes)"
assert old.count(before)==current.count(after)==1 and current.replace(after,before)==old
oldtests=(B/'core-before02/test_pcie_durable_spool_v1.py').read_text()
assert tests.read_text().startswith(oldtests)
assert [n.name for n in ast.parse(tests.read_text()[len(oldtests):]).body]==['test_actual_near_cap_terminal_inventory_rejected_before_write']
tree=ast.parse(current)
imports=[n.module if isinstance(n,ast.ImportFrom) else ','.join(x.name for x in n.names)
         for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
assert not any(x in ('socket','subprocess','requests','urllib')for x in imports)
cases={}
for suffix,count in [('02',24),('03',27),('04',28)]:
    p=B/f'local-controls{suffix}.xml';xml=ET.parse(p)
    rows=list(xml.iter('testcase'));assert len(rows)==count
    assert all(all(c.find(x)is None for x in ('failure','error','skipped'))for c in rows)
    cases[suffix]=[c.attrib for c in rows]

# Read latest real test files with an independent little-endian byte oracle.
T=Path('/dev/shm/nssoc-spool-local-controls04')
samples=[struct.pack('<dd',i/10,(-1)**i*1.25)for i in range(8)]
saved={}
for name in ['test_real_lossless_parts_and_t0','test_no_network_or_reclaim_aft0']:
    s=T/name/'ssd';ledger=j(s/'parts.json');assert ledger['status']=='LOCAL_CAPTURE_COMPLETE'
    assert ledger['public_verified']is False and ledger['no_decimation']is True
    raw=[];count=0
    for index,row in enumerate(ledger['parts']):
        assert row['index']==index and row['first_row']==count
        assert row['name']==f'spool-test-unique-part{index:05d}.bin.xz'
        d=s/'committed'/f'{index:05d}';assert j(d/'record.json')==row
        p=d/row['name'];assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
        data=lzma.decompress(p.read_bytes())
        assert len(data)==row['uncompressed_bytes']==row['rows']*16
        assert hashlib.sha256(data).hexdigest()==row['uncompressed_sha256']
        raw.append(data);count+=row['rows']
    assert [r['rows']for r in ledger['parts']]==[3,3,2]
    assert b''.join(raw)==b''.join(samples)
    assert ledger['rows']==ledger['committed_rows']==count==8
    assert ledger['payload_sha256']==hashlib.sha256(b''.join(samples)).hexdigest()
    assert (s/'trailer.bin').read_bytes()==b'8'
    assert ledger['stream_metadata']=={x:pin(s/x)for x in ('header.bin','trailer.bin')}
    assert j(T/name/'ram/parts.json')==ledger
    saved[name]=dict(parts=3,rows=8,exact_binary_payload=True,ledger=pin(s/'parts.json'))

boundaries=['data_write','record_write','data_fsync','rename','committed_dir_fsync',
            'ledger_write','ledger_replace','mirror_write']
for index,kind in enumerate(boundaries):
    s=T/f'test_actual_failed_commit_boun{index}'/'ssd';ledger=j(s/'parts.json')
    staging=sorted(p.name for p in (s/'staging').iterdir())
    committed=sorted(p.name for p in (s/'committed').iterdir())
    assert ledger['status']=='CAPTURING_LOCAL' and (s/'reservation.bin').is_file()
    if kind=='mirror_write':
        assert ledger['committed_rows']==3 and len(ledger['parts'])==1 and staging==[] and committed==['00000']
        assert (T/f'test_actual_failed_commit_boun{index}'/'ram/parts.json.pending').stat().st_size>0
    elif kind in ('committed_dir_fsync','ledger_write','ledger_replace'):
        assert ledger['committed_rows']==0 and ledger['parts']==[] and staging==[] and committed==['00000']
    else:
        assert ledger['committed_rows']==0 and ledger['parts']==[] and staging==['00000'] and committed==[]
    saved['commit_'+kind]=dict(canonical_rows=ledger['committed_rows'],staging=staging,committed=committed)

# Every deliberate corruption remains present; no producer rerun is required.
for index,kind in enumerate(['part','row','order','trailer','rawhash']):
    s=T/f'test_actual_corruption_rejecte{index}'/'ssd';ledger=j(s/'parts.json')
    row=ledger['parts'][0];d=s/'committed/00000'
    if kind=='part':assert pin(d/row['name'])!={k:row[k]for k in ('bytes','sha256')}
    elif kind=='row':assert j(d/'record.json')['first_row']==1!=row['first_row']
    elif kind=='order':assert row['index']==1
    elif kind=='trailer':assert (s/'trailer.bin').read_bytes()==b'7' and ledger['rows']==8
    else:assert ledger['payload_sha256']=='0'*64
    assert (s/'reservation.bin').exists() and len(list((s/'committed').glob('*/*.xz')))==3
    saved['corruption_'+kind]=dict(retained=True,canonical_file=pin(s/'parts.json'))
assert (T/'test_real_short_os_write_compl0/bytes').read_bytes()==b'1234567890abcdef'
assert (T/'test_zero_write_fails_with_pre0/bytes').read_bytes()==b'123'
s=T/'test_actual_near_cap_terminal_0'/'ssd'
assert s.exists(), sorted(p.name for p in T.iterdir()if 'near_cap' in p.name)
assert not(s/'native-terminal.json').exists() and (s/'reservation.bin').exists()
assert j(s/'parts.json')['committed_rows']==3
used=sum(p.stat().st_size for p in s.rglob('*')if p.is_file()and p.name!='reservation.bin')
assert used<20000
saved['corrected_terminal_cap']=dict(retained_reservation=True,terminal_record_absent=True,used=used,payload_cap=20000)
s=T/'test_terminal_native_raw_and_p0'/'ssd';term=j(s/'native-terminal.json')
assert len(term['native_capture'])==4 and not(s/'reservation.bin').exists()
for name,expected in term['native_capture'].items():
    assert pin(s/'native-terminal-capture'/name)==expected==pin(T/'test_terminal_native_raw_and_p0'/'native'/name)
assert (s/'native-terminal-capture/capture/unpublished-tail.bin').read_bytes()==samples[3]
assert (s/'native-terminal-capture/capture/unparsed-tail.bin').read_bytes()==b'partial-frame'
assert term['result']['status']=='ERROR_NATIVE_OR_STREAM_CAPTURE' and not term['public_verified']
saved['terminal_failure_tail']=dict(exact_files=4,unpublished_bytes=16,unparsed_bytes=13)
assert all(pin(p)==h for p,h in inputs.items())
record=dict(status='PASS_SOURCE_AND_SAVED_LOCAL_SPOOL_CORE',freeze=pin(F),findings=[],
            reviewer='RX independent whole-source and saved-data read-only peer',method=pin(Path(__file__)),
            inputs_rehashed=inputs,unique_pins=len(inputs),actual_fixture_files=len(freeze['actual_fixture_files']),
            cases=cases,saved_controls=saved,
            closed_source_finding=dict(original_freeze=pin(B/'core-source-freeze01.json'),
                issue='Terminal JSON result/inventory was not included in final disk cap precheck.',
                correction='Only serialize exact terminal bytes, check their size, then durable write; new actual near-cap refusal retains reservation and all original bytes.',
                exact_whole_source_inverse=True),
            source_checks=[
                'Full core and tests read. Exclusive new spool, advisory producer lock, actual posix_fallocate10GiB reservation;8GiB payload+metadata and1GiB free floor. Reservation is separate, not filesystem quota.',
                'Local part order: exclusive complete payload+record writes and fsync; staging-directory fsync; rename, destination/source parent fsync; canonical atomic ledger+parent fsync; RAM mirror then clear pending.',
                'Short writes loop; zero/failure retains prefix. Orphans never become canonical and completion refuses staged/orphan bytes; exact raw byte hash/row count and native trailer required.',
                'Terminal native capture files are rehashed before/after exact durable copy; terminal record only then reservation unlink. Caller must invoke after actual native wait/reap and retain pending/unparsed tails; this core alone cannot attest process completion.',
                'Local receipt never asserts public verification or solver resume. No network imports/operations or native launch. Asynchronous publisher and acquisition bridge are excluded and need separate gates.'
            ],
            scope='Source and saved local file/fault fixtures only. No producer/control/native/network rerun. Fault injections are observed file operations, not an empirical power-loss or filesystem hardware test. Partial writes retained as failures; no adoption of staging/orphans. Fresh native not authorized by this core peer alone.')
save(B/'core-source-peer-rx01.json',record)
print(json.dumps(dict(peer=pin(B/'core-source-peer-rx01.json'),unique_pins=len(inputs),fixtures=len(freeze['actual_fixture_files']),latest=len(cases['04'])),indent=2))
