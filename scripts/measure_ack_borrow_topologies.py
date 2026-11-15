import os,json,subprocess,hashlib,base64,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT=Path('out-ack-borrow-map');OUT.mkdir()
source=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
text=source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='1983ad5eb2b05c4e99d72eb2be736c8ec63af98681b73cb5f4794e0a73b65cb6'
segment=text.split('// BEGIN ACK_STALE_PREFIX',1)[1].split('// END ACK_STALE_PREFIX',1)[0]
assert "wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;"in text
assert "wire current_ack_allowed=ack_delta==0 || (ack_delta<=12'(sent_count) && ack_delta!=0);"in text
header="module ack(input [11:0] ack_sequence_i,acknowledged_sequence_o,input [2:0] sent_count,output [11:0] delta_o,output allowed_o,stale_o);\nwire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;\nwire current_ack_allowed=ack_delta==0 || (ack_delta<=12'(sent_count) && ack_delta!=0);\nassign delta_o=ack_delta;\nassign allowed_o=current_ack_allowed;\n"
variants={}
variants['original']='wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;'
variants['group3']=text.split('// BEGIN ACK_DELTA_PREFIX',1)[1].split('// END ACK_DELTA_PREFIX',1)[0]+'\nwire [11:0] ack_delta=ack_delta_prefix;'
base_logic='wire [11:0] g=(~ack_sequence_i)&acknowledged_sequence_o;\nwire [11:0] p=~(ack_sequence_i^acknowledged_sequence_o);\n'
terms=[]
for i in range(1,12):
 items=[]
 for j in range(i):items.append('('+'&'.join(['g['+str(j)+']']+['p['+str(k)+']'for k in range(j+1,i)])+')')
 terms.append('assign b['+str(i)+']='+' | '.join(items)+';')
variants['flat_borrow']=base_logic+'wire [11:0] b; assign b[0]=0;\n'+'\n'.join(terms)+'\nwire [11:0] ack_delta=ack_sequence_i^acknowledged_sequence_o^b;'
k=base_logic+'wire [11:0] g0=g,p0=p;\n'
for level,distance in enumerate([1,2,4,8],1):
 k+='wire [11:0] g'+str(level)+',p'+str(level)+';\n'
 for i in range(12):
  prev=str(level-1);now=str(level)
  rhs='g'+prev+'['+str(i)+']';prhs='p'+prev+'['+str(i)+']'
  if i>=distance:
   rhs+=' | (p'+prev+'['+str(i)+'] & g'+prev+'['+str(i-distance)+'])'
   prhs+=' & p'+prev+'['+str(i-distance)+']'
  k+='assign g'+now+'['+str(i)+']='+rhs+'; assign p'+now+'['+str(i)+']='+prhs+';\n'
variants['prefix_tree']=k+'wire [11:0] ack_delta=ack_sequence_i^acknowledged_sequence_o^{g4[10:0],1\'b0};'
formal=[]
for mode,delta in variants.items():
 actual_header=header.replace('wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;',delta)
 body=segment+'\nassign stale_o=ack_stale_prefix;\n'
 (OUT/(mode+'.sv')).write_text(actual_header+body+'endmodule\n')
 proof='module proof(input [11:0] ack_sequence_i,acknowledged_sequence_o,output ok);\n'+delta+'\nwire [11:0] expected=ack_sequence_i-acknowledged_sequence_o; assign ok=ack_delta==expected; endmodule\n'
 v=OUT/(mode+'-proof.v');v.write_text(proof)
 ys=OUT/(mode+'-proof.ys');ys.write_text('read_verilog '+str(v)+'\nprep -top proof\nflatten\nsat -verify -prove ok 1 -show-inputs\n')
 r=subprocess.run(['yosys','-s',str(ys)],capture_output=True,text=True,timeout=180);log=r.stdout+r.stderr;(OUT/(mode+'-proof.log')).write_text(log)
 assert r.returncode==0 and 'SUCCESS!'in log,log[-3000:]
 formal.append(dict(mode=mode,all24bit_pairs_equivalent=True))
(OUT/'constraints.txt').write_text('set_driving_cell sg13g2_buf_2\nset_load 10.0\n')
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
base='repos/IHP-GmbH/IHP-Open-PDK/'
def api(s):return json.loads(subprocess.check_output(['gh','api',base+s]))
results=[];libs={}
try:
 entries=api('contents/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib?ref='+PDK)
 for corner in ['slow_1p08V_125C','typ_1p20V_25C','fast_1p32V_m40C']:
  name='sg13g2_stdcell_'+corner+'.lib';e=next(x for x in entries if x['name']==name)
  raw=base64.b64decode(api('git/blobs/'+e['sha'])['content'])
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha']
  lib=OUT/name;lib.write_bytes(raw);libs[corner]=dict(git_blob=e['sha'],sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
  for mode in variants:
   stem=OUT/(corner+'-'+mode)
   ys=Path(str(stem)+'.ys')
   ys.write_text(f'read_liberty -lib {lib}\nread_verilog -sv {OUT/(mode+".sv")}\nsynth -top ack -noabc\nabc -liberty {lib} -constr {OUT/"constraints.txt"}\nclean\nstat -liberty {lib}\nwrite_verilog -noattr {stem}.v\nwrite_json {stem}.json\n')
   p=subprocess.run(['yosys','-s',str(ys)],capture_output=True,text=True,timeout=180)
   log=p.stdout+p.stderr;Path(str(stem)+'.log').write_text(log);assert p.returncode==0,log[-4000:]
   # Keep original ABC native timing lines, not inferred RTL operator counts.
   measures=[x for x in log.splitlines()if any(t in x for t in ['Delay =','delay =','Area =','area =','Chip area','ABC RESULTS'])]
   assert any('Delay ='in x or 'delay ='in x for x in measures),'No native ABC delay reported'
   results.append(dict(corner=corner,mode=mode,native_measurements=measures,mapped_netlist_sha256=hashlib.sha256(Path(str(stem)+'.v').read_bytes()).hexdigest()))
 result=dict(status='MEASURED_ACK_CONE_NOT_CHIP_ACCEPTANCE',pdk=PDK,libraries=libs,source_head=os.environ['GITHUB_SHA'],rtl_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),measurements=results,formal=formal,constraints='Same buf2 input driver and ABC set_load10fF for every output. Joint delta[11:0],allowed,stale cone keeps sharing visible. DEPTH4 sent_count3bits.',scope='ABC mapped combinational delay estimate only. No routed RC, clock, sequential timing, or full-chip/fullPHY acceptance.',accepted=False,yosys=subprocess.check_output(['yosys','-V'],text=True).strip())
except BaseException as e:
 result=dict(status='FAIL',error=repr(e),libraries=libs,measurements=results,accepted=False);raise
finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
