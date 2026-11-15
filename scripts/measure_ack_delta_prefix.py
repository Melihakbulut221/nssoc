import os,json,subprocess,hashlib,base64,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT=Path('out-ack-delta-map');OUT.mkdir()
source=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
text=source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='1983ad5eb2b05c4e99d72eb2be736c8ec63af98681b73cb5f4794e0a73b65cb6'
segment=text.split('// BEGIN ACK_STALE_PREFIX',1)[1].split('// END ACK_STALE_PREFIX',1)[0]
assert "wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;"in text
assert "wire current_ack_allowed=ack_delta==0 || (ack_delta<=12'(sent_count) && ack_delta!=0);"in text
header="module ack(input [11:0] ack_sequence_i,acknowledged_sequence_o,input [2:0] sent_count,output [11:0] delta_o,output allowed_o,stale_o);\nwire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;\nwire current_ack_allowed=ack_delta==0 || (ack_delta<=12'(sent_count) && ack_delta!=0);\nassign delta_o=ack_delta;\nassign allowed_o=current_ack_allowed;\n"
for mode in ['reference','stale_only','candidate']:
 body=segment+'\nassign stale_o=ack_stale_prefix;\n'if mode!='reference'else"assign stale_o=ack_delta>12'd2048;\n"
 delta=text.split('// BEGIN ACK_DELTA_PREFIX',1)[1].split('// END ACK_DELTA_PREFIX',1)[0]
 actual_header=header.replace('wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;',delta+'\nwire [11:0] ack_delta=ack_delta_prefix;') if mode=='candidate'else header
 (OUT/(mode+'.sv')).write_text(actual_header+body+'endmodule\n')
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
  for mode in ['reference','stale_only','candidate']:
   stem=OUT/(corner+'-'+mode)
   ys=Path(str(stem)+'.ys')
   ys.write_text(f'read_liberty -lib {lib}\nread_verilog -sv {OUT/(mode+".sv")}\nsynth -top ack -noabc\nabc -liberty {lib} -constr {OUT/"constraints.txt"}\nclean\nstat -liberty {lib}\nwrite_verilog -noattr {stem}.v\nwrite_json {stem}.json\n')
   p=subprocess.run(['yosys','-s',str(ys)],capture_output=True,text=True,timeout=180)
   log=p.stdout+p.stderr;Path(str(stem)+'.log').write_text(log);assert p.returncode==0,log[-4000:]
   # Keep original ABC native timing lines, not inferred RTL operator counts.
   measures=[x for x in log.splitlines()if any(t in x for t in ['Delay =','delay =','Area =','area =','Chip area','ABC RESULTS'])]
   assert any('Delay ='in x or 'delay ='in x for x in measures),'No native ABC delay reported'
   results.append(dict(corner=corner,mode=mode,native_measurements=measures,mapped_netlist_sha256=hashlib.sha256(Path(str(stem)+'.v').read_bytes()).hexdigest()))
 result=dict(status='MEASURED_ACK_CONE_NOT_CHIP_ACCEPTANCE',pdk=PDK,libraries=libs,source_head=os.environ['GITHUB_SHA'],rtl_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),measurements=results,constraints='Same buf2 input driver and ABC set_load10fF for every output. Joint delta[11:0],allowed,stale cone keeps sharing visible. DEPTH4 sent_count3bits.',scope='ABC mapped combinational delay estimate only. No routed RC, clock, sequential timing, or full-chip/fullPHY acceptance.',accepted=False,yosys=subprocess.check_output(['yosys','-V'],text=True).strip())
except BaseException as e:
 result=dict(status='FAIL',error=repr(e),libraries=libs,measurements=results,accepted=False);raise
finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
