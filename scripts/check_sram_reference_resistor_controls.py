#!/usr/bin/env python3
"""Native isolated strict resistor model/width/length/connectivity controls."""
import pathlib,subprocess,json,zipfile,io,hashlib,os
P=pathlib.Path
b=P('merge-controls.zip').read_bytes()
assert hashlib.sha256(b).hexdigest()=='b58b9142d77cb2f5b429ea23df5854b5e65f5bb19158561d635f9be9872214da'
controls=json.loads(zipfile.ZipFile(io.BytesIO(b)).read('merge-switch-controls.json'))
assert controls['status']=='PASS_ISOLATED_MERGE_SWITCH_CONTROLS' and len(controls['cases'])==16
source=controls['candidate_RES2_source']
assert source==controls['original_RES2_source'].replace('    super\n','    super\n    self.supports_serial_combination = SERIES_RES\n    self.supports_parallel_combination = PARALLEL_RES\n')
ruby="require 'json'\nSERIES_RES=false\nPARALLEL_RES=false\n"+source+"\n"+r'''
def network(layer, mutation)
  nl=RBA::Netlist.new
  classes={}
  ['res_metal2','res_metal3'].each do |name|
    dc=RES2.new;dc.name=name;nl.add(dc);classes[name]=dc
  end
  c=RBA::Circuit.new;c.name='TOP';nl.add(c)
  nets={}
  ['A','B','C','OPEN'].each { |name| nets[name]=c.create_net(name) }
  ['A','B','C'].each { |name| c.connect_pin(c.create_pin(name),nets[name]) }
  2.times do |i|
    model=(i==0 && mutation=='wrong_layer') ? (layer=='res_metal2' ? 'res_metal3' : 'res_metal2') : layer
    d=c.create_device(classes[model],'R'+i.to_s)
    ends=i==0 ? ['A',mutation=='open' ? 'OPEN' : 'B'] : ['B','C']
    d.connect_terminal('A',nets[ends[0]]);d.connect_terminal('B',nets[ends[1]])
    d.set_parameter('W',i==0 ? (mutation=='wrong_width' ? 0.21 : 0.2) : 0.24)
    d.set_parameter('L',i==0 ? (mutation=='wrong_length' ? 0.7 : 0.6) : 0.8)
    d.set_parameter('R',0)
  end
  nl
end
rows=[]
['res_metal2','res_metal3'].each do |layer|
  ['positive','wrong_layer','wrong_width','wrong_length','open'].each do |mutation|
    layout=network(layer,'positive');reference=network(layer,mutation)
    cmp=RBA::NetlistComparer.new
    result=cmp.compare(layout,reference)
    expected=mutation=='positive'
    rows << {'layer'=>layer,'mutation'=>mutation,'match'=>result,'expected_match'=>expected}
    File.write('out/partial-controls.json',JSON.pretty_generate(rows))
    raise "Unexpected result #{layer} #{mutation}" unless result==expected
  end
end
File.write('out/native-controls.json',JSON.pretty_generate(rows))
'''
P('out').mkdir(exist_ok=True);P('control.rb').write_text(ruby)
p=subprocess.run(['klayout','-b','-zz','-r','control.rb'],capture_output=True,text=True,timeout=120)
P('out/native.stdout.log').write_text(p.stdout);P('out/native.stderr.log').write_text(p.stderr)
p.check_returncode();rows=json.loads(P('out/native-controls.json').read_text());assert len(rows)==10
result={'status':'PASS_ISOLATED_STRICT_RESISTOR_CONTROLS','source':os.environ['GITHUB_SHA'],'cases':rows,'native_returncode':p.returncode,'ruby_sha256':hashlib.sha256(ruby.encode()).hexdigest(),'res2_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Exact fixed native Ruby RES2 comparison policy and two distinct physical layer model names. Positive cases must pass; wrong layer, width, length and open connectivity must fail. Not original/candidate SRAM macro LVS, deck reader qualification, RC value calibration or manufacturing approval.'}
P('out/result.json').write_text(json.dumps(result,indent=2));print(result['status'])
