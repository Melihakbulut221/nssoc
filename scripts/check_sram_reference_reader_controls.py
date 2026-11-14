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
import base64
blob=P('diagnostic.zip').read_bytes()
assert hashlib.sha256(blob).hexdigest()=='d6ff10e2ebc4613908dad51f338860592ef9ef4b8e88e48b729538d22a93e45a'
evidence=json.loads(zipfile.ZipFile(io.BytesIO(blob)).read('top-mismatch.json'))['deck_source_evidence']['custom_reader.lvs']
reader_source=evidence['source'];assert hashlib.sha256(reader_source.encode()).hexdigest()==evidence['sha256']
old="    elsif num_nets == 2 && model.downcase == 'lvsres'\n      RES2.new\n"
new="    elsif num_nets == 2 && ['lvsres', 'res_metal2', 'res_metal3'].include?(model.downcase)\n      RES2.new\n"
assert reader_source.count(old)==1
reader_candidate=reader_source.replace(old,new)
globals_source=base64.b64decode(json.loads(P('globals.json').read_text())['content']).decode()
assert hashlib.sha256(globals_source.encode()).hexdigest()=='f6c58978f1c21c81efa3f2f6348327f32d72188620511e0f36bd70b30a0209fb'

ruby="require 'json'\nSERIES_RES=false\nPARALLEL_RES=false\n"+globals_source+"\n"+source+"\n"+reader_candidate+"\n"+r'''
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

def read_reference(layer,mutation)
  model=mutation=='wrong_layer' ? (layer=='res_metal2' ? 'res_metal3' : 'res_metal2') : layer
  width=mutation=='wrong_width' ? '2.1e-07' : '2e-07'
  length=mutation=='wrong_length' ? '7e-07' : '6e-07'
  net=mutation=='open' ? 'OPEN' : 'B'
  path='reference-control.cdl'
  File.write(path,"* independent reader fixture\n.subckt TOP A B C\nR0 A #{net} #{model} w=#{width} l=#{length}\nR1 B C #{layer} w=2.4e-07 l=8e-07\n.ends TOP\n")
  nl=RBA::Netlist.new
  nl.read(path,RBA::NetlistSpiceReader.new(CustomReader.new))
  c=nl.circuit_by_name('TOP');raise 'Wrong reader inventory' unless c.each_device.to_a.size==2
  devices=c.each_device.to_a
  r0=devices.find { |d| d.name=='0' };r1=devices.find { |d| d.name=='1' }
  raise 'Missing resistor identities' unless r0 && r1
  raise 'Reader lost layer identity' unless r0.device_class.name.downcase==model && r1.device_class.name.downcase==layer
  raise 'Reader lost dimensions' unless (r0.parameter('W')-width.to_f*1e6).abs<1e-12 && (r0.parameter('L')-length.to_f*1e6).abs<1e-12
  nl
end

rows=[]
['res_metal2','res_metal3'].each do |layer|
  ['positive','wrong_layer','wrong_width','wrong_length','open'].each do |mutation|
    layout=network(layer,'positive');reference=read_reference(layer,mutation)
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
result={'status':'PASS_EXACT_READER_STRICT_RESISTOR_CONTROLS','source':os.environ['GITHUB_SHA'],'cases':rows,'native_returncode':p.returncode,'ruby_sha256':hashlib.sha256(ruby.encode()).hexdigest(),'res2_sha256':hashlib.sha256(source.encode()).hexdigest(),'reader_candidate_sha256':hashlib.sha256(reader_candidate.encode()).hexdigest(),'reader_source_sha256':evidence['sha256'],'globals_sha256':hashlib.sha256(globals_source.encode()).hexdigest(),'scope':'Exact candidate CustomReader reads actual CDL R statements with both metal layers and dimensions; compares against independent native RES2 graph. Positive cases pass, wrong layer/W/L/open fail. This qualifies only these reader paths and comparator policy; not full macro/topology/RC/manufacturing approval. Reader hash must bind to actual candidate macro result before transferring this evidence.'}
P('out/result.json').write_text(json.dumps(result,indent=2));print(result['status'])
