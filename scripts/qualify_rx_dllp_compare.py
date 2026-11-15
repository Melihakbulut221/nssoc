import os,json,subprocess,hashlib,base64,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT=Path('out-rx-dllp-compare');OUT.mkdir()
source=Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v');text=source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest()=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
results=[];formal=[];libs={}
def execute(name,script):
 ys=OUT/(name+'.ys');ys.write_text(script)
 p=subprocess.run(['yosys','-s',str(ys)],capture_output=True,text=True,timeout=180)
 log=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(log)
 return p,log
try:
 for width in [1,2,3,4,5,6,7,8,9,10,12,16,24,32]:
  header='module proof(input ['+str(width-1)+':0] output_index,head_last,input [2:0] dllp_length,input select_dllp,output ok); localparam CW='+str(width)+';\n'
  original="wire reference=select_dllp ? output_index+1'b1==CW'(dllp_length) : output_index==head_last;\n"
  candidate="wire [CW-1:0] last=CW'(dllp_length)-CW'(1); wire candidate=(CW<3) ? reference : (select_dllp ? output_index==last : output_index==head_last);\n"
  for mutant in [False,True]if width>3 else[False]:
   name='width'+str(width)+('-mutant'if mutant else'');v=OUT/(name+'.sv')
   body=candidate.replace("CW'(dllp_length)-CW'(1)","CW'(3'(dllp_length-1'b1))")if mutant else candidate
   v.write_text(header+original+body+'assign ok=reference==candidate; endmodule\n')
   p,log=execute(name,'read_verilog -sv '+str(v)+'\nprep -top proof\nflatten\nsat -verify -prove ok 1 -show-inputs\n')
   if mutant:assert p.returncode!=0 and 'proof did fail'in log,log[-3000:]
   else:assert (p.returncode==0 and 'SUCCESS!'in log)or(p.returncode!=0 and 'proof did fail'in log),log[-3000:]
   formal.append(dict(width=width,mutant=mutant,status='REJECTED_MUTANT'if mutant else('PASS'if p.returncode==0 else'NOT_EQUIVALENT')))
 assert all(x['status']!='NOT_EQUIVALENT'for x in formal),formal
 (OUT/'constraints.txt').write_text('set_driving_cell sg13g2_buf_2\nset_load 10.0\n')
 PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c';repo='repos/IHP-GmbH/IHP-Open-PDK/'
 def api(s):return json.loads(subprocess.check_output(['gh','api',repo+s]))
 entries=api('contents/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib?ref='+PDK)
 for corner in ['slow_1p08V_125C','typ_1p20V_25C','fast_1p32V_m40C']:
  name='sg13g2_stdcell_'+corner+'.lib';e=next(x for x in entries if x['name']==name);raw=base64.b64decode(api('git/blobs/'+e['sha'])['content'])
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha']
  lib=OUT/name;lib.write_bytes(raw);libs[corner]=dict(git_blob=e['sha'],sha256=hashlib.sha256(raw).hexdigest())
  for width in [6,8,10]:
   for mode in ['reference','candidate']:
    stem=corner+'-w'+str(width)+'-'+mode;v=OUT/(stem+'.sv')
    header='module eop(input ['+str(width-1)+':0] output_index,head_last,input [2:0] dllp_length,input select_dllp,output out_eop_o); localparam CW='+str(width)+';\n'
    body="assign out_eop_o=select_dllp ? output_index+1'b1==CW'(dllp_length) : output_index==head_last;"if mode=='reference'else text.split(chr(96)+'ifdef SOC_PCIE_RX_DLLP_LAST_COMPARE',1)[1].split(chr(96)+'else',1)[0]
    v.write_text(header+body+'\nendmodule\n')
    p,log=execute(stem,f'read_liberty -lib {lib}\nread_verilog -sv {v}\nsynth -top eop -noabc\nabc -liberty {lib} -constr {OUT/"constraints.txt"}\nclean\nstat -liberty {lib}\nwrite_verilog -noattr {OUT/stem}.v\n')
    assert p.returncode==0,log[-3000:]
    lines=[l for l in log.splitlines()if 'Delay ='in l or'Chip area'in l];assert any('Delay ='in l for l in lines)
    results.append(dict(corner=corner,width=width,mode=mode,native_measurements=lines))
 per_input=[]
 sta_version=subprocess.run(['sta','-version'],capture_output=True,text=True,check=True).stdout.strip()
 for row in results:
  corner=row['corner'];width=row['width'];mode=row['mode'];stem=corner+'-w'+str(width)+'-'+mode
  lib=OUT/('sg13g2_stdcell_'+corner+'.lib')
  pins=[f'output_index[{i}]'for i in range(width)]+[f'head_last[{i}]'for i in range(width)]+[f'dllp_length[{i}]'for i in range(3)]+['select_dllp']
  script=[f'read_liberty {lib}',f'read_verilog {OUT/stem}.v','link_design eop','create_clock -name virtual -period 10','set_input_delay 0 -clock virtual [all_inputs]','set_output_delay 0 -clock virtual [all_outputs]','set_driving_cell -lib_cell sg13g2_buf_2 -pin X [all_inputs]','set_load 0.01 [all_outputs]']
  for idx,pin in enumerate(pins):
   script += [f'puts "INPUT_BEGIN {idx}"',f'report_checks -from [get_ports {{{pin}}}] -to [all_outputs] -path_delay max -format full_clock_expanded -digits 9',f'puts "INPUT_END {idx}"']
  script += ['exit']
  tcl=OUT/(stem+'-input.tcl');tcl.write_text('\n'.join(script)+'\n')
  proc=subprocess.run(['sta','-exit',str(tcl)],capture_output=True,text=True,timeout=180)
  log=proc.stdout+proc.stderr;(OUT/(stem+'-input.log')).write_text(log)
  assert proc.returncode==0 and not re.search(r'(?mi)^Error',log),log[-3000:]
  measurements=[]
  for idx,pin in enumerate(pins):
   match=re.search(r'INPUT_BEGIN '+str(idx)+r'\n(.*?)INPUT_END '+str(idx)+r'\b',log,re.S);assert match,(stem,idx)
   arrivals=re.findall(r'([-+\d.eE]+)\s+data arrival time',match[1]);assert arrivals,(stem,pin,match[1])
   measurements.append(dict(input=pin,arrival_ns=max(map(float,arrivals))))
  per_input.append(dict(corner=corner,width=width,mode=mode,inputs=measurements))
 (OUT/'per-input-sta.json').write_text(json.dumps(dict(status='ISOLATED_INPUT_PATHS_NOT_CHIP_ACCEPTANCE',sta_version=sta_version,source_head=os.environ['GITHUB_SHA'],constraints=dict(virtual_clock_ns=10,io_delay_ns=0,output_load_pf=.01,driver='sg13g2_buf_2'),measurements=per_input,accepted=False),indent=2)+'\n')
 r=dict(status='EQUIVALENCE_AND_MAPPED_EOP_CONE_ONLY',source_head=os.environ['GITHUB_SHA'],rtl_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),formal=formal,measurements=results,libraries=libs,accepted=False,scope='Binary combinational substitution only; fourteen CW values (original expression retained below3) including zero-length modulo wrap; wholemodule traffic/mappedboot/physical timing/fullPHY not accepted.')
except BaseException as e:r=dict(status='FAIL',error=repr(e),formal=formal,measurements=results,accepted=False);raise
finally:(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
