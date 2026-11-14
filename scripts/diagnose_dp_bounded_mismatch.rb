require 'json'
require 'digest'
raise 'Wrong database' unless Digest::SHA256.file('/tmp/full-macro.lvsdb').hexdigest=='341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa'
db=RBA::LayoutVsSchematic.new;db.read('/tmp/full-macro.lvsdb');xref=db.xref
pairs=xref.each_circuit_pair.to_a;bad=pairs.select { |p| p.status.to_s!='Match' };raise 'Wrong scope' unless bad.size==1
cp=bad[0];a=cp.first;b=cp.second;raise 'Wrong top' unless a.name=='RM_IHPSG13_2P_256x16_c2_bm_bist'
[a,b].each do |c|
 names=c.each_net.map { |n| n.expanded_name };raise 'Ambiguous net identity' unless names.uniq.size==names.size
end
port_maps=[a,b].map do |c|
 ports={}
 c.each_pin do |pin|
  n=c.net_for_pin(pin.id)
  (ports[n.expanded_name]||=[]) << pin.name if n
 end
 ports
end
net_status=[{},{}];net_counts=Hash.new(0);top_ports=[]
xref.each_net_pair(cp) do |pair|
 status=pair.status.to_s;net_counts[status]+=1;row={'status'=>status}
 [pair.first,pair.second].each_with_index do |net,i|
  next unless net
  key=net.expanded_name;net_status[i][key]=status
  row[['layout_ports','reference_ports'][i]]=port_maps[i].fetch(key,[])
 end
 top_ports << row if !row.fetch('layout_ports',[]).empty? || !row.fetch('reference_ports',[]).empty?
end
device=lambda do |d,i|
 if !d
  nil
 else
  cls=d.device_class
  params=cls.parameter_definitions.map { |q| [q.name,d.parameter(q.id)] }.to_h
  terms=cls.terminal_definitions.map do |term|
   n=d.net_for_terminal(term.id);key=n ? n.expanded_name : nil
   {'terminal'=>term.name,'net_comparison_status'=>net_status[i].fetch(key,'missing'),'top_ports'=>port_maps[i].fetch(key,[])}
  end
  {'class'=>cls.name,'parameters'=>params,'terminals'=>terms}
 end
end
counts=Hash.new(0);samples=[];param_counts=Hash.new(0)
xref.each_device_pair(cp) do |pair|
 status=pair.status.to_s;da=device.call(pair.first,0);dr=device.call(pair.second,1)
 counts[[status,da ? da['class'] : nil,dr ? dr['class'] : nil]]+=1
 if da && dr
  (da['parameters'].keys|dr['parameters'].keys).each do |k|
   av=da['parameters'][k];bv=dr['parameters'][k];param_counts[[k,av,bv]]+=1 if av!=bv
  end
 end
 samples << {'status'=>status,'layout'=>da,'reference'=>dr} if status!='Match' && samples.size<30
end
subcounts=Hash.new(0);xref.each_subcircuit_pair(cp) { |pair| subcounts[pair.status.to_s]+=1 }
circuit_counts=Hash.new(0);pairs.each { |pair| circuit_counts[pair.status.to_s]+=1 }
r={'status'=>'DIAGNOSTIC_ONLY_NOT_LVS_ACCEPTANCE','source_run'=>43587554414,'native_artifact'=>14111500413,'database_sha256'=>Digest::SHA256.file('/tmp/full-macro.lvsdb').hexdigest,
 'reader'=>'Native KLayout Ruby; Python binding abort not bypassed',
 'circuit_status_counts'=>circuit_counts,'net_status_counts'=>net_counts,'subcircuit_status_counts'=>subcounts,
 'device_status_and_class_counts'=>counts.map { |k,v| {'status'=>k[0],'layout_class'=>k[1],'reference_class'=>k[2],'count'=>v} },
 'parameter_difference_counts'=>param_counts.map { |k,v| {'parameter'=>k[0],'layout'=>k[1],'reference'=>k[2],'count'=>v} },
 'top_port_net_pairs'=>top_ports,'nonmatching_device_samples'=>samples,'xref_log_api'=>xref.methods.map(&:to_s).select { |n| n.include?('log') },
 'scope'=>'Bounded-search mismatch diagnosis only. Internal net identifiers omitted. No native circuit edit, waiver or manufacturing approval.'}
Dir.mkdir('out') unless Dir.exist?('out');File.write('out/top-mismatch.json',JSON.pretty_generate(r))
