"""Exact still-owned birth/group cleanup; no healthy elapsed-time policy."""
from pathlib import Path
import os,signal

def identity(pid):
 try:
  fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
 except FileNotFoundError:return None
 return dict(pid=pid,start_ticks=fields[19],process_group=int(fields[2]))

def free_floor(free,minimum=528*1024**2):
 if free<minimum:raise RuntimeError('Shared scratch floor breached')
 return free

class OwnedNative:
 def __init__(self,process):
  self.process=process
  self.boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  self.birth=identity(process.pid)
  assert self.birth is not None and self.birth['process_group']==process.pid,'Fresh owned native session required'
  self.cleanup=None
 def kill_and_reap(self):
  p=self.process
  # poll()/wait() may already have reaped it. Never signal that numeric group.
  if p.returncode is not None:
   self.cleanup=dict(status='ALREADY_REAPED_NO_SIGNAL',birth=self.birth,returncode=p.returncode)
   return self.cleanup
  current=identity(p.pid)
  boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  if boot!=self.boot_id or current!=self.birth:
   self.cleanup=dict(status='REFUSED_BIRTH_OR_GROUP_MISMATCH_NO_SIGNAL',expected=self.birth,current=current,boot_id=boot)
   raise RuntimeError('Native cleanup identity mismatch; signal refused')
  # This direct child has not been reaped. Even if it exits now, its zombie
  # retains the PID until our wait below, preventing PGID/PID reuse in this gap.
  try:os.killpg(self.birth['process_group'],signal.SIGKILL);sent=True
  except ProcessLookupError:sent=False
  code=p.wait()
  self.cleanup=dict(status='EXACT_OWNED_GROUP_KILLED_AND_REAPED',birth=self.birth,signal_sent=sent,returncode=code)
  return self.cleanup
