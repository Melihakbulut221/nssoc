#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact CRC parallelization proof and native packet-path timing experiment."""
import ast,copy,hashlib,json,os,re,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_lcrc_word_onehot_candidate import candidate as onehot, ANCHOR, OBS
from cloud_lcrc_word_onehot_timing import normalize_structural,verify_structural,q
from check_pcie_tx_read_banks import run_yosys
from check_pcie_integrity import tool_environment
from check_pcie_integrity_native import LIB_SHA,MODEL_SHA,quote
from check_pcie_replay import COMMON,LINK
from cocotb_results import count_results
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-crc32-parallel-candidate'
TOPS=['soc_pcie_lcrc_tx','soc_pcie_reliable_packets']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def balanced(terms):
    if not terms:return "1'b0"
    if len(terms)==1:return terms[0]
    cut=len(terms)//2
    return '('+balanced(terms[:cut])+' ^ '+balanced(terms[cut:])+')'
def generate_crc():
    masks=[1<<i if i<8 else 0 for i in range(32)]
    for _ in range(8):
        f=masks[0]
        masks=[(masks[i+1]if i<31 else 0)^(f if (0xedb88320>>i)&1 else 0)for i in range(32)]
    lines=['// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut',
      '// SPDX-License-Identifier: CERN-OHL-W-2.0',chr(96)+'default_nettype none',
      '// Candidate: exact reflected CRC byte transform, no state or latency.',
      'module soc_pcie_crc32_byte(input wire [31:0] state_i, input wire [7:0] data_i, output wire [31:0] state_o);',
      'wire [7:0] feedback=state_i[7:0] ^ data_i;']
    for i,mask in enumerate(masks):
        terms=(['state_i['+str(i+8)+']']if i<24 else [])+['feedback['+str(j)+']'for j in range(8)if mask>>j&1]
        lines.append('assign state_o['+str(i)+'] = '+balanced(terms)+';')
    return '\n'.join(lines+['endmodule',chr(96)+'default_nettype wire','']),masks
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],candidate_adopted=False,full_phy_accepted=False,final_timing_complete=False,
      scope='Balanced CRC XOR transform and optional word cursor; unmasked LCRC sequential proof, native port tests and three-corner LCRC plus reliable-packet timing. Ideal clock, zero wire RC. Not physical closure.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        spec=json.loads((ROOT/'scripts/crc32-parallel-method.json').read_text())
        protected={}
        for rel,blob in spec['protected_git_blobs'].items():
            p=ROOT/rel;b=p.read_bytes()
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
            protected[str(p)]=sha(p)
        protected[str(Path(__file__))]=sha(__file__)
        crc=ROOT/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
        lcrc=ROOT/'hw/soc/rtl/pcie/soc_pcie_lcrc_tx.v'
        original=crc.read_text();parallel,masks=generate_crc()
        (OUT/'parallel-crc.v').write_text(parallel)
        r['crc_candidate']=dict(sha256=sha(OUT/'parallel-crc.v'),feedback_masks=masks)
        yosys=Path(shutil.which('yosys')).resolve();iv=Path(shutil.which('iverilog')).resolve()
        protected.update({str(p):sha(p)for p in [yosys,iv,iv.with_name('vvp')]})
        def combinational(label,text,negative=False):
            d=OUT/label;d.mkdir()
            (d/'gold.v').write_text(original.replace('module soc_pcie_crc32_byte','module gold'))
            (d/'gate.v').write_text(text.replace('module soc_pcie_crc32_byte','module gate'))
            recipe='\n'.join(['read_verilog -sv gold.v gate.v','proc','opt',
              'miter -equiv -make_outputs -make_assert -flatten gold gate miter','hierarchy -top miter',
              'sat -enable_undef -set-def-inputs -verify -prove-asserts -show-inputs -show-outputs'])
            code,log=run_yosys(yosys,d,recipe+'\n')
            passed=code==0 and 'SAT proof finished - no model found: SUCCESS!'in log
            rejected=code!=0 and ('proof did fail'in log or 'SAT proof finished - model found: FAIL!'in log)
            assert passed or rejected,'Tool failure is not a counterexample'
            result=dict(passed=passed,counterexample=rejected,returncode=code,log_sha256=sha(d/'proof.log'))
            assert rejected if negative else passed
            return result
        r['crc_all_40_input_bits_proof']=combinational('crc-proof',parallel);save()
        fault=parallel.replace('state_o[0] = ','state_o[0] = ~',1)
        r['wrong_crc_bit_control']=combinational('crc-wrong-bit',fault,True);save()
        def sequential(label,cursor):
            d=OUT/label;d.mkdir()
            gold=lcrc.read_text();gate=onehot(gold)if cursor else gold
            if cursor:gold=gold.replace(ANCHOR,ANCHOR+OBS)
            for name,text,c in [('gold',gold,original),('gate',gate,parallel)]:
                (d/(name+'.v')).write_text(text.replace('module soc_pcie_lcrc_tx #(','module '+name+' #(').replace('soc_pcie_crc32_byte crc_step','crc_'+name+' crc_step'))
                (d/('crc_'+name+'.v')).write_text(c.replace('module soc_pcie_crc32_byte','module crc_'+name))
            code,log=run_yosys(yosys,d,'\n'.join(['read_verilog -sv gold.v gate.v crc_gold.v crc_gate.v','proc','flatten','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef -short','equiv_induct -undef -seq 4','equiv_status -assert'])+'\n')
            counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
            r.setdefault('sequential',{})[label]=dict(returncode=code,counts=counts,log_sha256=sha(d/'proof.log'));save()
            assert code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!'in log
        sequential('lcrc-parallel-sequential',False)
        sequential('lcrc-parallel-onehot-sequential',True)
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        libroot=pdk/'libs.ref/sg13g2_stdcell'
        libs={c:libroot/'lib'/f for c,f in [
          ('typ','sg13g2_stdcell_typ_1p20V_25C.lib'),('slow','sg13g2_stdcell_slow_1p08V_125C.lib'),('fast','sg13g2_stdcell_fast_1p32V_m40C.lib')]}
        models=libroot/'verilog/sg13g2_stdcell.v'
        assert sha(libs['typ'])==LIB_SHA and sha(models)==MODEL_SHA
        pin=spec['sta_source']
        selected=['runtime/sta','runtime/opensta-source.tar.gz','runtime/cudd-source.tar.gz','runtime/opensta-generated-build.patch','runtime/cudd-generated-build.patch','runtime/build-workflow.yml','runtime/README.txt','runtime/dynamic-libraries.txt','baseline.json','candidate.json','baseline-slow/ALL_MAX.rpt','candidate-slow/ALL_MAX.rpt']
        selected+=[p.name for p in libs.values()]
        libs={c:OUT/'prior-sta'/p.name for c,p in libs.items()}
        old,proof=reports.restore_report('lcrc-word-onehot-timing',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'prior-sta',selected)
        assert old['status']=='COMPLETE_THREE_CORNER_ZERO_WIRE_COMPARISON_NOT_PHYSICAL_ACCEPTANCE'and old['sources_unchanged']
        assert old['source_head']==pin['source_head']
        for c,lib in libs.items():assert sha(lib)==old['libraries'][c]['sha256']
        sta=OUT/'prior-sta/runtime/sta';sta.chmod(0o755)
        assert sha(sta)==old['retained_runtime']['binary_sha256']
        deps=subprocess.run(['ldd',str(sta)],capture_output=True,text=True)
        (OUT/'sta-ldd.log').write_text(deps.stdout+deps.stderr)
        assert deps.returncode==0 and 'not found'not in deps.stdout+deps.stderr
        r['sta_source']=proof;r['diagnostic_conditions']=old['diagnostic_conditions']
        protected.update({str(p):sha(p)for p in [sta,models,*libs.values()]})
        r['prior_worst_paths']={}
        for label in ['baseline','candidate']:
            m=json.loads((OUT/'prior-sta'/(label+'.json')).read_text())['modules']['soc_pcie_lcrc_tx']
            aliases=old['cell_name_aliases'][label];back={v:k for k,v in aliases.items()}
            body=(OUT/'prior-sta'/(label+'-slow/ALL_MAX.rpt')).read_text()
            first=body.split('Startpoint:')[1].split('Startpoint:')[0];cells={}
            for alias in set(re.findall(r'physical_cell_\d+',first)):
                original_name=back[alias];cell=m['cells'][original_name];qbits=cell['connections'].get('Q',[])
                names={n:v['bits']for n,v in m['netnames'].items()if any(b in qbits for b in v['bits'])}
                cells[alias]=dict(original_cell=original_name,type=cell['type'],connections=cell['connections'],q_netnames=names)
            assert cells
            r['prior_worst_paths'][label]=dict(report=first,cells=cells)
        save()
        variants={'baseline':(original,lcrc.read_text()),'parallel':(parallel,lcrc.read_text()),'parallel_onehot':(parallel,onehot(lcrc.read_text()))}
        r['ports']=[];r['mapping']={};r['timing']={}
        def ports(top,label,inputs,native=False,reject=False):
            d=OUT/(top+'-'+label+'-ports');d.mkdir()
            bench=ROOT/'hw/soc/tb/cocotb'/('test_'+top+'.py')
            expected=sum(isinstance(n,ast.AsyncFunctionDef)and bool(n.decorator_list)for n in ast.parse(bench.read_text()).body)
            assert expected==(2 if top=='soc_pcie_lcrc_tx'else 4)
            cmd=['make','-f',str(bench.with_name('Makefile.'+top)),'--no-print-directory','VERILOG_SOURCES='+' '.join(map(str,inputs)),'SIM_BUILD='+str(d/'sim'),'COCOTB_RESULTS_FILE='+str(d/'results.xml'),'PCIE_NATIVE='+str(int(native))]
            with(d/'simulation.log').open('w')as f:code=subprocess.call(cmd,cwd=d,env=tool_environment(iv.parent),stdout=f,stderr=subprocess.STDOUT)
            counts=count_results([d/'results.xml'])
            r['ports'].append(dict(top=top,label=label,returncode=code,passed=counts[0],failed=counts[1],skipped=counts[2]));save()
            assert counts[2]==0 and sum(counts[:2])==expected
            if reject:assert code!=0 and counts[1]>0 and 'AssertionError'in(d/'simulation.log').read_text()
            else:assert code==0 and counts==(expected,0,0)
        for label,(ct,lt)in variants.items():
            folder=OUT/(label+'-rtl');folder.mkdir()
            for p in (ROOT/'hw/soc/rtl/pcie').glob('*.v'):shutil.copyfile(p,folder/p.name)
            (folder/crc.name).write_text(ct);(folder/lcrc.name).write_text(lt)
            for top in TOPS:
                names=['soc_pcie_crc32_byte','soc_pcie_lcrc_tx']if top=='soc_pcie_lcrc_tx'else list(COMMON+LINK+('soc_pcie_dllp_rx','soc_pcie_replay_tx','soc_pcie_reliable_packets'))
                sources=[folder/(n+'.v')for n in names]
                ports(top,label+'-rtl',sources)
                d=OUT/(top+'-'+label+'-mapped');d.mkdir()
                mapped=d/'mapped.v';mapped_json=d/'mapped.json'
                recipe='; '.join(['read_liberty -lib '+quote(libs['typ']),'read_verilog -sv '+' '.join(quote(p)for p in sources),'hierarchy -check -top '+top,'flatten -noscopeinfo','synth -top '+top+' -noabc','dfflibmap -liberty '+quote(libs['typ']),'abc -liberty '+quote(libs['typ']),'hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO','clean','check -assert','stat -liberty '+quote(libs['typ']),'write_json '+quote(mapped_json),'write_verilog -noattr -noexpr '+quote(mapped)])
                code,log=run_yosys(yosys,d,recipe+'\n');assert code==0,log[-4000:]
                (d/'proof.log').rename(d/'synthesis.log');(d/'proof.ys').rename(d/'synthesis.ys')
                module=json.loads(mapped_json.read_text())['modules'][top]
                assert module['cells']and all(c['type'].startswith('sg13g2_')for c in module['cells'].values())
                key=top+'/'+label
                r['mapping'][key]=dict(cells=len(module['cells']),netlist_sha256=sha(mapped),json_sha256=sha(mapped_json));save()
                ports(top,label+'-mapped',[mapped,models],True)
                scalar=d/'scalar.v';aliases=normalize_structural(module,scalar)
                if top!='soc_pcie_lcrc_tx':
                    text=scalar.read_text();assert text.count('module soc_pcie_lcrc_tx (')==1
                    scalar.write_text(text.replace('module soc_pcie_lcrc_tx (','module '+top+' ('))
                parsed=d/'scalar.json'
                code,log=run_yosys(yosys,d,'read_liberty -lib '+quote(libs['typ'])+'\nread_verilog '+quote(scalar)+'\nhierarchy -check -top '+top+'\nwrite_json '+quote(parsed)+'\n')
                assert code==0,log[-2000:]
                native_module=json.loads(parsed.read_text())['modules'][top]
                r['mapping'][key]['normalization']=verify_structural(module,native_module,aliases)
                r['mapping'][key]['aliases']=aliases
                wrong=copy.deepcopy(native_module);name=next(n for n,c in wrong['cells'].items()if 'D'in c['connections']);wrong['cells'][name]['connections']['D']=['1']
                try:verify_structural(module,wrong,aliases)
                except AssertionError:r['mapping'][key]['normalization']['wrong_data_pin_rejected']=True
                else:raise AssertionError('Bad scalar pin accepted')
                r['timing'][key]={};save()
                for corner,lib in libs.items():
                    td=d/corner;td.mkdir()
                    lines=['read_liberty '+q(lib),'read_verilog '+q(scalar),'link_design '+top,'create_clock -name clk -period 4 [get_ports clk_i]','set_clock_uncertainty 0.25 [get_clocks clk]','set_clock_transition 0.05 [get_clocks clk]','set_input_transition 0.05 [all_inputs]','set_load 0.01 [all_outputs]','set_timing_derate -late 1.05','set_timing_derate -early 0.95','check_setup -verbose']
                    for delay in ['max','min']:
                        lines+=['puts BEGIN_'+delay,'report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay '+delay+' -group_path_count 10 -format full_clock_expanded -digits 9','puts END_'+delay]
                    lines+=['exit'];(td/'analysis.tcl').write_text('\n'.join(lines)+'\n')
                    with(td/'native.log').open('w')as f:code=subprocess.call([str(sta),'-exit',str(td/'analysis.tcl')],stdout=f,stderr=subprocess.STDOUT)
                    text=(td/'native.log').read_text()
                    assert code==0 and not re.search(r'(^|\n)Error[: ]|invalid command name|wrong # args',text),text[-5000:]
                    row={}
                    for delay in ['max','min']:
                        a='BEGIN_'+delay;b='END_'+delay;assert text.count(a)==text.count(b)==1
                        body=text.split(a)[1].split(b)[0]
                        values=[float(v)for v in re.findall(r'([-+]?[0-9]+(?:\.[0-9]+)?)\s+slack\s+\((?:MET|VIOLATED)\)',body)]
                        assert values and len(values)<=10
                        (td/(delay+'.rpt')).write_text(body)
                        row[delay]=dict(minimum_reported_slack_ns=min(values),reported_paths=len(values),report_sha256=sha(td/(delay+'.rpt')))
                    r['timing'][key][corner]=row;save()
        fault_dir=OUT/'fault-rtl';fault_dir.mkdir()
        (fault_dir/crc.name).write_text(fault)
        ports('soc_pcie_lcrc_tx','wrong-crc',[fault_dir/crc.name,lcrc],reject=True)
        r['differences']={top:{label:{c:{delay:r['timing'][top+'/'+label][c][delay]['minimum_reported_slack_ns']-r['timing'][top+'/baseline'][c][delay]['minimum_reported_slack_ns']for delay in ['max','min']}for c in libs}for label in ['parallel','parallel_onehot']}for top in TOPS}
        assert all(sha(p)==v for p,v in protected.items())
        r.update(status='COMPLETE_CRC_PARALLEL_PROOF_PORTS_AND_NATIVE_PACKET_COMPARISON_NOT_PHYSICAL_ACCEPTANCE',sources_unchanged=True,protected_inputs=protected)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
