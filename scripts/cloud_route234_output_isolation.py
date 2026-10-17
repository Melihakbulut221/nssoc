#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud feasibility of five native buffers for unavailable drive-strength cells."""
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch, sha
from branch_hold_targets import validate_child, CHILD_FILES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-route234-output-isolation'
ORIGINAL = ROOT / 'cloud-routed-extraction'
SUMMARY = '765b113220ba12b3267ee50cd1ff02bfac7eb89a336c41ba77632c7ccd401e6e'
PARTS = 'ed0fa830af18e5703c36e509ff3230ffe4522b106aaf764482709d5c9f2dc178'

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir()
    reports.OUT = OUT
    result = dict(status='RUNNING', accepted=False, source_head=os.environ['GITHUB_SHA'],
        source_run=38896397749, routed_candidate=False, timing_improvement_proven=False,
        scope='Alternative to nonexistent nand4_2/nand3_2/a22oi_2: insert exactly five actual buf_4 cells next to weak outputs. Hold all existing cells fixed, prove exact new topology and Liberty functional equivalence. No frozen-SPEF reuse, no timing/route acceptance. Rebase and fresh route/RC/all endpoints required after active nine-size candidate completes.')
    def save():
        (OUT / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    def run(args, label, env=None, expect=True):
        with (OUT / (label+'.log')).open('w') as log:
            proc = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, env=env)
        text = (OUT / (label+'.log')).read_text(errors='replace')
        print(label, proc.returncode, text[-2000:], flush=True)
        if expect:
            assert proc.returncode == 0 and not re.search(r'(?m)^\[ERROR|^Error:', text), (label, text[-4000:])
        return proc.returncode, text
    def tcl(text, label):
        path = OUT / (label+'.tcl')
        path.write_text(text)
        return run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', str(path)], label)
    def native(mode):
        return run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python',
            str(ROOT / 'scripts/prepare_route234_output_isolation.py')],
            mode, dict(os.environ, NSSOC_ISOLATION_MODE=mode))
    save()
    try:
        parent, proof = reports.restore_report('branch-hold-eco', 38896397749,
            SUMMARY, PARTS, OUT / 'parent', ('routed.odb','geometry-proof.json')+CHILD_FILES)
        validate_child(parent, OUT / 'parent')
        assert parent['native_drt_drvs'] == 0 and parent['logic']['status'] == 'PASS within scope'
        result['parent'] = proof
        fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38917800540-1-route234-sizing-screen/route234-sizing-screen-38917800540-1.summary.json',
            'd8b43beae0667c6eaa64f5cd80c9c8466eb20734bfc7d0aa6822e66d8513f751', OUT / 'screen.json')
        screen = json.loads((OUT / 'screen.json').read_text())
        assert screen['source_unchanged'] and screen['baseline_all_endpoint_rows_reproduced']
        assert screen['physical_source']['summary_sha256'] == SUMMARY
        assert [r['index'] for r in screen['preparation']['unavailable']] == [0,1,3,4,6]
        selected = {r['index'] for r in screen['preparation']['unavailable']}
        margins = [r for r in screen['remeasured_source_drivers'] if r['index'] in selected]
        assert len(margins) == 5 and all(v > 0 for r in margins for v in r['source234_hold_ns'].values())
        result['source_measured_margins'] = margins
        fetch(reports.BASE+'.summary.json', reports.SUMMARY_SHA, OUT / 'original-summary.json')
        old = json.loads((OUT / 'original-summary.json').read_text())
        packed = OUT / 'original.tar.gz'
        fetch(reports.BASE+'.tar.gz.part0000', reports.ARCHIVE_SHA, packed)
        assert packed.stat().st_size == 225682086 and not ORIGINAL.exists()
        with tarfile.open(packed) as archive:
            for member in archive:
                p = Path(member.name)
                assert not p.is_absolute() and '..' not in p.parts
                assert p.parts[0] == ORIGINAL.name and (member.isfile() or member.isdir())
                archive.extract(member, ROOT, filter='data')
        packed.unlink()
        assert sha(ORIGINAL / 'result.json') == reports.SUMMARY_SHA
        assert all(sha(ORIGINAL/n) == v for n,v in old['outputs'].items())
        assert all(sha(Path(n)) == v for n,v in old['protected_inputs'].items())
        native('prepare')
        tcl(f'read_db {{{OUT/"proposed.odb"}}}\nset_thread_count 2\ndetailed_placement -max_displacement {{50 50}}\ncheck_placement -verbose\nwrite_db {{{OUT/"legalized.odb"}}}\n', 'legalize-five')
        native('audit')
        result['physical_feasibility'] = json.loads((OUT / 'native-feasibility.json').read_text())
        tcl(f'read_db {{{OUT/"parent/routed.odb"}}}\nwrite_verilog {{{OUT/"before.v"}}}\n', 'before-netlist')
        tcl(f'read_db {{{OUT/"unrouted.odb"}}}\ncheck_placement -verbose\nwrite_verilog {{{OUT/"after.v"}}}\n', 'after-netlist')
        libs = [Path(n) for n in old['protected_inputs'] if n.endswith('_typ_1p20V_25C.lib')]
        standard = next(p for p in libs if 'stdcell' in str(p))
        cmd = [os.environ['CLOUD_APPIMAGE'],'python3',str(ROOT/'hw/soc/flow/check_eco_logic.py'),
               str(OUT/'before.v'),str(OUT/'after.v'),'--liberty',str(standard),'--output',str(OUT/'logic')]
        for lib in libs:
            if lib != standard:
                cmd += ['--macro-liberty',str(lib)]
        run(cmd, 'logic-proof')
        result['logic'] = json.loads((OUT / 'logic/result.json').read_text())
        assert result['logic']['status'] == 'PASS within scope'
        netlist = (OUT/'after.v').read_text()
        match = re.search(r'sg13g2_buf_4\s+nssoc_setup_isolation_buf_0\s*\((.*?)\);',netlist,re.S)
        assert match
        bad = netlist[:match.start()]+'sg13g2_inv_2 nssoc_setup_isolation_buf_0 ('+re.sub(r'\.X\s*\(','.Y(',match[1])+');'+netlist[match.end():]
        (OUT/'inverted.v').write_text(bad)
        negative = cmd.copy()
        negative[negative.index(str(OUT/'after.v'))] = str(OUT/'inverted.v')
        negative[negative.index(str(OUT/'logic'))] = str(OUT/'logic-negative')
        code, text = run(negative, 'negative-inversion', expect=False)
        assert code != 0 and 'Non-buffer instance added or removed' in text
        result['inversion_control'] = 'REJECTED'
        assert all(sha(OUT/'parent'/n) == v['sha256'] for n,v in proof['restore']['selected_files'].items())
        assert all(sha(Path(n)) == v for n,v in old['protected_inputs'].items())
        result.update(status='PASS_FIVE_BUFFER_PLACEMENT_AND_RESTRICTED_LOGIC_NOT_ROUTED_OR_TIMED',
                      source_unchanged=True)
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        result['outputs'] = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p != OUT/'result.json'}
        save()

if __name__ == '__main__':
    main()
