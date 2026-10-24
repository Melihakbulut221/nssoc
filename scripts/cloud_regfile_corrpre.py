#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Actual RTL candidate; all results are standalone pre-layout, not mainchip closure.
import ast,hashlib,json,os,re,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
PHASE=os.environ.get('CORRPRE_PHASE','all')
assert PHASE in ('all','measure')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/('cloud-regfile-corrpre'+('-measure'if PHASE=='measure'else ''))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,mainchip_timing_closed=False,scope='Actual RTL CORRPRE=1 versus unchanged default CORRPRE=0. Clock-step equivalence after explicit async2sync, native asynchronous-reset stored-bit fault campaign with scrub on/off, mapped area and read-path timing. No whole-core or routed acceptance.')
    r['phase']=PHASE
    r['formal_proof_in_this_run']=PHASE=='all'
    if PHASE=='measure':r['scope']='Actual CORRPRE component native fault campaigns and paired mapped three-corner timing only. Separate live formal run remains required; no formal, mainchip or routed acceptance.'
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(tag,cmd,cwd=ROOT,env=None,bad=False):
        with (OUT/(tag+'.log')).open('w')as f:rc=subprocess.call(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(tag=tag,command=list(map(str,cmd)),returncode=rc,expected_failure=bad));save()
        assert (rc!=0 if bad else rc==0),(tag,rc)
        return (OUT/(tag+'.log')).read_text(errors='replace')
    save()
    try:
        src=ROOT/'hw/soc/rtl/ibex_regfile_secded.v';enc=ROOT/'hw/rtl/secded_enc.v';dec=ROOT/'hw/rtl/secded_dec.v'
        inputs=OUT/'inputs';inputs.mkdir()
        for f in [src,enc,dec,ROOT/'hw/soc/tb/cocotb/test_ibex_regfile_secded.py',ROOT/'hw/soc/sta/ibex.sdc.in']:shutil.copy2(f,inputs/f.name)
        r['input_hashes']={str(p.relative_to(ROOT)):sha(p)for p in [src,enc,dec]}
        run('yosys-version',['yosys','-V']);run('iverilog-version',['iverilog','-V'])
        if PHASE=='all':
            mutant=OUT/'inverted-read.v';text=src.read_text();a='assign rdata_a_o = rf_corrected[raddr_a_i];'
            assert text.count(a)==1
            mutant.write_text(text.replace(a,"assign rdata_a_o = rf_corrected[raddr_a_i] ^ 32'h1;"))
            # Every matched node obligation must be proved; no valid-codeword assumptions.
            for scrub in [1,0]:
                for bad in [False,True]:
                    tag=f'equiv-s{scrub}'+('-inverted'if bad else '');commands=[]
                    for name,corr,file in [('gold',0,src),('gate',1,mutant if bad else src)]:
                        commands += [f'read_verilog {enc} {dec} {file}',f'chparam -set CORRPRE {corr} -set SCRUB {scrub} ibex_register_file_ff','hierarchy -check -top ibex_register_file_ff','proc','flatten','async2sync','memory_map','opt_clean',f'rename ibex_register_file_ff {name}',f'design -stash {name}']
                    commands += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -seq 1','equiv_induct -seq 4','equiv_status -assert']
                    ys=OUT/(tag+'.ys');ys.write_text('\n'.join(commands)+'\n')
                    log=run(tag,['yosys','-s',str(ys)],bad=bad)
                    assert ('unproven $equiv cells'in log)if bad else ('Equivalence successfully proven!'in log)
            r['sequential_equivalence']=dict(scrub_variants=[1,0],output_inversion_controls_rejected=2);save()
        tb=ROOT/'hw/soc/tb/cocotb'
        for corr,scrub in [(0,1),(1,1),(1,0)]:
            tag=f'cocotb-c{corr}-s{scrub}';xml=OUT/(tag+'.xml');build=OUT/(tag+'-build')
            run(tag,['make','-f','Makefile.ibex_regfile_secded',f'EXTRA_COMPILE_ARGS=-Pibex_register_file_ff.CORRPRE={corr} -Pibex_register_file_ff.SCRUB={scrub}',f'SIM_BUILD={build}',f'COCOTB_RESULTS_FILE={xml}'],cwd=tb,env=dict(os.environ,REGFILE_SCRUB=str(scrub)))
            tests=list(ET.parse(xml).iter('testcase'))
            test_tree=ast.parse((tb/'test_ibex_regfile_secded.py').read_text())
            expected={n.name for n in test_tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name.startswith('test_')}
            assert len(expected)==6 and {t.attrib['name']for t in tests}==expected and len(tests)==len(expected)
            assert not any(list(t)for t in tests)
            assert ('g_corrpre'in(build/'sim.vvp').read_text())==bool(corr),'Candidate override ignored'
            r.setdefault('fault_campaigns',[]).append(dict(corrpre=corr,scrub=scrub,testcases=len(tests),failed=0,skipped=0,elaboration_verified=True));save()
        libdir=Path(os.environ['CORRPRE_LIBDIR'])
        libs={c:libdir/n for c,n in {'typ':'sg13g2_stdcell_typ_1p20V_25C.lib','slow':'sg13g2_stdcell_slow_1p08V_125C.lib','fast':'sg13g2_stdcell_fast_1p32V_m40C.lib'}.items()}
        assert all(p.is_file()for p in libs.values());r['liberty']={k:dict(path=str(v),sha256=sha(v))for k,v in libs.items()}
        constr=OUT/'abc.constr';constr.write_text('set_driving_cell sg13g2_buf_4\nset_load 0.005\n')
        sdc=OUT/'rf.sdc';sdc.write_text((ROOT/'hw/soc/sta/ibex.sdc.in').read_text().replace('@PERIOD@','20'))
        # Same historical ABC -D20ps for both, SDC20ns. Not a20ns ABC target.
        for corr in [0,1]:
            tag=f'corrpre{corr}';net=OUT/(tag+'.v');stat=OUT/(tag+'.stat.json');ys=OUT/(tag+'.ys')
            ys.write_text(f'''read_liberty -lib {libs['typ']}
read_verilog {enc} {dec} {src}
chparam -set CORRPRE {corr} ibex_register_file_ff
hierarchy -check -top ibex_register_file_ff
synth -flatten -top ibex_register_file_ff
opt -purge
dfflibmap -liberty {libs['typ']}
opt
abc -liberty {libs['typ']} -constr {constr} -D 20
flatten
setundef -zero
opt_clean -purge
splitnets
clean
write_verilog -noattr -noexpr -nohex -nodec {net}
check -assert
tee -o {stat} stat -json -liberty {libs['typ']}
''')
            run(tag+'-synth',['yosys','-s',str(ys)])
            r.setdefault('mapped',{})[tag]=dict(netlist_sha256=sha(net),statistics=json.loads(stat.read_text()))
            for corner,lib in libs.items():
                tcl=OUT/(tag+'-'+corner+'.tcl')
                tcl.write_text(f'''read_liberty {lib}
read_verilog {net}
link_design ibex_register_file_ff
read_sdc {sdc}
puts "ALL_PATHS"
report_checks -path_delay min_max -group_path_count 5 -format full_clock_expanded -digits 9
puts "ADDRESS_TO_READ"
report_checks -path_delay max -from [get_ports {{raddr_a_i* raddr_b_i*}}] -to [get_ports {{rdata_a_o* rdata_b_o*}}] -group_path_count 5 -format full_clock_expanded -digits 9
puts "STORAGE_TO_READ"
report_checks -path_delay max -from [all_registers -output_pins] -to [get_ports {{rdata_a_o* rdata_b_o*}}] -group_path_count 5 -format full_clock_expanded -digits 9
puts "COVERAGE"
check_setup -verbose
exit
''')
                log=run(tag+'-'+corner,[os.environ['CLOUD_APPIMAGE'],'sta','-no_splash','-exit',str(tcl)])
                assert not re.search(r'(?m)^Error:',log);paths={}
                for section,end in [('ADDRESS_TO_READ','STORAGE_TO_READ'),('STORAGE_TO_READ','COVERAGE')]:
                    body=log.split(section+'\n',1)[1].split(end+'\n',1)[0]
                    arrivals=[float(v)for v in re.findall(r'^\s*([-+0-9.]+)\s+data arrival time',body,re.M)]
                    assert arrivals,(tag,corner,section);paths[section]=dict(arrival_ns=arrivals,worst_arrival_ns=max(arrivals))
                r.setdefault('prelayout_timing',{})[tag+'-'+corner]=paths;save()
        assert all(sha(ROOT/p)==h for p,h in r['input_hashes'].items())
        r['status']=('COMPLETE_CORRPRE_COMPONENT_VALIDATION_NOT_MAINCHIP_TIMING_CLOSURE'if PHASE=='all'else 'COMPLETE_CORRPRE_COMPONENT_MEASUREMENTS_FORMAL_AND_MAINCHIP_ACCEPTANCE_STILL_REQUIRED')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
