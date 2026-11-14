#!/usr/bin/env python3
"""Read retained placed ODBs; report exact write-register paths without replacing placement."""
import pathlib,subprocess,json,hashlib,zipfile,os,re
P=pathlib.Path;out=P('out');native=out/'native';native.mkdir(parents=True)
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha('placement-native.zip')=='d55d22b5617fb2d693985c1cf2dec9616dbbb1f50a0f555ee9d640844eca1611'
with zipfile.ZipFile('placement-native.zip') as z:
 for n in z.namelist():
  p=P(n);assert not p.is_absolute() and '..' not in p.parts
  if n.endswith('/'):continue
  target=native/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(n))
app=P('/mnt/s/librelane.AppImage');assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
report={'source_run':43616617171,'source_native_artifact':14122337899,'scope':'Read-only exact saved isolated placement, same original constraints and estimated RC. Target paths begin at the nine original or 26 predecoded write-register clock pins. No new placement, routing, CTS or full-chip timing acceptance.','cases':{},'timing_accepted':False}
for label,expected in [('baseline',9),('predecode',26)]:
 original=(native/label/'place.tcl').read_text();prefix=original.split('initialize_floorplan ',1)[0]
 for stage in ['placed','electrical_repair']:
  odb=native/label/(stage+'.odb');before=sha(odb);folder=out/(label+'-'+stage);folder.mkdir()
  prefix_lines=[line for line in prefix.splitlines() if not line.startswith(('read_lef ','link_design '))]
  prefix_lines=[('read_db '+str(odb)) if line.startswith('read_verilog ') else line for line in prefix_lines]
  tcl='\n'.join(prefix_lines)+'\n'+f"""foreach {{l r c}} {{Metal2 2.53519E-03 1.69121E-04 Metal3 1.54329E-03 1.82832E-04 Metal4 6.31424E-04 1.66454E-04 Metal5 6.84051E-04 8.57431E-05}} {{set_layer_rc -layer $l -resistance $r -capacitance $c}}
set_wire_rc -signal -layer Metal3
set_wire_rc -clock -layer Metal4
estimate_parasitics -placement
set froms {{}}
set fp [open {folder}/write-sources.tsv w]
foreach net [get_nets -quiet {{write_valid write_address* write_group* write_low*}}] {{
 foreach pin [get_pins -of_objects $net] {{
  if {{[get_property $pin direction] ne "output"}} {{continue}}
  set cell [get_cells -of_objects $pin]
  set name [get_full_name $cell]
  set clock [get_pins -quiet "$name/CLK"]
  if {{[llength $clock] != 1}} {{error "Write-register net is not directly driven by a clocked register: [get_full_name $net] $name"}}
  lappend froms [get_full_name $clock]
  puts $fp "[get_full_name $net]\t[get_full_name $pin]\t[get_full_name $clock]"
 }}
}}
close $fp
set froms [lsort -unique $froms]
if {{[llength $froms] != {expected}}} {{error "Wrong write-register source count [llength $froms], expected {expected}"}}
foreach c {{slow typ fast}} {{
 report_checks -corner $c -path_delay max -from [get_pins $froms] -to [all_registers -data_pins] -group_path_count 40 -fields {{slew cap fanout}} -digits 6 > {folder}/$c-max.rpt
 report_checks -corner $c -path_delay min -from [get_pins $froms] -to [all_registers -data_pins] -group_path_count 40 -fields {{slew cap fanout}} -digits 6 > {folder}/$c-min.rpt
}}
puts NSSOC_EXACT_WRITE_PATHS_REPORTED_NO_PLACEMENT_CHANGED
"""
  script=folder/'read.tcl';script.write_text(tcl);env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
  with (folder/'native.log').open('w') as log:r=subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=300)
  assert r.returncode==0 and 'NSSOC_EXACT_WRITE_PATHS_REPORTED_NO_PLACEMENT_CHANGED' in (folder/'native.log').read_text(),folder
  assert sha(odb)==before
  rows={}
  for path in folder.glob('*.rpt'):
   slacks=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',path.read_text());assert slacks,path
   rows[path.name]={'worst_slack_ns':min(map(float,slacks)),'report_sha256':sha(path)}
  assert len(rows)==6
  report['cases'][label+'-'+stage]={'odb_sha256':before,'source_register_count':expected,'source_pins_tsv':(folder/'write-sources.tsv').read_text(),'timing':rows}
  (out/'write-paths.json').write_text(json.dumps(report,indent=2)+'\n')
report['status']='COMPLETE_READ_ONLY_TARGETED_WRITE_PATH_SCREEN';(out/'write-paths.json').write_text(json.dumps(report,indent=2)+'\n')
