from pathlib import Path
import os,sys,hashlib,json,shutil,resource,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'component-diagnostic01';D.mkdir()
sys.path.insert(0,str(R/'scripts'));import characterize_pcie_clock_trim_stream_v2 as life
os.sched_setaffinity(0,{6})
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
old=Path('/dev/shm/nssoc-integrity-v25-full-controls01/test_actual_command_temporal_r0')
raw=(old/'command.v').read_text()
marker=' $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_WRITES");'
assert raw.count(marker)==1
changed=raw.replace(marker, ' $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_WRITES kind=%0d slot=%0d slotbefore=%h slotafter=%h cachebefore=%b cacheafter=%b refslot=%h refcache=%b rst=%b enabled=%b step=%b valid=%b commit=%h",t,i,held_slot[i],{dut.slot_data[i],dut.slot_keep[i],dut.slot_sop[i],dut.slot_eop[i],dut.slot_dllp[i],dut.slot_sequence[i],dut.slot_tag[i]},held_cache[i],dut.slot_verdict[i],{ref_dut.slot_data[i],ref_dut.slot_keep[i],ref_dut.slot_sop[i],ref_dut.slot_eop[i],ref_dut.slot_dllp[i],ref_dut.slot_sequence[i],ref_dut.slot_tag[i]},ref_dut.slot_verdict[i],rst_ni,enabled,step,dut.command_valid,dut.visible_commit_ptr);')
mark=' reg [4:0] held_commit;'
assert changed.count(mark)==1
instrument=r'''
 always @(negedge rst_ni) begin
  $display("ASYNC_ACTIVE time=%0t kind=%0d rst=%b enabled=%b step=%b drive=%b valid=%b slot8=%h cache8=%b refslot8=%h refcache8=%b",$time,t,rst_ni,enabled,step,drive,dut.command_valid,dut.slot_data[8],dut.slot_verdict[8],ref_dut.slot_data[8],ref_dut.slot_verdict[8]);
  $strobe("ASYNC_NBA time=%0t kind=%0d rst=%b enabled=%b step=%b drive=%b valid=%b slot8=%h cache8=%b refslot8=%h refcache8=%b",$time,t,rst_ni,enabled,step,drive,dut.command_valid,dut.slot_data[8],dut.slot_verdict[8],ref_dut.slot_data[8],ref_dut.slot_verdict[8]);
 end
'''
changed=changed.replace(mark,mark+instrument)
(D/'command.v').write_text(changed)
def limits():resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def floor():assert shutil.disk_usage('/dev/shm').free>=528*1024**2
results=[]
with life.ProcessOwner(D/'owner.json') as owner:
 for label,cmd in [('compile',[shutil.which('iverilog'),'-g2012','-s','tb','-o',str(D/'sim.vvp'),str(D/'command.v')]),('simulation',[shutil.which('vvp'),str(D/'sim.vvp')])]:
  floor();owner.check()
  with (D/(label+'.log')).open('x') as stream:
   p=owner.launch('native',cmd,stdout=stream,stderr=subprocess.STDOUT,preexec_fn=limits,env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')})
   while p.poll() is None:owner.check();floor();owner.cancelled.wait(.02)
   owner.check();code=owner.complete(p);floor();owner.check()
  results.append(dict(stage=label,returncode=code,command=cmd))
  if label=='compile':assert code==0
 owner.check()
owner.check()
(D/'result.json').write_text(json.dumps(dict(scope='Exact unchanged failed stimulus and DUT; additive display only; diagnostic not positive acceptance',original_hdl=pin(old/'command.v'),instrumented_hdl=pin(D/'command.v'),stages=results,outputs={p.name:pin(p) for p in D.iterdir() if p.is_file()}),indent=2)+'\n')
print((D/'simulation.log').read_text())
