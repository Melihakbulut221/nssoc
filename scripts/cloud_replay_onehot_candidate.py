#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove registered one-hot replay selection before canonical RTL adoption."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from check_pcie_tx_read_banks import run_yosys,cut,cut_header,extract
from cocotb_results import count_results
ROOT=Path(__file__).resolve().parents[1]
REL='hw/soc/rtl/pcie/soc_pcie_replay_tx.v'
BASE='1a15c0b9d6cfdfbf5ebed9a61c52901e126ca826008d167ff96bea4218a8f4dc'
CRC='b3e856cb329d35a634171f6c57b4e0205b94d140e8e8c50ca6334826dbb70129'
ANCHOR='    reg [BW-1:0] write_pos,read_pos;\n'.replace('\n','\n')
DECL="    localparam integer READ_CHOICES=(1<<BW);\n    (* keep = 1 *) reg [READ_CHOICES-1:0] replay_read_onehot;\n".replace('\n','\n')
BODY="""    // A registered one-hot cursor removes binary-address decoding from
    // the memory-to-transmit path. Include cross-bank addresses exactly as
    // the flat reference does; unaddressable array reads remain undefined.
    wire [7:0] replay_bank_byte [0:DEPTH-1];
    genvar replay_bank,replay_bit,replay_offset;
    generate for(replay_bank=0;replay_bank<DEPTH;replay_bank=replay_bank+1) begin: read_replay_bank
        for(replay_bit=0;replay_bit<8;replay_bit=replay_bit+1) begin: read_bit
            wire [READ_CHOICES-1:0] selected;
            for(replay_offset=0;replay_offset<READ_CHOICES;replay_offset=replay_offset+1) begin: read_byte
                if(replay_bank*MAX_BYTES+replay_offset<DEPTH*MAX_BYTES) begin: present
                    assign selected[replay_offset]=replay_read_onehot[replay_offset] & bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit];
                end else begin: absent
                    assign selected[replay_offset]=1'b0;
                end
            end
            assign replay_bank_byte[replay_bank][replay_bit]=(read_pos<(DEPTH-replay_bank)*MAX_BYTES) ? |selected : 1'bx;
        end
    end endgenerate
    assign tx_data_o=replay_bank_byte[send_slot];
"""
ROTATE='{replay_read_onehot[READ_CHOICES-2:0],replay_read_onehot[READ_CHOICES-1]}'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def candidate(text):
    assert hashlib.sha256(text.encode()).hexdigest()==BASE
    old=extract('replay',text);assert text.count(old)==1 and text.count(ANCHOR)==1
    new=text.replace(ANCHOR,ANCHOR+DECL).replace(old,BODY)
    assert new.count('read_pos<=0;')==3
    new=new.replace('read_pos<=0;',"read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};")
    old_step="else read_pos<=read_pos+1'b1;"
    assert new.count(old_step)==1
    new=new.replace(old_step,"else begin read_pos<=read_pos+1'b1;replay_read_onehot<="+ROTATE+";end")
    return new

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--depth',type=int,required=True);ap.add_argument('--max-bytes',type=int,required=True);ap.add_argument('--ports',action='store_true');a=ap.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert (a.depth,a.max_bytes) in [(2,18),(3,38),(4,38)]
    out=ROOT/f'cloud-replay-onehot-d{a.depth}-b{a.max_bytes}';out.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],parameters=dict(DEPTH=a.depth,MAX_BYTES=a.max_bytes),adopted=False,timing_accepted=False,full_phy_accepted=False,scope='Actual replay controller, registered one-hot address and parallel byte reduction. Original cycle behavior, invalid outputs and flat cross-bank reads retained. No clock/constraint/handshake change. This proof is not mapped or routed timing.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        canonical=ROOT/REL;baseline=ROOT/'sw/tests/fixtures/pcie_chip_timing/pre-onehot-replay-20261017.v';crc=ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
        assert sha(baseline)==BASE and sha(crc)==CRC
        original=baseline.read_text();altered=candidate(original)
        assert canonical.read_text()==altered,'Canonical replay differs from exactly proven one-hot candidate'
        yosys=Path(shutil.which('yosys')).resolve();iverilog=Path(shutil.which('iverilog')).resolve()
        protected={str(p):sha(p)for p in [baseline,canonical,crc,yosys,iverilog,Path(__file__),ROOT/'scripts/check_pcie_replay.py']}
        folders={}
        for label in ['baseline','candidate','wrong_cursor']:
            folder=out/(label+'-rtl');folder.mkdir();folders[label]=folder
            for p in (ROOT/'hw/soc/rtl/pcie').glob('*.v'):shutil.copyfile(p,folder/p.name)
        (folders['baseline']/'soc_pcie_replay_tx.v').write_text(original)
        (folders['candidate']/'soc_pcie_replay_tx.v').write_text(altered)
        wrong=altered.replace(ROTATE,'replay_read_onehot');assert wrong!=altered
        (folders['wrong_cursor']/'soc_pcie_replay_tx.v').write_text(wrong)
        r['baseline_sha256']=BASE;r['candidate_sha256']=sha(folders['candidate']/'soc_pcie_replay_tx.v');save()
        header=cut_header('replay',r['parameters'])+'localparam integer BW=$clog2(MAX_BYTES+1),READ_CHOICES=(1<<BW);\nwire [READ_CHOICES-1:0] replay_read_onehot={{(READ_CHOICES-1){1\'b0}},1\'b1}<<read_pos;\n'
        golden=extract('replay',original);actual=extract('replay',altered)
        r['read_cut']=cut(yosys,out/'arbitrary-memory',header,golden,actual);assert r['read_cut']['passed'];save()
        r['controls']={}
        for label,old,new in [('wrong_byte','bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit]','~bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit]'),('wrong_slot','replay_bank_byte[send_slot]','replay_bank_byte[send_slot^1]')]:
            assert actual.count(old)==1
            p=cut(yosys,out/label,header,golden,actual.replace(old,new));assert p['counterexample'] and not p['passed'];r['controls'][label]=p;save()
        # Add an observation wire to the unchanged golden controller. Equiv
        # must prove this wire against the added register, as well as ALL
        # original outputs/state; it is not an assumed or masked invariant.
        gold=original.replace(ANCHOR,ANCHOR+"    localparam integer READ_CHOICES=(1<<BW);\n    (* keep = 1 *) wire [READ_CHOICES-1:0] replay_read_onehot={{(READ_CHOICES-1){1'b0}},1'b1}<<read_pos;\n")
        seq=out/'sequential';seq.mkdir()
        for name,text in [('gold',gold),('gate',altered)]:
            anchor='module soc_pcie_replay_tx #(';assert text.count(anchor)==1
            (seq/(name+'.v')).write_text(text.replace(anchor,'module '+name+' #('))
        shutil.copyfile(crc,seq/'crc.v')
        recipe=['read_verilog -sv crc.v gold.v gate.v']
        for name in ['gold','gate']:recipe += [f'chparam -set DEPTH {a.depth} {name}',f'chparam -set MAX_BYTES {a.max_bytes} {name}']
        recipe += ['proc','flatten','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef -short','equiv_induct -undef -seq 4','equiv_status -assert','']
        code,log=run_yosys(yosys,seq,'\n'.join(recipe))
        counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
        r['sequential']=dict(returncode=code,counts=counts,log_sha256=sha(seq/'proof.log'));save()
        assert code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!'in log,'Full unmasked sequential proof failed'
        r['ports']=[]
        if a.ports:
            for label in ['baseline','candidate','wrong_cursor']:
                for top in (['soc_pcie_replay_tx']if label=='wrong_cursor'else ['soc_pcie_replay_tx','soc_pcie_reliable_packets']):
                    dest=out/(label+'-'+top)
                    command=[sys.executable,str(ROOT/'scripts/check_pcie_replay.py'),'--top',top,'--out',str(dest),'--rtl-dir',str(folders[label]),'--iverilog-dir',str(iverilog.parent)]
                    with(out/(label+'-'+top+'.log')).open('w')as stream:code=subprocess.call(command,stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
                    record=json.loads((dest/'result.json').read_text());observed=count_results([dest/'results.xml'])
                    r['ports'].append(dict(case=label,top=top,returncode=code,result=record,observed_tests=dict(zip(['passed','failed','skipped'],observed))));save()
                    passed,failed,skipped=observed;assert skipped==0 and passed+failed==record['expected_tests']
                    if label=='wrong_cursor':assert code!=0 and failed>0 and 'AssertionError'in(dest/'simulation.log').read_text()
                    else:assert code==0 and failed==0 and record['status']=='PASS_PORT_ONLY_PCIE_REPLAY'
        assert all(sha(p)==d for p,d in protected.items())
        r.update(status='PASS_REPLAY_ONEHOT_CUT_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING',sources_unchanged=True,protected_inputs=protected,port_tests_executed=a.ports)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
