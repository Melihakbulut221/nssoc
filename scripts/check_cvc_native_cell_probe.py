# SPDX-License-Identifier: Apache-2.0
"""Supplemental CVC native-cell compatibility, not a production simulator change."""
import hashlib,importlib.util,json,pathlib,re,subprocess
root=pathlib.Path.cwd()
spec=importlib.util.spec_from_file_location('boot',root/'hw/soc/flow/sim_logic_boot_gl.py');boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
library=root/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
original=hashlib.sha256(library.read_bytes()).hexdigest()
report={'library_sha256':original,'scope':'Finite native reset/data/hold and failed-assertion compatibility; no SDF, SRAM, full-chip or speed qualification','runs':[]}
for engine in ('icarus','cvc'):
 for negative in (False,True):
    folder=root/'out'/f'native-{engine}-{int(negative)}';folder.mkdir()
    text=boot.CELL_PROBE
    if negative:
        assert 'if(q!==0)' in text
        text=text.replace('if(q!==0)','if(q!==1)',1)
    bench=folder/'tb.v';bench.write_text(text)
    compile_cmd=(['iverilog','-g2005-sv','-s','tb_native_cell_gate','-o','sim.vvp',str(bench),str(library)] if engine=='icarus' else ['/tmp/cvc/build64/cvc64',str(bench),str(library)])
    p=subprocess.run(compile_cmd,cwd=folder,capture_output=True,text=True,timeout=120)
    (folder/'compile.log').write_text(p.stdout+p.stderr)
    assert p.returncode==0,(engine,negative,p.stdout+p.stderr)
    p=subprocess.run(['vvp','sim.vvp'] if engine=='icarus' else ['./cvcsim'],cwd=folder,capture_output=True,text=True,timeout=20)
    log=p.stdout+p.stderr;(folder/'run.log').write_text(log)
    banner='NATIVE_CELL_GATE PASS' in log
    ok=(not banner and 'Native reset assertion failed' in log) if negative else (p.returncode==0 and banner and not re.search(r'(?im)FATAL:|ERROR:|%Fatal|%Error',log))
    report['runs'].append(dict(engine=engine,negative_control=negative,returncode=p.returncode,pass_banner=banner,expected_outcome_observed=ok))
    report['library_unchanged']=hashlib.sha256(library.read_bytes()).hexdigest()==original
    report['passed']=len(report['runs'])==4 and all(r['expected_outcome_observed'] for r in report['runs']) and report['library_unchanged']
    (root/'out/native-cell-result.json').write_text(json.dumps(report,indent=2))
    assert ok,(engine,negative,log)
print(json.dumps(report,indent=2))
