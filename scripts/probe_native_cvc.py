"""Cloud-only CVC/Icarus untouched-IHP cell and four-state preflight, not chip acceptance."""
import os,sys,json,pathlib,hashlib,subprocess,time
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'hw/soc/flow'))
from sim_logic_boot_gl import CELL_PROBE
out=root/'cvc-probe';out.mkdir(exist_ok=False)
lib=root/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(lib)=='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
cvc=root/'cvc-source/build64/cvc64'
bench=CELL_PROBE.replace(' $display("NATIVE_CELL_GATE PASS");', '  d=1\'bx;\n  #20; if(q!==1\'bx) $fatal(1,"Four-state X capture failed");\n  rst=0;\n  #1; if(q!==0) $fatal(1,"Reset must clear X state");\n  $display("FOUR_STATE_GATE PASS");\n  $display("NATIVE_CELL_GATE PASS");')
assert 'FOUR_STATE_GATE PASS' in bench
from ihp_zero_delay_aliases import adapt
adapted,aliases=adapt(lib.read_text())
model=out/'derived-zero-delay.v';model.write_text(adapted)
r={'source_head':os.environ['GITHUB_SHA'],'cvc_source':'1c5e043ec33ef6f1fdbf38565501c944893a83cf','library_sha256':sha(lib),'chip_accepted':False,'native_unmodified_model_compatible':False,'functional_aliases':aliases,'derived_model_sha256':sha(model),'scope':'Derived zero-delay functional model only. Original CVC/native model compatibility failed; no timing or SDF acceptance.','cases':[]}
def run(cmd,folder,name,timeout):
 start=time.monotonic()
 with (folder/(name+'.log')).open('w')as log:
  p=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 return dict(command=cmd,returncode=p.returncode,elapsed_s=time.monotonic()-start,log_sha256=sha(folder/(name+'.log')))
try:
 for engine in ['iverilog','cvc']:
  for fault in [False,True]:
   folder=out/(engine+('-mutant'if fault else'-positive'));folder.mkdir()
   src=folder/'probe.v';src.write_text(bench.replace('if(q!==1)', 'if(q!==0)')if fault else bench)
   exe=folder/'sim';cmd=([str(cvc),'-sv','+define+NSSOC_CVC_ZERO_DELAY','-o',str(exe),str(src),'-v',str(model)]if engine=='cvc'else['iverilog','-g2005-sv','-s','tb_native_cell_gate','-o',str(exe),str(src),str(lib)])
   item={'engine':engine,'mutation':fault,'bench_sha256':sha(src),'compile':run(cmd,folder,'compile',300)}
   if item['compile']['returncode']==0 and exe.is_file():
    item['run']=run([str(exe)]if engine=='cvc'else['vvp','-i',str(exe)],folder,'run',30)
    text=(folder/'run.log').read_text();item['passed']=item['run']['returncode']==0 and 'NATIVE_CELL_GATE PASS'in text and 'FOUR_STATE_GATE PASS'in text
    item['fault_detected']='Native'in text and 'failed'in text and not item['passed']
   else:item.update(passed=False,fault_detected=False)
   r['cases'].append(item);(out/'result.json').write_text(json.dumps(r,indent=2))
 r['passed']=len(r['cases'])==4 and all(x['fault_detected']if x['mutation']else x['passed']for x in r['cases'])
 assert sha(lib)==r['library_sha256'];assert r['passed'],'Native four-state compatibility is not established'
finally:
 r['library_unchanged']=sha(lib)==r['library_sha256'];r['cvc_binary_sha256']=sha(cvc)
 (out/'result.json').write_text(json.dumps(r,indent=2))
