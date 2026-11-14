"""Reproduce delayed VmRSS observation; preserve fail-closed monitor semantics."""
import contextlib,json,pathlib,os
import physical_memory_sampler as m
assert os.environ.get('GITHUB_ACTIONS')=='true'
assert m.ATTEMPTS==3 and m.INTERVAL==.02 and m.RESAMPLE_WINDOW==1.0
class Clock:
 def __init__(self):self.t=0.
 def __call__(self):return self.t
 def pause(self,value):self.t+=value
class Access:
 def __init__(self,clock,mode):self.clock=clock;self.mode=mode;self.attempt=0;self.enumeration_disappearances=[]
 def meminfo(self,path):
  self.attempt+=1;self.clock.pause(1.1 if self.mode=='deadline'else .005)
  return 'MemAvailable: 14903148 kB\n'
 def start(self):return 101 if self.mode=='reuse'and self.attempt>1 else 100
 def members(self,pgid):return [dict(pid=42,pgrp=42,starttime=self.start(),state='S')]
 @contextlib.contextmanager
 def hold(self,pid):
  assert pid==42
  def read(name):
   if name=='stat':return '42 (worker) '+' '.join(['S','1','42']+['0']*16+[str(self.start())])
   assert name=='status'
   missing=self.mode=='persistent'or(self.attempt==1 and self.mode in ['recover','reuse'])
   rss=''if missing else 'VmRSS: 999 '+('MB'if self.mode=='units'else'kB')+'\n'
   return 'Pid: 42\nState: S (sleeping)\n'+rss
  yield read
checks=[]
def execute(mode,window=1.0):
 c=Clock();access=Access(c,mode);events=[];old=m.RESAMPLE_WINDOW;m.RESAMPLE_WINDOW=window
 def emit(name,**kw):
  events.append((name,kw))
  if mode=='recover'and name=='memory_counter_resample_attempt':c.pause(.279)
 try:return m.snapshot(42,access=access,clock=c,pause=c.pause,emit=emit),events
 finally:m.RESAMPLE_WINDOW=old
def rejected(label,mode,fragment,window=1.0):
 try:execute(mode,window)
 except m.CounterError as e:assert fragment in str(e),(label,str(e));checks.append(label)
 else:raise AssertionError('Unexpected acceptance: '+label)
rejected('original100ms_reproduces_observed_failure','recover','Missing-counter resampling window exhausted',.1)
r,events=execute('recover');assert r['sampling_attempts']==2 and r['group_rss_kib']==999 and r['members'][0]['rss_kib']==999 and .279<r['sampling_elapsed_seconds']<1.0
assert len(r['resampling_evidence'])==2 and events;checks.append('fresh_counter_after279ms_logging_delay')
rejected('persistent_missing_counter_is_not_zero_or_stale','persistent','Persistent unavailable live VmRSS')
rejected('one_second_total_deadline_still_enforced','deadline','Total memory snapshot bounded window exhausted')
rejected('PID_reuse_rejected','reuse','PID identity changed across resamples')
rejected('invalid_RSS_units_rejected','units','Malformed VmRSS counter or units')
r,_=execute('normal');assert r['sampling_attempts']==1 and r['group_rss_kib']==999;checks.append('ordinary_fresh_sample')
pathlib.Path('memory-sampler-controls.json').write_text(json.dumps({'status':'PASS','checks':checks,'attempts':m.ATTEMPTS,'interval_seconds':m.INTERVAL,'snapshot_budget_seconds':m.RESAMPLE_WINDOW,'resource_limits_changed':False,'physical_gates_changed':False},indent=2))
print('MEMORY_SAMPLER_CONTROLS_PASS',len(checks))
