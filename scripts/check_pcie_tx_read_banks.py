#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cycle-exact TX bank proofs and non-vacuous arbitrary-memory corruption controls."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REFS={'replay': '6432a197a96005a12cfb9c223e695af25ab8dfa9febbb8e34fe1233953c2ad19', 'lcrc': '988f786b50819539284b36b6c620efba6e05feafd0d54c6cd10e7c5f558f8928'}

def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def extract(kind,text):
    if kind=='replay':
        for token in ['reg [7:0] bytes [0:DEPTH*MAX_BYTES-1];','reg [PW-1:0] head,tail,send_slot,replay_slot;','reg [BW-1:0] write_pos,read_pos;']:
            assert text.count(token)==1,('Unsupported replay state shape',token)
        begin=text.index('    assign tx_valid_o=');begin=text.index('\n',begin)+1
        end=text.index('    assign tx_sop_o=',begin)
    else:
        for token in ['reg [31:0] words [0:MAX_TLP_DWORDS-1];','reg [CW-1:0] count,length,index;','reg [1:0] byte_index;']:
            assert text.count(token)==1,('Unsupported LCRC state shape',token)
        begin=text.index('    always @* begin')
        if '    wire [7:0] selected_word_byte 'in text:begin=text.index('    wire [7:0] selected_word_byte ')
        end=text.index('    generate if (MAX_TLP_DWORDS<4',begin)
    return text[begin:end]

def cut_header(kind,parameters):
    if kind=='replay':
        depth=parameters['DEPTH'];cap=parameters['MAX_BYTES']
        return f"""module NAME(input [8*{depth*cap}-1:0] memory_bits,
 input [((({depth})<=2)?1:$clog2({depth}))-1:0] send_slot,
 input [$clog2({cap}+1)-1:0] read_pos,output [7:0] tx_data_o,output defined_read);
 localparam integer DEPTH={depth},MAX_BYTES={cap};
 wire [7:0] bytes [0:DEPTH*MAX_BYTES-1];
 genvar cut_n;generate for(cut_n=0;cut_n<DEPTH*MAX_BYTES;cut_n=cut_n+1)begin: cut_memory
 assign bytes[cut_n]=memory_bits[8*cut_n+:8];end endgenerate
 assign defined_read=send_slot*MAX_BYTES+read_pos<DEPTH*MAX_BYTES;
"""
    cap=parameters['MAX_TLP_DWORDS']
    return f"""module NAME(input [32*{cap}-1:0] memory_bits,
 input [$clog2({cap}+1)-1:0] index,input [2:0] header_words,state,
 input [1:0] byte_index,input [31:0] crc,input [11:0] next_sequence_o,
 output reg [7:0] tx_data_o,output defined_read);
 localparam integer MAX_TLP_DWORDS={cap};
 localparam [2:0] IDLE=0,COLLECT=1,DROP=2,PREFIX0=3,PREFIX1=4,DATA=5,CRC=6;
 wire [31:0] words [0:MAX_TLP_DWORDS-1];
 genvar cut_n;generate for(cut_n=0;cut_n<MAX_TLP_DWORDS;cut_n=cut_n+1)begin: cut_memory
 assign words[cut_n]=memory_bits[32*cut_n+:32];end endgenerate
 assign defined_read=state!=DATA || index<MAX_TLP_DWORDS;
"""

def run_yosys(yosys,folder,recipe):
    folder.mkdir(parents=True,exist_ok=True);(folder/'proof.ys').write_text(recipe)
    with (folder/'proof.log').open('w')as log:p=subprocess.run([str(yosys),'-s','proof.ys'],cwd=folder,stdout=log,stderr=subprocess.STDOUT)
    return p.returncode,(folder/'proof.log').read_text(errors='replace')

