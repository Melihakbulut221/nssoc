# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual saved-byte equivalence and hostile saved-table controls; no native."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,os,resource,sys,types
from unittest.mock import patch
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
import numpy as np
from raw_table01 import open_table,file_pin,SSD_FLOOR
R=Path.cwd();B=Path(__file__).resolve().parent;F=B/'fixtures01';F.mkdir(exist_ok=False)
sys.path.insert(0,str(R/'scripts'));Q=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-quarterstep-20261006/characterize_quarterstep01.py'
spec=importlib.util.spec_from_file_location('saved_reader_reference',Q);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);m=module.core
checks=[];inputs={str(Q):file_pin(Q),str(B/'raw_table01.py'):file_pin(B/'raw_table01.py'),str(Path(__file__)):file_pin(Path(__file__))}
for label in ['wire','halfstep','quarterstep']:
 N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-'+label+'-06-01');r=json.loads((N/'result.json').read_text());path=N/'wave.raw.gz'
 for p in [N/'result.json',path]:inputs[str(p)]=file_pin(p)
 with gzip.open(path,'rb')as stream:header,meta=m.life.tiny.parse_header(stream,m.n.vectors(r['devices'],r['config']['extra_vectors']));body=stream.read()
 width=len(meta['columns'])*8;payload=body[:r['rows']*width];old=np.frombuffer(payload,'<f8').reshape(r['rows'],-1)
 columns=m.stream.previous.data_names(meta['columns'])
 assert hashlib.sha256(payload).hexdigest()==r['payload_sha256']
 before=set(F.iterdir())
 with open_table(path,rows=r['rows'],columns=columns,compressed_pin=file_pin(path),raw_sha256=r['raw_sha256'],payload_sha256=r['payload_sha256'],raw_bytes=r['raw_bytes'],scratch_directory=F,scratch_limit=1024**3)as table:
  assert table['header']==header and table['matrix'].flags.writeable is False
  for start in range(0,r['rows'],1024):assert np.array_equal(table['matrix'][start:start+1024],old[start:start+1024])
  data=dict(zip(columns,table['matrix'].T));contacts=[x for x in r['devices']if x['model']in('ptap1','ntap1')];other=[x for x in r['devices']if x not in contacts]
  safe=m.n.safety(data,other,r['config']['window_s']);assert safe['all_device_bounds']==r['safety']['all_device_bounds'][:424]
  assert safe['model_geometry_range_issues']==r['safety']['model_geometry_range_issues']
  for row,reported in zip(contacts,r['safety']['all_device_bounds'][424:]):
   v=[data['v('+x+')']if x!='0'else np.zeros(r['rows'])for x in row['nets']];actual=float(abs(v[0]-v[1]).max())
   assert row['path']==reported['path']and actual==reported['max_capture_terminal_difference']and actual/float(row['params']['r'])==reported['inferred_ohmic_peak_a']
  assert m.measurement(data,r['config'])==r['measurement']
  assert m.n.validate_time_grid(data['time'],34e-9,r['config']['step_s'])==r['time_grid']
  del data
 assert set(F.iterdir())==before
 checks.append(dict(name='complete_'+label+'_saved_equivalence',values=r['values'],rows=r['rows'],native_status=r['status'],all455_bounds_equal=True,all_measurements_equal=True,full_payload_bit_equal=True,anonymous_cleanup=True))
 del table,old,payload,body
header=b'Title: bounded fixture\nFlags: real\nNo. Variables: 2\nNo. Points: 0\nVariables:\n\t0\ttime\ttime\n\t1\tv(x)\tvoltage\nBinary:\n';payload=np.array([[0,0],[1e-9,1],[2e-9,2]],dtype='<f8').tobytes();trailer=b'3'
def fixture(name,h=header,p=payload,t=trailer):
 raw=h+p+t;path=F/(name+'.raw.gz');path.write_bytes(gzip.compress(raw,mtime=0));return path,dict(rows=3,columns=['time','v(x)'],compressed_pin=file_pin(path),raw_sha256=hashlib.sha256(raw).hexdigest(),payload_sha256=hashlib.sha256(p).hexdigest(),raw_bytes=len(raw),scratch_directory=F,scratch_limit=48)
def run_case(name,expected,alter=lambda kw:None,h=header,p=payload,t=trailer,free=None,raise_inside=False):
 path,kw=fixture(name,h,p,t);alter(kw);before=set(F.iterdir());error=None
 def use():
  with open_table(path,**kw)as result:
   if raise_inside:raise RuntimeError('consumer cancellation')
   assert result['matrix'].shape==(3,2)and not result['matrix'].flags.writeable
 try:
  if free is None:use()
  else:
   seq=iter(free)
   with patch('raw_table01.shutil.disk_usage',lambda _p:types.SimpleNamespace(free=next(seq))):use()
 except (AssertionError,RuntimeError)as e:error=str(e)
 assert error==expected,(name,error,expected)
 assert set(F.iterdir())==before,'anonymous temporary leaked'
 checks.append(dict(name=name,expected_diagnostic=expected,actual_diagnostic=error,anonymous_cleanup=True));inputs[str(path)]=file_pin(path)
run_case('small_positive',None)
run_case('wrong_compressed_pin','compressed input pin',lambda kw:kw['compressed_pin'].update(sha256='0'*64))
run_case('wrong_raw_digest','raw digest',lambda kw:kw.update(raw_sha256='0'*64))
run_case('wrong_payload_digest','payload digest',lambda kw:kw.update(payload_sha256='0'*64))
run_case('wrong_raw_count','raw byte count',lambda kw:kw.update(raw_bytes=kw['raw_bytes']+1))
run_case('wrong_column_labels','column labels',lambda kw:kw.update(columns=['time','v(y)']))
run_case('wrong_column_index','column index',h=header.replace(b'\t1\tv(x)',b'\t3\tv(x)'))
run_case('wrong_trailer','exact native trailer',t=b'4')
run_case('extra_trailer','exact native trailer',t=b'3extra')
run_case('short_payload','float alignment',p=payload[:-8])
bad=np.array([[0,0],[1e-9,float('nan')],[2e-9,2]],dtype='<f8').tobytes();run_case('nonfinite_payload','nonfinite payload',p=bad)
run_case('scratch_cap','scratch cap',lambda kw:kw.update(scratch_limit=47))
run_case('SSD_entry_floor','SSD entry floor',free=[SSD_FLOOR+47])
run_case('SSD_continuous_floor','SSD continuous floor',free=[SSD_FLOOR+48,SSD_FLOOR-1])
run_case('SSD_terminal_floor','SSD terminal floor',free=[SSD_FLOOR+48,SSD_FLOOR,SSD_FLOOR-1])
run_case('SSD_post_context_floor','SSD post-context floor',free=[SSD_FLOOR+48,SSD_FLOOR,SSD_FLOOR,SSD_FLOOR-1])
run_case('consumer_exception_cleanup','consumer cancellation',raise_inside=True)
r=dict(status='PASS_SAVED_STREAMING_READER_EQUIVALENCE_AND_CORRUPTION_CONTROLS',checks=checks,inputs=inputs,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,source=inputs[str(B/'raw_table01.py')],scope='Existing5/2.5/1.25ps full arrays and original455 safety/measurement/time-grid functions exactly equal; seventeen small saved-file cases exercise actual bounded reader. No source/native capture modification and no simulator executed. Reference baseline materialization is used only in this bounded test; new reader itself uses anonymous SSD mapping.')
(B/'controls01.json').write_text(json.dumps(r,indent=2)+'\n');print(len(checks),file_pin(B/'controls01.json'))
