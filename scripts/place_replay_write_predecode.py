#!/usr/bin/env python3
"""Same-area replay placement comparison; ideal clocks and estimated RC only."""
import pathlib,subprocess,json,base64,hashlib,zipfile,os,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);native=out/'native';native.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
archive=P('mapping-native.zip');assert sha(archive)=='0e5355f3d4b464f6140577ae29150b1896515f1272d5446bce2f763e26b8698e'
with zipfile.ZipFile(archive) as z:
 for n in z.namelist():
  assert P(n).name==n and not n.endswith('/'),n
  (native/n).write_bytes(z.read(n))
assert sha(native/'baseline.v')=='94d9fdf2d76a62596c71a62683133d35cac34d33baa7616fd4251957646c55e7'
assert sha(native/'predecode.v')=='16a2ac7af7af967acd65dab9b1e09247c061fb2de4de5e0c8dd2c554bc0d2e3d'
specs=[('tech.lef','0b3558d0277a80e6ca91bd8fd6b82e610f416aa9',None),('cells.lef','4dd096a420edb5c52575e46f63bb1d2354feae49',None),('slow.lib','6dd075da1073a86a98d9804019842be3d2f13a9f','ed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d'),('fast.lib','fd479d3fd11358bbacee450dc7352b46de8588cb','547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e')]
bindings={}
for name,blob,digest in specs:
 raw=subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/git/blobs/'+blob],timeout=60)
 data=base64.b64decode(json.loads(raw)['content']);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
 path=native/name;path.write_bytes(data)
 if digest:assert sha(path)==digest
 bindings[name]={'git_blob':blob,'sha256':sha(path)}
assert sha(native/'typ.lib')=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
app=P('/mnt/s/librelane.AppImage');assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
result=dict(status='RUNNING',scope='Isolated replay placement with identical 600x600um core, 4ns ideal clock, .25ns uncertainty, original 5% derates, frozen IHP libraries and identical estimated layer RC. No CTS, routed RC, full-chip hold, DRC/LVS or production acceptance.',native_mapping_artifact=14121339687,bindings=bindings,timing_accepted=False,cases={})
for label in ['baseline','predecode']:
 folder=out/label;folder.mkdir();nfolder=native/label;nfolder.mkdir()
 tcl=f"""if {{[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"}} {{error "Runtime drift"}}
set_thread_count 2
read_lef {native}/tech.lef
read_lef {native}/cells.lef
define_corners slow typ fast
foreach c {{slow typ fast}} {{read_liberty -corner $c {native}/$c.lib}}
read_verilog {native}/{label}.v
link_design soc_pcie_replay_tx
create_clock -name pcie_clk_i -period 4.0 [get_ports clk_i]
set_clock_uncertainty 0.25 [all_clocks]
set_clock_transition 0.15 [all_clocks]
set data_inputs [get_ports {{link_up_i training_i retrain_done_i in_data_i* in_sop_i in_eop_i in_valid_i ack_valid_i ack_nak_i ack_sequence_i* reserve_ready_i tx_ready_i}}]
set_input_delay -clock pcie_clk_i -max 0.8 $data_inputs
set_input_delay -clock pcie_clk_i -min 0.2 $data_inputs
set_output_delay -clock pcie_clk_i -max 0.8 [all_outputs]
set_output_delay -clock pcie_clk_i -min 0.2 [all_outputs]
set_driving_cell -lib_cell sg13g2_buf_4 -pin X $data_inputs
set_load 0.006 [all_outputs]
set_max_fanout 10 [current_design]
set_timing_derate -early 0.95
set_timing_derate -late 1.05
initialize_floorplan -die_area {{0 0 620 620}} -core_area {{10 10 610 610}} -site CoreSite
make_tracks
place_pins -hor_layers Metal3 -ver_layers Metal2
foreach {{l r c}} {{Metal2 2.53519E-03 1.69121E-04 Metal3 1.54329E-03 1.82832E-04 Metal4 6.31424E-04 1.66454E-04 Metal5 6.84051E-04 8.57431E-05}} {{set_layer_rc -layer $l -resistance $r -capacitance $c}}
set_wire_rc -signal -layer Metal3
set_wire_rc -clock -layer Metal4
global_placement -density 0.6
detailed_placement
check_placement -verbose
estimate_parasitics -placement
proc reports {{phase}} {{
 foreach c {{slow typ fast}} {{
  report_checks -corner $c -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 40 -fields {{slew cap fanout}} -digits 6 > {folder}/$phase-$c-max.rpt
  report_checks -corner $c -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 40 -fields {{slew cap fanout}} -digits 6 > {folder}/$phase-$c-min.rpt
 }}
 write_db {nfolder}/$phase.odb
 write_verilog {nfolder}/$phase.v
}}
reports placed
repair_design
detailed_placement
check_placement -verbose
estimate_parasitics -placement
reports electrical_repair
puts NSSOC_REPLAY_PLACEMENT_SCREEN_COMPLETE_NOT_ROUTED
"""
 script=nfolder/'place.tcl';script.write_text(tcl)
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
 with (folder/'native.log').open('w') as log:
  r=subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=2400)
 assert r.returncode==0 and 'NSSOC_REPLAY_PLACEMENT_SCREEN_COMPLETE_NOT_ROUTED' in (folder/'native.log').read_text(),label
 row={}
 for report in folder.glob('*.rpt'):
  text=report.read_text();slacks=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',text)
  assert slacks,(report,text[-1000:])
  row[report.name]={'worst_reported_slack_ns':min(map(float,slacks)),'reported_paths':len(slacks),'sha256':sha(report)}
 assert len(row)==12
 result['cases'][label]=row;(out/'placement-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
result['status']='COMPLETE_ISOLATED_PLACEMENT_ESTIMATE_NOT_TIMING_ACCEPTED';(out/'placement-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
