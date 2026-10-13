#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted isolated replay idle-clear candidate; no production RTL replacement."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-replay-idle'
REL = 'hw/soc/rtl/pcie/soc_pcie_replay_tx.v'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def candidate(text):
    anchors = {
        '            if(ack_valid_i && !ack_observed) begin':
            '            // Idle owns no transmitted byte; prepare the next byte index before credit grant.\n'
            '            if(!sending) read_pos<=0;\n'
            '            if(ack_valid_i && !ack_observed) begin',
        'send_slot<=replay_slot;read_pos<=0;': 'send_slot<=replay_slot;',
        'send_slot<=new_slot;read_pos<=0;': 'send_slot<=new_slot;',
    }
    for old, new in anchors.items():
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text

def wrapped(text, name, rename_state=False):
    # Wrappers mask only invalid-cycle payload/framing values. The real RTL
    # and its internal tx_eop feedback are not modified by the observation mask.
    declaration = 'module soc_pcie_replay_tx #('
    assert text.count(declaration) == 1
    core = text.replace(declaration, 'module ' + name + '_core #(')
    active_index = '    (* keep *) wire [BW-1:0] active_read_index = sending ? read_pos : {BW{1\'b0}};\n'
    anchor = '    reg capturing,sending,sending_replay,replay_active,replay_pending,replay_first,halt;'
    assert core.count(anchor) == 1
    core = core.replace(anchor, anchor + '\n' + active_index)
    if rename_state:
        core = re.sub(r'\bread_pos\b', 'idle_read_pos', core)
        for port in ('tx_data_o','tx_sop_o','tx_eop_o'):
            core = re.sub(r'\b' + port + r'\b', 'idle_' + port, core)
    start = text.index(declaration)
    end = text.index('\n);', start) + len('\n);')
    header = text[start:end].replace(declaration, 'module ' + name + ' #(')
    header = header.replace('output reg ', 'output wire ')
    ports = text[text.index(') (', start)+3:end-3]
    names = []
    for line in ports.splitlines():
        line = line.strip().rstrip(',')
        if not line:
            continue
        match = re.fullmatch(r'(?:input|output)\s+(?:wire|reg)\s*(?:\[[^]]+\]\s*)?(.+)', line)
        assert match, line
        names.extend(n.strip() for n in match[1].split(','))
    assert len(names) == len(set(names)) and {'tx_data_o','tx_sop_o','tx_eop_o','tx_valid_o'} <= set(names)
    masked = {'tx_data_o','tx_sop_o','tx_eop_o'}
    raw = 'raw_gate_' if rename_state else 'raw_gold_'
    connections = ','.join('.' + ('idle_' if rename_state and n in masked else '') + n + '(' + (raw if n in masked else '') + n + ')' for n in names)
    wrapper = header + '\nwire [7:0] ' + raw + 'tx_data_o;\nwire ' + raw + 'tx_sop_o,' + raw + 'tx_eop_o;\n'
    wrapper += name + '_core #(.DEPTH(DEPTH),.MAX_BYTES(MAX_BYTES),.TIMEOUT_CYCLES(TIMEOUT_CYCLES),.MAX_REPLAYS(MAX_REPLAYS)) design(' + connections + ');\n'
    wrapper += "assign tx_data_o=tx_valid_o ? " + raw + "tx_data_o : 8'b0;\n"
    wrapper += 'assign tx_sop_o=tx_valid_o && ' + raw + 'tx_sop_o;\nassign tx_eop_o=tx_valid_o && ' + raw + 'tx_eop_o;\nendmodule\n'
    return core + '\n' + wrapper

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False, production_rtl_modified=False,
                  scope='Isolated replay idle-clear RTL. Compare all handshake/control outputs at every clock, payload/SOP/EOP only while tx_valid. Preserve real internal feedback. Explicit clock/asynchronous-reset model, complete port scoreboards. No mapping, timing, route or PHY acceptance.')
    original = (ROOT / REL).read_text()
    source_hash = sha(ROOT / REL)
    result['source_sha256'] = source_hash
    def save():
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    def execute(command, label, cwd=None):
        with (OUT / (label + '.log')).open('w') as stream:
            code = subprocess.call([str(v) for v in command], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        return code, (OUT / (label + '.log')).read_text(errors='replace')
    try:
        altered = candidate(original)
        gold_dir, gate_dir, bad_dir = [OUT / n for n in ('baseline-rtl','candidate-rtl','negative-rtl')]
        for directory in (gold_dir,gate_dir,bad_dir):
            directory.mkdir()
            for file in (ROOT / 'hw/soc/rtl/pcie').glob('*.v'):
                shutil.copyfile(file, directory / file.name)
        (gate_dir / 'soc_pcie_replay_tx.v').write_text(altered)
        assert altered.count('if(!sending) read_pos<=0;') == 1
        wrong = altered.replace('if(!sending) read_pos<=0;', "if(!sending) read_pos<=1;")
        (bad_dir / 'soc_pcie_replay_tx.v').write_text(wrong)
        result['candidate_sha256'] = sha(gate_dir / 'soc_pcie_replay_tx.v')
        result['negative_sha256'] = sha(bad_dir / 'soc_pcie_replay_tx.v')
        yosys = shutil.which('yosys')
        iverilog = shutil.which('iverilog')
        assert yosys and iverilog
        result['runtime'] = dict(yosys=subprocess.check_output([yosys,'-V'],text=True).strip())
        result['proofs'] = []
        for label, text in [('positive',altered),('wrong_idle_index',wrong)]:
            directory = OUT / ('proof-' + label)
            directory.mkdir()
            (directory / 'gold.v').write_text(wrapped(original,'gold'))
            (directory / 'gate.v').write_text(wrapped(text,'gate',True))
            shutil.copyfile(gold_dir / 'soc_pcie_crc32_byte.v', directory / 'crc.v')
            recipe = '\n'.join([
                'read_verilog -sv crc.v gold.v gate.v', 'hierarchy -check',
                'proc', 'memory_map', 'opt', 'flatten gold gate', 'opt',
                'clk2fflogic', 'opt', 'equiv_make gold gate equiv',
                'hierarchy -top equiv', 'equiv_simple', 'equiv_induct -seq 4',
                'equiv_status -assert', ''])
            (directory / 'proof.ys').write_text(recipe)
            code, log = execute([yosys,'-s','proof.ys'],'proof-'+label,cwd=directory)
            counts = re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
            passed = code == 0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!' in log
            negative_rejected = code != 0 and bool(counts) and int(counts[-1][1])>0
            result['proofs'].append(dict(case=label,returncode=code,counts=counts,
                passed=passed,negative_rejected=negative_rejected,
                unproven_lines=[line for line in log.splitlines() if 'Unproven' in line or 'unproven' in line][-90:],
                log_sha256=sha(OUT / ('proof-'+label+'.log'))))
            save()
        result['ports'] = []
        # Always execute both actual baseline and candidate scoreboards, even
        # when an equivalence engine cannot prove the relational state invariant.
        for label, directory in [('baseline',gold_dir),('candidate',gate_dir),('wrong_idle_index',bad_dir)]:
            tops = ('soc_pcie_replay_tx',) if label=='wrong_idle_index' else ('soc_pcie_replay_tx','soc_pcie_reliable_packets')
            for top in tops:
                out = OUT / (label + '-' + top)
                command = [sys.executable,ROOT/'scripts/check_pcie_replay.py','--top',top,
                           '--out',out,'--rtl-dir',directory,'--iverilog-dir',Path(iverilog).parent]
                code, log = execute(command,label+'-'+top)
                record = json.loads((out/'result.json').read_text())
                result['ports'].append(dict(case=label,top=top,returncode=code,result=record))
                save()
                if label=='wrong_idle_index':
                    from cocotb_results import count_results
                    xml = out / 'results.xml'
                    assert xml.is_file()
                    passed, failed, skipped = count_results([xml])
                    result['ports'][-1]['observed_tests'] = dict(passed=passed,failed=failed,skipped=skipped)
                    result['ports'][-1]['observed_xml_sha256'] = sha(xml)
                    assert code != 0 and failed > 0 and skipped == 0
                    assert passed + failed == record['expected_tests']
                    assert 'AssertionError' in (out / 'simulation.log').read_text(errors='replace')
                else:
                    assert code == 0 and record['status']=='PASS_PORT_ONLY_PCIE_REPLAY'
                    assert record['tests']==dict(passed=record['expected_tests'],failed=0,skipped=0)
        assert sha(ROOT / REL)==source_hash
        assert result['proofs'][0]['passed'] and result['proofs'][1]['negative_rejected']
        result['status']='PASS_OBSERVABLE_REPLAY_EQUIVALENCE_AND_COMPLETE_PORT_CONTROLS_NOT_TIMING'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error))
        raise
    finally:
        save()

if __name__=='__main__':
    main()