def cut(yosys,folder,header,gold,gate):
    folder.mkdir(parents=True,exist_ok=False)
    for name,body in [('gold',gold),('gate',gate)]:
        (folder/(name+'.v')).write_text(header.replace('NAME',name)+body+'\nendmodule\n')
    code,log=run_yosys(yosys,folder,"""read_verilog -sv gold.v gate.v
proc
memory_map
opt
miter -equiv -ignore_gold_x -make_outputs -make_assert -flatten gold gate miter
hierarchy -top miter
opt_clean
sat -enable_undef -set-def-inputs -set gold_defined_read 1 -verify -prove-asserts -show-inputs -show-outputs
""")
    passed=code==0 and 'SAT proof finished - no model found: SUCCESS!'in log
    rejected=code!=0 and ('SAT proof finished - model found: FAIL!'in log or 'proof did fail' in log)
    assert passed or rejected,'Tool error is not a functional counterexample'
    return dict(passed=passed,counterexample=rejected,returncode=code,log_sha256=sha(folder/'proof.log'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=REFS,required=True);p.add_argument('--parameters',type=json.loads,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    yosys=Path(shutil.which('yosys')).resolve();kind=a.kind;params=a.parameters
    assert set(params)==({'DEPTH','MAX_BYTES'}if kind=='replay'else {'MAX_TLP_DWORDS'})
    assert all(type(v)is int and v>0 for v in params.values())
    top='soc_pcie_replay_tx'if kind=='replay'else'soc_pcie_lcrc_tx'
    reference=ROOT/('sw/tests/fixtures/pcie_chip_timing/pre-bank-'+kind+'-20261017.v')
    candidate=ROOT/'hw/soc/rtl/pcie'/(top+'.v');crc=ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
    assert sha(reference)==REFS[kind]
    sources={str(p):sha(p)for p in [reference,candidate,crc,yosys,Path(__file__)]}
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],kind=kind,parameters=params,sources=sources,timing_accepted=False,full_phy_accepted=False,
        scope='Unmasked full sequential equivalence plus arbitrary defined memory/address read cuts. Includes replay cross-bank reads, LCRC all states/header sizes/byte order, no valid-only or reachable-state restriction in read cuts. Not mapped or physical timing acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        gold=reference.read_text();gate=candidate.read_text();header=cut_header(kind,params)
        golden=extract(kind,gold);actual=extract(kind,gate)
        onehot=kind=='replay' and 'reg [READ_CHOICES-1:0] replay_read_onehot;'in gate
        if onehot:
            header+="localparam integer BW=$clog2(MAX_BYTES+1),READ_CHOICES=(1<<BW);\nwire [READ_CHOICES-1:0] replay_read_onehot={{(READ_CHOICES-1){1'b0}},1'b1}<<read_pos;\n"
            anchor='    reg [BW-1:0] write_pos,read_pos;\n'
            assert gold.count(anchor)==1
            gold=gold.replace(anchor,anchor+"    localparam integer READ_CHOICES=(1<<BW);\n    (* keep = 1 *) wire [READ_CHOICES-1:0] replay_read_onehot={{(READ_CHOICES-1){1'b0}},1'b1}<<read_pos;\n")
        result['read_cut']=cut(yosys,out/'arbitrary-memory',header,golden,actual)
        assert result['read_cut']['passed'];save()
        mutations=([('wrong_byte','bytes[replay_bank*MAX_BYTES+read_pos]','bytes[replay_bank*MAX_BYTES+(read_pos^1)]'),
                    ('wrong_slot','replay_bank_byte[send_slot]','replay_bank_byte[send_slot^1]')]
                   if kind=='replay'else[
                    ('wrong_word','selected_word_byte[index]','selected_word_byte[index^1]'),
                    ('wrong_order','tx_word<header_words','tx_word>=header_words')])
        if onehot:mutations=[('wrong_byte','bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit]','~bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit]'),('wrong_slot','replay_bank_byte[send_slot]','replay_bank_byte[send_slot^1]')]
        result['controls']=[]
        for label,old,new in mutations:
            assert actual.count(old)==1
            r=cut(yosys,out/label,header,golden,actual.replace(old,new))
            assert r['counterexample']and not r['passed'];result['controls'].append(dict(fault=label,**r));save()
        seq=out/'sequential';seq.mkdir()
        for name,text in [('gold',gold),('gate',gate)]:
            declaration='module '+top+' #(';assert text.count(declaration)==1
            (seq/(name+'.v')).write_text(text.replace(declaration,'module '+name+' #('))
        (seq/'crc.v').write_bytes(crc.read_bytes())
        recipe=['read_verilog -sv crc.v gold.v gate.v']
        for name in ['gold','gate']:
            for key,value in params.items():recipe.append(f'chparam -set {key} {value} {name}')
        recipe+=['proc','flatten','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef -short','equiv_induct -undef -seq 4','equiv_status -assert']
        code,log=run_yosys(yosys,seq,'\n'.join(recipe)+'\n')
        counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
        assert code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!'in log,'Sequential equivalence incomplete'
        result['sequential']=dict(returncode=code,counts=counts,log_sha256=sha(seq/'proof.log'))
        assert all(sha(p)==h for p,h in sources.items());result['sources_unchanged']=True
        result['status']='PASS_TX_BANK_READ_CUT_CONTROLS_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(json.dumps({k:result[k]for k in ['status','kind','parameters']}),flush=True)
if __name__=='__main__':main()
