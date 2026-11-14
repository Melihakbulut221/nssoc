require 'json'
def build(text)
  nl=RBA::Netlist.new
  [['PMOS4', RBA::DeviceClassMOS4Transistor], ['NMOS4', RBA::DeviceClassMOS4Transistor]].each do |name, klass|
    dc=klass.new; dc.name=name; nl.add(dc)
  end
  nl.from_s(text)
  nl
end
base="circuit INV(IN=IN,OUT=OUT,VDD=VDD,VSS=VSS);\n  device PMOS4 P(S=VDD,G=IN,D=OUT,B=VDD)(L=0.25,W=0.95);\n  device NMOS4 N(S=VSS,G=IN,D=OUT,B=VSS)(L=0.25,W=0.95);\nend;\n"
cases={'identity'=>[base,true], 'wrong_width'=>[base.sub('W=0.95','W=1.9'),false],
 'open_gate'=>[base.sub('G=IN','G=OPEN'),false],
 'missing_device'=>[base.lines.reject { |l| l.include?('device NMOS4') }.join,false],
 'extra_device'=>[base.sub('end;','device NMOS4 EXTRA(S=VSS,G=IN,D=OUT,B=VSS)(L=0.25,W=0.95);
end;'),false]}
rows=[]
[nil,16].each do |limit|
  cases.each do |label,(candidate,expected)|
    comparer=RBA::NetlistComparer.new
    comparer.max_branch_complexity=limit if limit
    actual=comparer.compare(build(base),build(candidate))
    rows << {'limit'=>limit || 'default','label'=>label,'expected'=>expected,'actual'=>actual}
    raise "Control failed #{label}/#{limit}" unless actual==expected
  end
end
Dir.mkdir('out') unless Dir.exist?('out')
File.write('out/comparison-controls.json',JSON.pretty_generate({'status'=>'PASS','scope'=>'Native comparer identity and graph/parameter mutations only, not full macro or foundry acceptance','cases'=>rows}))
