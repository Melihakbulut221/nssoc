#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Screen an LCRC registered word selector without adopting it or changing clocks."""
import argparse,ast,hashlib,json,os,re,shutil,subprocess,sys,traceback
from pathlib import Path
from check_pcie_tx_read_banks import cut,cut_header,extract,run_yosys
from check_pcie_integrity import tool_environment
from check_pcie_integrity_native import LIB_SHA,MODEL_SHA,quote
from cocotb_results import count_results
ROOT=Path(__file__).resolve().parents[1]
TOP='soc_pcie_lcrc_tx'
REL='hw/soc/rtl/pcie/'+TOP+'.v'
ANCHOR='    reg [CW-1:0] count,length,index;\n'
DECL="    localparam integer WORD_CHOICES=(1<<CW);\n    (* keep = 1 *) reg [WORD_CHOICES-1:0] word_read_onehot;\n"
OBS="    localparam integer WORD_CHOICES=(1<<CW);\n    (* keep = 1 *) wire [WORD_CHOICES-1:0] word_read_onehot={{(WORD_CHOICES-1){1'b0}},1'b1}<<index;\n"
ROTATE='{word_read_onehot[WORD_CHOICES-2:0],word_read_onehot[WORD_CHOICES-1]}'
SELECTION="""    // Registered decoding removes binary word-address logic from the
    // word-to-CRC cone. The full address ring preserves binary wrap and
    // out-of-range reads; cycle timing and packet framing are unchanged.
    wire [7:0] selected_onehot_byte;
    genvar read_bit,read_word;
    generate for(read_bit=0;read_bit<8;read_bit=read_bit+1) begin: select_word_bit
        wire [MAX_TLP_DWORDS-1:0] terms;
        for(read_word=0;read_word<MAX_TLP_DWORDS;read_word=read_word+1) begin: select_word
            assign terms[read_word]=word_read_onehot[read_word] & selected_word_byte[read_word][read_bit];
        end
        assign selected_onehot_byte[read_bit]=|terms;
    end endgenerate
"""
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def candidate(text):
    assert text.count(ANCHOR)==1 and text.count('    always @* begin')==1
    text=text.replace(ANCHOR,ANCHOR+DECL)
    text=text.replace('    always @* begin',SELECTION+'    always @* begin')
    assert text.count('DATA:tx_data_o=selected_word_byte[index];')==1
    text=text.replace('DATA:tx_data_o=selected_word_byte[index];',"DATA:tx_data_o=(index<MAX_TLP_DWORDS) ? selected_onehot_byte : 8'bx;")
    assert len(re.findall(r'(?<![A-Za-z0-9_])index<=0;',text))==2
    text=re.sub(r'(?<![A-Za-z0-9_])index<=0;',"index<=0;word_read_onehot<={{(WORD_CHOICES-1){1'b0}},1'b1};",text)
    old="else index<=index+1'b1;";assert text.count(old)==1
    return text.replace(old,"else begin index<=index+1'b1;word_read_onehot<="+ROTATE+";end")
