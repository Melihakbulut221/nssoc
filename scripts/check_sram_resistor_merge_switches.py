# SPDX-License-Identifier: Apache-2.0
"""Run the exact pinned Ruby RES2 class and its proposed switch correction."""
import pathlib,subprocess,json,zipfile,io,hashlib,re
import klayout.db as db
P=pathlib.Path
raw=P('diagnostic.zip').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='d6ff10e2ebc4613908dad51f338860592ef9ef4b8e88e48b729538d22a93e45a'
data=json.loads(zipfile.ZipFile(io.BytesIO(raw)).read('top-mismatch.json'))
source=data['deck_source_evidence']['custom_devices.lvs']['source']
assert hashlib.sha256(source.encode()).hexdigest()==data['deck_source_evidence']['custom_devices.lvs']['sha256']
match=re.search(r'(?ms)^class RES2 < RBA::DeviceClassResistor\n.*?^end$',source);assert match
original=match[0]
assert original.count('    super\n')==1
fixed=original.replace('    super\n','    super\n    self.supports_serial_combination = SERIES_RES\n    self.supports_parallel_combination = PARALLEL_RES\n')
P('out').mkdir();rows=[]
for variant,definition in [('original',original),('fixed',fixed)]:
 for serial in [False,True]:
  for parallel in [False,True]:
   tag=f'{variant}-{int(serial)}-{int(parallel)}'
   ruby="require 'json'\nSERIES_RES = "+str(serial).lower()+"\nPARALLEL_RES = "+str(parallel).lower()+"\n"+definition+"\n"
   ruby += """
results = []
['serial','parallel'].each do |kind|
  nl = RBA::Netlist.new
  dc = RES2.new; dc.name = 'RES2'; nl.add(dc)
  c = RBA::Circuit.new; c.name = 'TOP'; nl.add(c)
  a = c.create_net('a'); b = c.create_net('b'); x = c.create_net('x')
  c.connect_pin(c.create_pin('a'), a); c.connect_pin(c.create_pin('b'), b)
  connections = kind == 'serial' ? [[a,x],[x,b]] : [[a,b],[a,b]]
  connections.each_with_index do |ends,i|
    dev = c.create_device(dc, 'R'+i.to_s)
    dev.connect_terminal('A',ends[0]); dev.connect_terminal('B',ends[1])
    dev.set_parameter('W',0.26); dev.set_parameter('L',0.6); dev.set_parameter('R',1000.0)
  end
  before = c.each_device.to_a.size
  raise 'Expected two native devices' unless before == 2
  nl.combine_devices
  results << {'topology'=>kind,'device_count_before'=>before,'device_count_after'=>c.each_device.to_a.size}
end
File.write('behavior.json',JSON.generate(results))
"""
   P('behavior.rb').write_text(ruby)
   proc=subprocess.run(['klayout','-b','-zz','-r','behavior.rb'],timeout=60,capture_output=True,text=True)
   if proc.returncode:
    failure={'variant':variant,'tag':tag,'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'production_accepted':False}
    P('out/native-control-error.json').write_text(json.dumps(failure,indent=2));print(json.dumps(failure));proc.check_returncode()
   for row in json.loads(P('behavior.json').read_text()):
    enabled=(serial if row['topology']=='serial' else parallel) if variant=='fixed' else True
    expected=1 if enabled else 2
    row.update(variant=variant,requested_serial=serial,requested_parallel=parallel,expected_count=expected)
    rows.append(row)
    P('out/partial-controls.json').write_text(json.dumps(rows,indent=2))
    assert row['device_count_after']==expected,(tag,row)
r={'status':'PASS_ISOLATED_MERGE_SWITCH_CONTROLS','source_sha':__import__('os').environ.get('GITHUB_SHA'),'original_custom_devices_sha256':hashlib.sha256(source.encode()).hexdigest(),'original_RES2_source':original,'candidate_RES2_source':fixed,'cases':rows,'scope':'Exact Ruby RES2 class instantiated in native KLayout two-resistor graphs, with boundary pins and all four switch combinations. Not macro LVS, topology qualification, DRC, or manufacturing acceptance. No SRAM GDS/CDL or comparison tolerances changed.','production_accepted':False,'upstream_reference':'https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1121','upstream_head':'3df647ebe53439ae41d56a1e9c2b38003ba2124d'}
P('out/merge-switch-controls.json').write_text(json.dumps(r,indent=2));print(r['status'],len(rows))
