from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET,datetime,re
B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v18-max4118-01/direct/test_actual_wide_rx_full_posit0/capture');M=D.parents[2]/'miter/test_v11_v18_cycle_exact_all_p0/capture'
def pin(p):
 p=Path(p);return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def ident(pid,start):
 p=Path('/proc')/str(pid);s=(p/'stat').read_text().split(') ',1)[1].split();assert s[19]==str(start);return dict(pid=pid,start_ticks=s[19],state=s[0],ppid=int(s[1]),process_group=int(s[2]),command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(),cpu_allowed=next(x for x in(p/'status').read_text().splitlines()if x.startswith('Cpus_allowed_list:')))
j=json.loads((D/'result.json').read_text());assert j['tests']==dict(passed=13,failed=0,skipped=0);assert j['max_encoded_bytes']==4118 and j['minimum_packet_ring_dwords']==2048
for p,x in j['inputs'].items():assert pin(p)==x
for n,x in j['outputs'].items():assert pin(D/n)==x
cases=ET.parse(D/'results.xml').getroot().findall('.//testcase');assert len(cases)==13 and all(not list(x)for x in cases)
log=(D/'simulation.log').read_text();assert 'TESTS=13 PASS=13 FAIL=0 SKIP=0' in log
# Source-only count: 1024 20-byte wire TLPs +32 tail blocks;4096 8-byte wire DLLPs +32 tail blocks.
# Both are already multiples of1024 bytes, and each64B four-lane block is130bits/lane, consumed32bits/cycle.
cycles=(1024*20+32*64)//64*130//32+(4096*8+32*64)//64*130//32+4
assert cycles==3644 and cycles*4==14576
mlog=(M/'simulation.log').read_text();assert '14576.00ns' in mlog and 'sustained_minimum_packets_exceed_every_buffer passed' in mlog
r={'status':'DIRECT_MAX4118_13_CASES_PASS_MITER_FIRST_CASE_PASS_REMAINDER_RUNNING','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'direct':{'result':pin(D/'result.json'),'inputs_rehashed':j['inputs'],'outputs_rehashed':j['outputs'],'actual_cases':[x.attrib for x in cases],'first_case_expected_cycles':cycles,'first_case_simulated_ns':14576,'first_case_real_seconds':6639.03,'total_simulated_ns':124352.01,'total_real_seconds':18538.02,'diagnosis':'Actual finite simulation completed; prior silent first-case window was not a demonstrated stall. Testbench logs testcase boundaries only.','original_orphan_parent_wait_status':None,'native_helper_make_returncode':j['commands'][0]['returncode']},'current_miter_observation':{'log_snapshot':mlog,'log_pin_at_read':{'bytes':len(mlog.encode()),'sha256':hashlib.sha256(mlog.encode()).hexdigest()},'completed_cases_observed':1,'next_case':'maximum_zero_packets_cross_blocks_and_verdict_wrap','final_result_exists':(M/'result.json').exists()},'live_identities':[ident(105584,1386708),ident(108156,1429254),ident(171610,3105790),ident(171721,3106952)],'no_new_native_no_signals_no_duplicate':True,'limitations':['Miter remainder is not yet PASS.','Functional simulation is not mapped frequency, final timing, full PHY or production acceptance.'],'method':pin(__file__)}
q=B/'progress-review-20261006.json';q.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(q)))
