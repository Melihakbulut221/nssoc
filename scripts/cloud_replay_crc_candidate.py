#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove a cycle-exact replay CRC verdict cut on the actual banked chip source."""
import argparse,base64,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from check_pcie_tx_read_banks import run_yosys
from cocotb_results import count_results
ROOT=Path(__file__).resolve().parents[1]
BASE='a745b57c0eec0e03d687d034f847e25233fc85ccbb242eca51b754656dff78dc'
CRC='b3e856cb329d35a634171f6c57b4e0205b94d140e8e8c50ca6334826dbb70129'
BOOT='f65c0c35a6e2c706f0fe7df485ab6b2115b11e6a'
REL='hw/soc/rtl/pcie/soc_pcie_replay_tx.v'
DECL="    wire replay_crc_residue_ok=((in_sop_i ? 32'hffffffff : input_crc) ^\n                              {24'b0,in_data_i})==32'h00be26ed;\n"
EXPR="((in_sop_i ? 32'hffffffff : input_crc) ^ {24'b0,in_data_i})==32'h00be26ed"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def candidate(text):
    anchor='    wire [31:0] next_crc;\n';verdict="next_crc!=32'hdebb20e3"
    assert text.count(anchor)==text.count(verdict)==1
    new=text.replace(anchor,anchor+DECL).replace(verdict,'!replay_crc_residue_ok')
    assert new.replace(DECL,'').replace('!replay_crc_residue_ok',verdict)==text
    return new

