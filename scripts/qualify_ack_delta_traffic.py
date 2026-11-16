import os,json,subprocess,hashlib,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('ack-delta-traffic');out.mkdir()
src=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
s=src.read_text()
base=Path('hw/soc/tb/ack_delta_original.v').read_text()
assert hashlib.sha256(base.encode()).hexdigest()=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
proof=json.loads(Path('ack-delta-proof/result.json').read_text())
assert proof['source_head']==os.environ['GITHUB_SHA']
assert proof['rtl_sha256']==hashlib.sha256(src.read_bytes()).hexdigest()
assert proof['status']=='PASS_24BIT_ARITHMETIC_EQUIVALENCE_WITH_MUTATION_NOT_CHIP_ACCEPTANCE'
# Assert the source substitution is the only change relative to the reference.
begin='    // BEGIN ACK_DELTA_GROUP_PREFIX'
end='    // END ACK_DELTA_GROUP_PREFIX'
assert s.count(begin)==s.count(end)==1
restored=s.split(begin)[0]+'    wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;'+s.split(end)[1]
assert restored==base
reference=re.sub(r'\bsoc_pcie_replay_tx\b','soc_pcie_replay_tx_ref',base)
reference=re.sub(r'\bsoc_pcie_stream_skid\b','soc_pcie_stream_skid_ref',reference)
(out/'candidate.v').write_text(s)
result=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
try:
 traffic=[]
 common=['SOC_PCIE_ACK_STALE_PREFIX','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_WRITE_PREDECODE','SOC_PCIE_REPLAY_EOP_CACHE','SOC_PCIE_REPLAY_CRC_SELECT']
 pre=''.join(chr(96)+'define '+n+'\n'for n in common)
 post=''.join(chr(96)+'undef '+n+'\n'for n in common)
 (out/'reference.v').write_text(pre+reference+'\n'+post)
 (out/'candidate.v').write_text(pre+(out/'candidate.v').read_text()+'\n'+post)
 bench=Path('hw/soc/tb/tb_pcie_replay_ahead.v').read_text()
 port='.clk_i(clk), .rst_ni(rst_ni), .link_up_i(link_up)'
 assert bench.count(port)==2
 bench=bench.replace(port,'.rst_copy_ni(rst_ni), '+port,1)
 (out/'traffic-bench.v').write_text(bench)
 for depth,size,timeout,seed in [(4,38,256,1),(4,38,256,2),(4,38,1024,3),(4,38,256,4),(2,22,128,5),(2,22,128,6)]:
  name=f'traffic-d{depth}-b{size}-t{timeout}-s{seed}';exe=out/(name+'.vvp')
  cmd=['iverilog','-g2012','-DCOSIM_RESET_COPIES','-s','tb_pcie_replay_ahead','-o',str(exe),f'-Ptb_pcie_replay_ahead.DEPTH={depth}',f'-Ptb_pcie_replay_ahead.MAX_BYTES={size}',f'-Ptb_pcie_replay_ahead.TIMEOUT_CYCLES={timeout}','hw/soc/rtl/pcie/soc_pcie_crc32_byte.v',str(out/'reference.v'),str(out/'candidate.v'),str(out/'traffic-bench.v')]
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
  (out/(name+'-compile.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
  p=subprocess.run(['vvp','-n',str(exe),f'+seed={seed}','+cycles=300000'],capture_output=True,text=True,timeout=600)
  text=p.stdout+p.stderr;(out/(name+'.log')).write_text(text)
  assert p.returncode==0 and re.search(r'^RESULT PASS',text,re.M) and not re.search(r'MISMATCH|FATAL|RESULT FAIL',text),text[-3000:]
  traffic.append(dict(depth=depth,max_bytes=size,timeout=timeout,seed=seed,cycles=300000,status='PASS',summary=[l for l in text.splitlines()if l.startswith(('SUMMARY','RESULT'))]))

 result.update(status='PASS_ACK_DELTA_ARITHMETIC_AND_SIX_REPLAY_TRAFFIC_CASES',rtl_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(base.encode()).hexdigest(),arithmetic_proof=proof,traffic=traffic,common_defines=common,scope='Same-cycle full replay output comparison, six configurations, 1.8M cycles. Not exhaustive sequential, arbitrary-X/Z, mapped timing or full PHY acceptance.')
except BaseException as e:
 result.update(status='FAIL',error=repr(e));raise
finally:
 (out/'result.json').write_text(json.dumps(result,indent=2))
