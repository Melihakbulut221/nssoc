from pathlib import Path
import os,sys,hashlib,json,shutil,resource,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'burst-baseline-diagnostic02';D.mkdir()
sys.path.insert(0,str(R/'scripts'));import characterize_pcie_clock_trim_stream_v2 as life
os.sched_setaffinity(0,{6})
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
import runpy
old=Path('/dev/shm/nssoc-integrity-v25-full-controls01/test_actual_pending_badblock_f0/fault_epochs')
api=runpy.run_path(str(R/'sw/tests/test_pcie_gen3_integrity_v25_block_burst.py'))
parent=runpy.run_path(str(api['PARENT']))
blocks,expected,packets=api['stimulus'](True)
raw=parent['bench'](blocks,expected,packets)
removed=[line for line in raw.splitlines(keepends=True) if ' reference(' in line or 'V23_FRAMER_PUBLIC_MITER' in line];assert len(removed)==2
raw=''.join(line for line in raw.splitlines(keepends=True) if line not in removed)
raw=raw.replace('reference.step','candidate.step').replace('reference.slice','candidate.slice').replace('reference.next_valid','candidate.next_valid')
marker='   if(framing_error_o || overflow_o || halted_o) $fatal(1,"V23_FRAMER_UNEXPECTED_FAULT");';assert raw.count(marker)==1
instrument='   if(candidate.fault_now || overflow_o || halted_o)\n    $display("BASELINE_DIAG cycle=%0d t=%0t ready=%b cap=%b bad=%b token=%b occupied=%0d wp=%0d rp=%0d retire=%b step=%b",cycle_no,$time,ready_i,candidate.ring_overflow_now,candidate.bad_block_now,candidate.token_failure,candidate.occupied,candidate.write_ptr,candidate.read_ptr,candidate.retire,candidate.step);\n'
(D/'tb.v').write_text(raw.replace(marker,instrument+marker))
dut=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v';shutil.copyfile(dut,D/dut.name)
def limits():resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def floor():assert shutil.disk_usage('/dev/shm').free>=528*1024**2
results=[]
with life.ProcessOwner(D/'owner.json') as owner:
 for label,cmd in [('compile',[shutil.which('iverilog'),'-g2012','-s','tb','-o',str(D/'sim.vvp'),str(D/'tb.v'),str(D/dut.name)]),('simulation',[shutil.which('vvp'),str(D/'sim.vvp')])]:
  floor();owner.check()
  with (D/(label+'.log')).open('x') as stream:
   p=owner.launch('native',cmd,stdout=stream,stderr=subprocess.STDOUT,preexec_fn=limits,env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')})
   while p.poll() is None:owner.check();floor();owner.cancelled.wait(.02)
   owner.check();code=owner.complete(p);floor();owner.check()
  results.append(dict(stage=label,returncode=code,command=cmd))
  if label=='compile':assert code==0
 owner.check()
owner.check()
(D/'result.json').write_text(json.dumps(dict(scope='Original V23 actual framer with identical 128-packet byte stream and original repeated ready pattern; independent byte scoreboard preserved; no equivalence/adoption claim',original_tb=pin(old/'tb.v'),original_dut=pin(dut),instrumented_tb=pin(D/'tb.v'),copied_dut=pin(D/dut.name),stages=results,outputs={p.name:pin(p) for p in D.iterdir() if p.is_file()}),indent=2)+'\n')
print((D/'simulation.log').read_text())
