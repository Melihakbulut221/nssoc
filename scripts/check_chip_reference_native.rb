require 'json'
nssoc_top = schematic.circuit_by_name('SOC_TOP') || schematic.circuit_by_name('soc_top')
raise 'Full chip reference top missing' unless nssoc_top
nssoc_memo = {}
nssoc_count = lambda do |c|
  return nssoc_memo[c.name] if nssoc_memo.key?(c.name)
  n = c.each_device.count
  c.each_subcircuit { |s| n += nssoc_count.call(s.circuit_ref) }
  nssoc_memo[c.name] = n
end
nssoc_total = nssoc_count.call(nssoc_top)
nssoc_pins = nssoc_top.each_pin.map { |p| p.name }
nssoc_macros = {}
['RM_IHPSG13_2P_256X16_C2_BM_BIST','RM_IHPSG13_1P_2048X64_C2_BM_BIST'].each do |name|
  c = schematic.circuit_by_name(name)
  raise "Macro missing #{name}" unless c
  nssoc_macros[name] = nssoc_count.call(c)
end
nssoc_rows = {'status'=>'NATIVE_REFERENCE_READER_INVENTORY','top'=>nssoc_top.name,'top_pins'=>nssoc_pins,'top_pin_count'=>nssoc_pins.size,'top_subcircuit_count'=>nssoc_top.each_subcircuit.count,'recursive_primitive_count'=>nssoc_total,'macro_counts'=>nssoc_macros,'full_chip_lvs_passed'=>false,'scope'=>'Same frozen native LVS reader/deck as prior passing DP macro, stopped after independent schematic read before extraction. No electrical comparison.'}
File.write('out/derived/native-reference-reader.json',JSON.pretty_generate(nssoc_rows))
raise 'Top pin count or duplicate changed' unless nssoc_pins.size==354 && nssoc_pins.map(&:upcase).uniq.size==354
raise 'Supply pins missing' unless ['VPWR','VGND'].all? { |p| nssoc_pins.include?(p) }
raise 'Instance count changed' unless nssoc_rows['top_subcircuit_count']==158681
raise 'Primitive count changed' unless nssoc_total==7456816
raise 'SRAM counts changed' unless nssoc_macros.values.sort==[70110,1211120]
nssoc_rows['status']='NATIVE_REFERENCE_READER_PASSED'
File.write('out/derived/native-reference-reader.json',JSON.pretty_generate(nssoc_rows))
exit(0)
