#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted all-input ACK-window algebra, exact physical replay and port controls."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-ack-window'
URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38472422176-1-ack-map-physical_idle_credit/ack-map-physical_idle_credit-38472422176-1.tar.gz'
ARCHIVE_SHA='ed43f52d14422ffb15c450350b5b697b61031ff50cee16d1e051a3e4374aa2be'
SOURCE_SHA='1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc'
EXPRESSION="""    // A bounded forward window spans at most one low-CW page boundary.
    // High-page comparisons run in parallel with the small low subtraction.
    // This preserves every CW-bit sent_count encoding and modulo4096 wrap.
    wire [CW:0] ack_low_difference={1'b0,ack_sequence_i[CW-1:0]}-
        {1'b0,acknowledged_sequence_o[CW-1:0]};
    (* keep = "true" *) wire [11-CW:0] ack_page_successor=
        acknowledged_sequence_o[11:CW]+1'b1;
    wire ack_same_page=ack_sequence_i[11:CW]==acknowledged_sequence_o[11:CW];
    wire ack_next_page=ack_sequence_i[11:CW]==ack_page_successor;
    wire current_ack_allowed=(ack_low_difference[CW] ? ack_next_page : ack_same_page) &&
        ack_low_difference[CW-1:0]<=sent_count;"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def candidate(text):
    old='    wire current_ack_allowed=ack_delta==0 || (ack_delta<=sent_count && ack_delta!=0);'
    assert text.count(old)==1
    text=text.replace(old,EXPRESSION)
    old='if(ack_delta!=0) begin'
    assert text.count(old)==1
    return text.replace(old,'if(ack_sequence_i!=acknowledged_sequence_o) begin')

def bad_candidate(text):
    old='wire ack_next_page=ack_sequence_i[11:CW]==ack_page_successor;'
    assert text.count(old)==1
    return text.replace(old,'wire ack_next_page=ack_sequence_i[11:CW]==acknowledged_sequence_o[11:CW];')

def algebra(cw,wrong=False):
    expr=bad_candidate(EXPRESSION) if wrong else EXPRESSION
    return ('module ack_window(input wire [11:0] ack_sequence_i,acknowledged_sequence_o,'
        f'input wire [{cw-1}:0] sent_count,output wire ok);\n'
        f'localparam integer CW={cw};\n'
        'wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;\n'+expr+
        '\nwire original_allowed=ack_delta==0 || (ack_delta<=sent_count && ack_delta!=0);\n'
        'assign ok=(current_ack_allowed==original_allowed) && '
        '((ack_delta!=0)==(ack_sequence_i!=acknowledged_sequence_o));\nendmodule\n')

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',adopted=False,production_rtl_modified=False,
        scope='Same-source physical replay idle/credit baseline, excluding timing-rejected EOP candidate. Full modulo4096 all-input ACK-window identity for CW2..5, all replay outputs including invalid payload, complete replay/reliable port scoreboards and actual wrong-page controls. Not mapped or routed timing.')
    def save():
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def execute(cmd,label,cwd=None):
        with (OUT/(label+'.log')).open('w') as stream:
            code=subprocess.call(list(map(str,cmd)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        return code,(OUT/(label+'.log')).read_text(errors='replace')
    try:
        packed=OUT/'source.tar.gz'
        subprocess.run(['curl','--fail','--location','--retry','4',URL,'-o',str(packed)],check=True)
        assert packed.stat().st_size==16843323 and sha(packed)==ARCHIVE_SHA
        prefix='cloud-ack-map/physical_idle_credit/'
        selected={};pins={}
        with tarfile.open(packed) as tar:
            source=json.load(tar.extractfile(prefix+'result.json'))
            assert source['status']=='COMPLETE_UNPLACED_SCREEN_NOT_TIMING_CLOSURE'
            for original,pin in source['physical_source_binding']['selected'].items():
                name=Path(original).name
                if not name.startswith('soc_pcie_') or not name.endswith('.v'):continue
                member=pin['path'].split('/nssoc/nssoc/',1)[1]
                raw=tar.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==pin['sha256'] and name not in selected
                selected[name]=raw;pins[name]=dict(member=member,sha256=pin['sha256'])
            for name,digest in [('soc_pcie_replay_tx.v',SOURCE_SHA),
                ('soc_pcie_credit_tx.v','7fc31891f0ae48a8df5247b6df72388ff12cf2603de9f9dc9654b30a0256d38a')]:
                member=prefix+'candidate-'+name;raw=tar.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==digest
                selected[name]=raw;pins[name]=dict(member=member,sha256=digest)
        packed.unlink()
        assert len(selected)==21
        assert pins['soc_pcie_buffered_flow_packets.v']['sha256']=='459d69ddaf287004099f91edf1d0c57d35fd324edf4fa9838cb994d398dd2509'
        name='soc_pcie_replay_tx.v'
        original=selected[name].decode();altered=candidate(original);wrong=bad_candidate(altered)
        dirs={}
        for case,text in [('baseline',original),('candidate',altered),('wrong_page',wrong)]:
            d=OUT/(case+'-rtl');d.mkdir()
            for filename,raw in selected.items():(d/filename).write_bytes(raw)
            (d/name).write_text(text);dirs[case]=d
        result['source_binding']=dict(archive_url=URL,archive_sha256=ARCHIVE_SHA,selected=pins,
            source_sha256=SOURCE_SHA,candidate_sha256=sha(dirs['candidate']/name),negative_sha256=sha(dirs['wrong_page']/name))
        yosys=shutil.which('yosys');iverilog=shutil.which('iverilog');assert yosys and iverilog
        result['runtime']=subprocess.check_output([yosys,'-V'],text=True).strip()
        result['algebra']=[]
        for cw in [2,3,4,5]:
            for bad in [False,True]:
                label='algebra-cw'+str(cw)+('-wrong' if bad else '')
                d=OUT/label;d.mkdir();(d/'miter.v').write_text(algebra(cw,bad))
                (d/'proof.ys').write_text('read_verilog -sv miter.v\nprep -top ack_window -flatten\n'
                    'sat -verify -prove ok 1 -show-inputs -show-outputs -dump_json counterexample.json\n')
                code,log=execute([yosys,'-s','proof.ys'],label,d)
                passed=code==0 and 'SAT proof finished - no model found: SUCCESS!' in log
                rejected=code!=0 and 'SAT proof finished - model found: FAIL!' in log and (d/'counterexample.json').is_file()
                result['algebra'].append(dict(cw=cw,negative=bad,returncode=code,passed=passed,negative_rejected=rejected,
                    log_sha256=sha(OUT/(label+'.log')),counterexample=json.loads((d/'counterexample.json').read_text()) if rejected else None));save()
                assert rejected if bad else passed
        result['proofs']=[]
        for case,text in [('candidate',altered),('wrong_page',wrong)]:
            d=OUT/('proof-'+case);d.mkdir()
            for module,source in [('gold',original),('gate',text)]:
                declaration='module soc_pcie_replay_tx #(';assert source.count(declaration)==1
                (d/(module+'.v')).write_text(source.replace(declaration,'module '+module+' #('))
            (d/'crc.v').write_bytes(selected['soc_pcie_crc32_byte.v'])
            (d/'proof.ys').write_text('\n'.join([
                'read_verilog -sv crc.v gold.v gate.v','hierarchy -check',
                'proc','memory_map','opt','flatten gold gate','opt','clk2fflogic','opt',
                'equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple',
                'equiv_induct -seq 4','equiv_status -assert','']))
            code,log=execute([yosys,'-s','proof.ys'],'proof-'+case,d)
            counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
            passed=code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!' in log
            rejected=code!=0 and bool(counts) and int(counts[-1][1])>0
            result['proofs'].append(dict(case=case,returncode=code,counts=counts,passed=passed,
                negative_rejected=rejected,log_sha256=sha(OUT/('proof-'+case+'.log'))));save()
        result['ports']=[]
        for case in ['baseline','candidate','wrong_page']:
            for top in (['soc_pcie_replay_tx'] if case=='wrong_page' else ['soc_pcie_replay_tx','soc_pcie_reliable_packets']):
                out=OUT/(case+'-'+top)
                code,log=execute([sys.executable,ROOT/'scripts/check_pcie_replay.py','--top',top,
                    '--out',out,'--rtl-dir',dirs[case],'--iverilog-dir',Path(iverilog).parent],case+'-'+top)
                record=json.loads((out/'result.json').read_text())
                from cocotb_results import count_results
                passed,failed,skipped=count_results([out/'results.xml'])
                result['ports'].append(dict(case=case,top=top,returncode=code,result=record,
                    actual_tests=dict(passed=passed,failed=failed,skipped=skipped)));save()
                assert skipped==0 and passed+failed==record['expected_tests']
                if case=='wrong_page':
                    assert code!=0 and failed>0 and 'AssertionError' in (out/'simulation.log').read_text(errors='replace')
                else:
                    assert code==0 and failed==0 and record['status']=='PASS_PORT_ONLY_PCIE_REPLAY'
        assert result['proofs'][0]['passed'] and result['proofs'][1]['negative_rejected']
        result['status']='PASS_ALL_INPUT_ACK_WINDOW_AND_PHYSICAL_REPLAY_CONTROLS_NOT_TIMING'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        save()

if __name__=='__main__':
    main()
