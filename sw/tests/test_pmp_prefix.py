# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound transformation and actual HDL unsigned-comparison controls."""
import hashlib
from pathlib import Path
import random
import subprocess
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import prepare_pmp_prefix as pmp  # noqa: E402


def fixture():
    return b'''module ibex_pmp;
parameter PMPGranularity = 0;
assign region_match_gt[(c * PMPNumRegions) + r] = left > right;
assign region_match_lt[(c * PMPNumRegions) + r] = left < upper;
\tgenvar _gv_r_1;
// Permission and region-priority logic must remain byte-identical.
endmodule
'''


def test_exact_two_comparisons_reversible_without_permission_changes(monkeypatch):
    raw=fixture();monkeypatch.setattr(pmp,'SOURCE_SHA',hashlib.sha256(raw).hexdigest())
    changed,edits=pmp.transform(raw)
    assert b'nssoc_pmp_gt(left, right)' in changed
    assert b'nssoc_pmp_gt(upper, left)' in changed
    restored=changed.replace(pmp.FUNCTION.encode(),b'')
    for edit in reversed(edits): restored=restored.replace(edit['after'].encode(),edit['before'].encode(),1)
    assert restored==raw


@pytest.mark.parametrize('fault',['hash','duplicate','missing','wrong_operator','anchor'])
def test_changed_or_ambiguous_source_rejected(monkeypatch,fault):
    raw=fixture()
    if fault=='duplicate':raw=raw.replace(b'left > right;',b'left > right;\nassign region_match_gt[(c * PMPNumRegions) + r] = left > right;')
    if fault=='missing':raw=raw.replace(b'region_match_lt',b'region_match_bad')
    if fault=='wrong_operator':raw=raw.replace(b'left > right',b'left >= right')
    if fault=='anchor':raw=raw.replace(pmp.ANCHOR.encode(),b'')
    monkeypatch.setattr(pmp,'SOURCE_SHA',hashlib.sha256(raw).hexdigest())
    if fault=='hash':raw+=b'\n'
    with pytest.raises(ValueError):pmp.transform(raw)


@pytest.mark.parametrize('which',['original.v','candidate.v','negative.v','profile'])
def test_prepared_or_negative_inputs_cannot_change(tmp_path,monkeypatch,which):
    import json
    raw=fixture();monkeypatch.setattr(pmp,'SOURCE_SHA',hashlib.sha256(raw).hexdigest())
    source=tmp_path/'source.v';source.write_bytes(raw);out=tmp_path/'prepared';pmp.prepare(source,out)
    pmp.verify_prepared(out)
    if which=='profile':
        p=out/'preparation.json';r=json.loads(p.read_text());r['profile']['PMPNumChan']=2;p.write_text(json.dumps(r))
    else:(out/which).write_bytes((out/which).read_bytes()+b'\n')
    with pytest.raises(ValueError):pmp.verify_prepared(out)


@pytest.mark.parametrize('width',[1,2,4,5,16,31,32])
def test_actual_hdl_unsigned_prefix_against_relational_oracle(tmp_path,width):
    maximum=(1<<width)-1;rng=random.Random(2601002+width)
    pairs={(0,0),(0,maximum),(maximum,0),(maximum,maximum)}
    if width<=5:pairs.update((a,b) for a in range(1<<width) for b in range(1<<width))
    else:
        pairs.update((rng.getrandbits(width),rng.getrandbits(width)) for _ in range(256))
        for bit in range(width):
            value=1<<bit;pairs.update(((value,value-1),(value-1,value),(value,value)))
    statements='\n'.join(f"if (nssoc_pmp_gt({width}'d{a}, {width}'d{b}) !== 1'b{int(a>b)}) $fatal(1, \"bad unsigned comparison\");" for a,b in sorted(pairs))
    source=tmp_path/'control.v';source.write_text(f'module control; parameter PMPGranularity={32-width};\n'+pmp.FUNCTION+'\ninitial begin\n'+statements+'\n$display("PASS"); $finish; end endmodule\n')
    executable=tmp_path/'control.vvp'
    subprocess.run(['iverilog','-g2012','-s','control','-o',str(executable),str(source)],check=True,capture_output=True,text=True)
    result=subprocess.run(['vvp',str(executable)],check=True,capture_output=True,text=True)
    assert result.stdout.splitlines().count('PASS')==1


def test_proof_covers_current_three_channel_interface_without_internal_name_matching(tmp_path):
    script=pmp.proof_script(tmp_path,'candidate')
    assert script.count('PMPNumChan 3')==2 and script.count('PMPNumRegions 4')==2
    assert 'miter -equiv -flatten gold gate miter' in script
    assert 'sat -verify -prove trigger 0' in script
    assert '-set ' not in script.split('sat ')[1] and 'equiv_make' not in script
    with pytest.raises(ValueError):pmp.proof_script(tmp_path,'unknown')