def cut(yosys,folder,expression):
    folder.mkdir()
    header='module NAME(input [31:0] input_crc,input [7:0] in_data_i,input in_sop_i,output good);\n'
    gold="wire [31:0] next_crc; soc_pcie_crc32_byte update_crc(.state_i(in_sop_i ? 32'hffffffff : input_crc),.data_i(in_data_i),.state_o(next_crc));\nassign good=next_crc==32'hdebb20e3;\nendmodule\n"
    (folder/'gold.v').write_text(header.replace('NAME','gold')+gold)
    (folder/'gate.v').write_text(header.replace('NAME','gate')+'assign good='+expression+';\nendmodule\n')
    shutil.copyfile(ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v',folder/'crc.v')
    code,log=run_yosys(yosys,folder,'\n'.join(['read_verilog -sv crc.v gold.v gate.v','proc','flatten','opt',
        'miter -equiv -make_outputs -make_assert -flatten gold gate miter','hierarchy -top miter','opt_clean',
        'sat -verify -prove-asserts -set-def-inputs -show-inputs -show-outputs -dump_json counterexample.json','']))
    passed=code==0 and 'SAT proof finished - no model found: SUCCESS!'in log
    rejected=code!=0 and ('SAT proof finished - model found: FAIL!'in log or 'proof did fail'in log)
    assert passed or rejected,'Tool error cannot substitute for a counterexample'
    if rejected:assert (folder/'counterexample.json').is_file()
    return dict(passed=passed,counterexample=rejected,returncode=code,log_sha256=sha(folder/'proof.log'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--depth',type=int,required=True);ap.add_argument('--max-bytes',type=int,required=True);ap.add_argument('--ports',action='store_true');a=ap.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert (a.depth,a.max_bytes)in[(2,18),(3,38),(4,38)]
    out=ROOT/f'cloud-replay-crc-d{a.depth}-b{a.max_bytes}';out.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],parameters=dict(DEPTH=a.depth,MAX_BYTES=a.max_bytes),
        adopted=False,timing_accepted=False,full_phy_accepted=False,
        scope='Same banked replay source as current physical chip. Only EOP CRC Boolean predicate changes, no extra cycle or handshake changes. All41bit combinational proof, full unmasked sequential equivalence and optional original full port scoreboards. No mapped or routed timing claim.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        baseline=ROOT/'sw/tests/fixtures/pcie_chip_timing/pre-residue-replay-20261017.v';crc=ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
        canonical=ROOT/REL
        assert sha(baseline)==BASE and sha(crc)==CRC
        remote=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/contents/'+REL+'?ref='+BOOT]))
        assert hashlib.sha256(base64.b64decode(remote['content'])).hexdigest()==BASE
        r['physical_boot_source']=dict(head=BOOT,replay_sha256=BASE,byte_identity_verified=True)
        yosys=Path(shutil.which('yosys')).resolve();iverilog=Path(shutil.which('iverilog')).resolve()
        protected={str(p):sha(p)for p in [baseline,canonical,crc,yosys,iverilog,Path(__file__),ROOT/'scripts/check_pcie_replay.py']}
        original=baseline.read_text();altered=candidate(original)
        assert canonical.read_text()==altered,'Canonical RTL differs from exactly proven candidate'
        folders={}
        for label in ['baseline','candidate','wrong_residue']:
            folder=out/(label+'-rtl');folder.mkdir();folders[label]=folder
            for p in (ROOT/'hw/soc/rtl/pcie').glob('*.v'):shutil.copyfile(p,folder/p.name)
        (folders['candidate']/'soc_pcie_replay_tx.v').write_text(altered)
        wrong=altered.replace("==32'h00be26ed","==32'h00be26ec");assert wrong!=altered
        (folders['wrong_residue']/'soc_pcie_replay_tx.v').write_text(wrong)
        r['candidate_sha256']=sha(folders['candidate']/'soc_pcie_replay_tx.v')
        r['cut_proof']=cut(yosys,out/'predicate',EXPR);assert r['cut_proof']['passed'];save()
        r['controls']={}
        for label,expr in [('wrong_residue',EXPR.replace('00be26ed','00be26ec')),('wrong_byte',EXPR.replace('in_data_i}',"(in_data_i ^ 8'h01)}"))]:
            proof=cut(yosys,out/label,expr);assert proof['counterexample']and not proof['passed'];r['controls'][label]=proof;save()
        seq=out/'sequential';seq.mkdir()
        for name,text in [('gold',original),('gate',altered)]:
            anchor='module soc_pcie_replay_tx #(';assert text.count(anchor)==1
            (seq/(name+'.v')).write_text(text.replace(anchor,'module '+name+' #('))
        shutil.copyfile(crc,seq/'crc.v')
        recipe=['read_verilog -sv crc.v gold.v gate.v']
        for name in ['gold','gate']:
            recipe += [f'chparam -set DEPTH {a.depth} {name}',f'chparam -set MAX_BYTES {a.max_bytes} {name}']
        recipe += ['proc','flatten','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv',
            'equiv_simple -undef -short','equiv_induct -undef -seq 4','equiv_status -assert','']
        code,log=run_yosys(yosys,seq,'\n'.join(recipe))
        counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
        assert code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!'in log,'Full sequential proof failed'
        r['sequential']=dict(returncode=code,counts=counts,log_sha256=sha(seq/'proof.log'));save()
        r['ports']=[]
        if a.ports:
            for label in ['baseline','candidate','wrong_residue']:
                tops=['soc_pcie_replay_tx'] if label=='wrong_residue'else ['soc_pcie_replay_tx','soc_pcie_reliable_packets']
                for top in tops:
                    dest=out/(label+'-'+top)
                    command=[sys.executable,str(ROOT/'scripts/check_pcie_replay.py'),'--top',top,'--out',str(dest),'--rtl-dir',str(folders[label]),'--iverilog-dir',str(iverilog.parent)]
                    with(out/(label+'-'+top+'.log')).open('w')as stream:
                        code=subprocess.call(command,stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
                    record=json.loads((dest/'result.json').read_text());observed=count_results([dest/'results.xml'])
                    item=dict(case=label,top=top,returncode=code,result=record,observed_tests=dict(zip(['passed','failed','skipped'],observed)))
                    r['ports'].append(item);save()
                    passed,failed,skipped=observed
                    assert skipped==0 and passed+failed==record['expected_tests']
                    if label=='wrong_residue':assert code!=0 and failed>0 and 'AssertionError'in(dest/'simulation.log').read_text()
                    else:assert code==0 and failed==0 and record['status']=='PASS_PORT_ONLY_PCIE_REPLAY'
        assert all(sha(p)==d for p,d in protected.items())
        r.update(status='PASS_REPLAY_RESIDUE_CUT_AND_FULL_SEQUENTIAL_EQUIVALENCE_NOT_TIMING',sources_unchanged=True,
            protected_inputs=protected,controller_restore_byte_exact=True,port_tests_executed=a.ports)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