def sequential(yosys,folder,gold,gate,crc,cap):
    folder.mkdir()
    for name,text in [('gold',gold),('gate',gate)]:
        key='module '+TOP+' #(';assert text.count(key)==1
        (folder/(name+'.v')).write_text(text.replace(key,'module '+name+' #('))
    shutil.copyfile(crc,folder/'crc.v')
    recipe=['read_verilog -sv crc.v gold.v gate.v']
    recipe += [f'chparam -set MAX_TLP_DWORDS {cap} {name}'for name in ['gold','gate']]
    recipe += ['proc','flatten','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef -short','equiv_induct -undef -seq 4','equiv_status -assert']
    code,log=run_yosys(yosys,folder,'\n'.join(recipe)+'\n')
    counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
    assert len(counts)==1,('Missing native proof counts',code,log[-1200:])
    return {'returncode':code,'proven':int(counts[0][0]),'unproven':int(counts[0][1]),'passed':code==0 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!'in log,'log_sha256':sha(folder/'proof.log')}
def main():
    p=argparse.ArgumentParser();p.add_argument('--capacity',type=int,required=True);p.add_argument('--native',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true' and a.capacity in [4,5,8,16]
    assert not a.native or a.capacity==8
    out=ROOT/f'cloud-lcrc-word-onehot-n{a.capacity}';out.mkdir(exist_ok=False)
    r={'status':'RUNNING','source_head':os.environ['GITHUB_SHA'],'capacity':a.capacity,'candidate_adopted':False,'timing_accepted':False,'full_phy_accepted':False,
       'scope':'Unmasked clock-event sequential equivalence and arbitrary defined-memory read proof against frozen pre-bank RTL, plus cursor/byte/order fault controls. Optional unchanged original RTL/native IHP port suite. No routed timing, SDF, physical integration or serial PHY acceptance.'}
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pins=json.loads((ROOT/'scripts/lcrc-word-onehot-method.json').read_text())['protected']
        assert all(sha(ROOT/k)==v for k,v in pins.items())
        yosys=Path(shutil.which('yosys')).resolve();iv=Path(shutil.which('iverilog')).resolve()
        before={str(ROOT/k):v for k,v in pins.items()}
        before.update({str(x):sha(x)for x in [yosys,iv,iv.with_name('vvp'),Path(__file__)]})
        canonical=ROOT/REL;crc=ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
        reference=ROOT/'sw/tests/fixtures/pcie_chip_timing/pre-bank-lcrc-20261017.v'
        old=canonical.read_text();new=candidate(old);gold=reference.read_text()
        (out/'candidate.v').write_text(new)
        r['canonical_sha256']=sha(canonical);r['candidate_sha256']=sha(out/'candidate.v');save()
        header=cut_header('lcrc',{'MAX_TLP_DWORDS':a.capacity})
        header+="localparam integer CW=$clog2(MAX_TLP_DWORDS+1),WORD_CHOICES=(1<<CW);\nwire [WORD_CHOICES-1:0] word_read_onehot={{(WORD_CHOICES-1){1'b0}},1'b1}<<index;\n"
        golden=extract('lcrc',gold);actual=extract('lcrc',new)
        r['read_cut']=cut(yosys,out/'arbitrary-memory',header,golden,actual);save();assert r['read_cut']['passed']
        r['controls']={}
        for label,bad,good in [
            ('wrong_word','selected_word_byte[read_word][read_bit]','selected_word_byte[(read_word+1)%MAX_TLP_DWORDS][read_bit]'),
            ('wrong_order','tx_word<header_words','tx_word>=header_words')]:
            assert actual.count(bad)==1
            c=cut(yosys,out/label,header,golden,actual.replace(bad,good));r['controls'][label]=c;save()
            assert c['counterexample']and not c['passed']
        # The observed combinational invariant on the unmodified reference
        # is itself proved against the new register. It is never assumed.
        assert gold.count(ANCHOR)==1
        observed=gold.replace(ANCHOR,ANCHOR+OBS)
        r['sequential']=sequential(yosys,out/'sequential',observed,new,crc,a.capacity);save()
        assert r['sequential']['passed']
        bad=new.replace(ROTATE,'word_read_onehot');assert bad!=new
        r['controls']['frozen_cursor']=sequential(yosys,out/'frozen-cursor',observed,bad,crc,a.capacity);save()
        assert not r['controls']['frozen_cursor']['passed'] and r['controls']['frozen_cursor']['unproven']>0
        if a.native:
            pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
            lib=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
            models=pdk/'libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
            assert sha(lib)==LIB_SHA and sha(models)==MODEL_SHA
            before.update({str(x):sha(x)for x in [lib,models]})
            bench=ROOT/'hw/soc/tb/cocotb/test_soc_pcie_lcrc_tx.py'
            expected=sum(isinstance(n,ast.AsyncFunctionDef)and bool(n.decorator_list)for n in ast.parse(bench.read_text()).body)
            assert expected==2
            r['ports']=[];r['native_mapping']={}
            def ports(label,sources,native=False,reject=False):
                d=out/label;d.mkdir()
                cmd=['make','-f',str(bench.with_name('Makefile.'+TOP)),'--no-print-directory',
                     'VERILOG_SOURCES='+' '.join(map(str,sources)),'SIM_BUILD='+str(d/'sim'),
                     'COCOTB_RESULTS_FILE='+str(d/'results.xml'),'PCIE_NATIVE='+str(int(native))]
                with(d/'simulation.log').open('w')as log:code=subprocess.call(cmd,cwd=d,env=tool_environment(iv.parent),stdout=log,stderr=subprocess.STDOUT)
                counts=count_results([d/'results.xml'])
                r['ports'].append({'case':label,'returncode':code,'counts':dict(zip(['passed','failed','skipped'],counts))});save()
                assert counts[2]==0 and sum(counts[:2])==expected
                if reject:assert code!=0 and counts[1]>0 and 'AssertionError'in(d/'simulation.log').read_text()
                else:assert code==0 and counts==(expected,0,0)
            for label,text in [('baseline',old),('candidate',new),('wrong-cursor',bad)]:
                d=out/(label+'-rtl');d.mkdir();rtl=d/(TOP+'.v');rtl.write_text(text)
                ports(label+'-ports',[crc,rtl],reject=label=='wrong-cursor')
                if label=='wrong-cursor':continue
                mapped=d/'mapped.v';mapped_json=d/'mapped.json'
                recipe='; '.join(['read_liberty -lib '+quote(lib),'read_verilog -sv '+quote(crc)+' '+quote(rtl),
                    'hierarchy -check -top '+TOP,'flatten -noscopeinfo','synth -top '+TOP+' -noabc',
                    'dfflibmap -liberty '+quote(lib),'abc -liberty '+quote(lib),
                    'hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO',
                    'clean','check -assert','stat -liberty '+quote(lib),
                    'write_json '+quote(mapped_json),'write_verilog -noattr -noexpr '+quote(mapped)])
                code,log=run_yosys(yosys,d,recipe+'\n');assert code==0,log[-1200:]
                cells=json.loads(mapped_json.read_text())['modules'][TOP]['cells']
                assert cells and all(c['type'].startswith('sg13g2_')for c in cells.values())
                r['native_mapping'][label]={'cells':len(cells),'netlist_sha256':sha(mapped),'json_sha256':sha(mapped_json)};save()
                ports(label+'-native-ports',[mapped,models],native=True)
                folder=out/(label+'-packet-rtl');folder.mkdir()
                for f in (ROOT/'hw/soc/rtl/pcie').glob('*.v'):shutil.copyfile(f,folder/f.name)
                (folder/(TOP+'.v')).write_text(text)
                dest=out/(label+'-reliable-packets')
                cmd=[sys.executable,str(ROOT/'scripts/check_pcie_replay.py'),'--top','soc_pcie_reliable_packets','--rtl-dir',str(folder),'--out',str(dest),'--iverilog-dir',str(iv.parent)]
                with(out/(label+'-reliable.log')).open('w')as log:code=subprocess.call(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                result=json.loads((dest/'result.json').read_text())
                r.setdefault('packet_integration',{})[label]=result;save()
                assert code==0 and result['status']=='PASS_PORT_ONLY_PCIE_REPLAY'
        assert all(sha(p)==d for p,d in before.items())
        r.update(status='PASS_LCRC_REGISTERED_WORD_SELECTION_PROOFS_NOT_TIMING_ACCEPTANCE',sources_unchanged=True,protected_inputs=before)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
        save()
if __name__=='__main__':main()
