# SPDX-License-Identifier: Apache-2.0
require 'json'
def ns_find(nl,name)
  found=nl.each_circuit.select { |c| c.name.downcase==name.downcase }
  raise "Missing/ambiguous circuit #{name}" unless found.size==1
  found[0]
end
def ns_count(c,cache={},active=[])
  raise 'Recursive hierarchy' if active.include?(c.name)
  return cache[c.name] if cache.key?(c.name)
  n=c.each_device.count
  c.each_subcircuit { |s| n+=ns_count(s.circuit_ref,cache,active+[c.name]) }
  cache[c.name]=n
end
raise 'Unsafe comparison switches' if ALLOW_UNMATCHED_PORTS || SIMPLIFY || PURGE || PURGE_NETS || SERIES_RES || PARALLEL_RES
raise 'Expected native top pin construction' unless TOP_LVL_PINS
netlist.make_top_level_pins
schematic.make_top_level_pins
pairs=[
 ['NSDP_RM_IHPSG13_2P_BITKIT_16x2_SRAM','NSDP_RM_IHPSG13_256X16_C2_2P_BITKIT_16X2_SRAM'],
 ['NSDP_RM_IHPSG13_2P_COLUMN_64','NSDP_RM_IHPSG13_256X16_C2_2P_COLUMN_PCELL_0'],
 ['NSDP_RM_IHPSG13_2P_MATRIX_64x32','NSDP_RM_IHPSG13_256X16_C2_2P_MATRIX_PCELL_1'],
 ['NSSP_RM_IHPSG13_1P_BITKIT_16x2_SRAM','NSSP_RM_IHPSG13_2048X64_C2_1P_BITKIT_16X2_SRAM'],
 ['NSSP_RM_IHPSG13_1P_COLUMN_512','NSSP_RM_IHPSG13_2048X64_C2_1P_COLUMN_PCELL_0'],
 ['NSSP_RM_IHPSG13_1P_MATRIX_512x128','NSSP_RM_IHPSG13_2048X64_C2_1P_MATRIX_PCELL_1']]
pairs.each { |a,b| same_circuits(ns_find(netlist,a).name,ns_find(schematic,b).name) }
align
netlist.combine_devices if COMBINE_DEVICES
schematic.combine_devices if COMBINE_DEVICES
specs=[
 ['NSDP_','RM_IHPSG13_2P_256x16_c2_bm_bist',70110,215,%w[CINVX2 CINVX8 DFPQD_MSAFFX2P FILLCAP4 FILLCAP8 WLDRVX8 INVX2 NAND2X2 CINVX4]],
 ['NSSP_','RM_IHPSG13_1P_2048x64_c2_bm_bist',1211120,355,%w[CBUFX8 CINVX2 CINVX8 FILLCAP4 FILLCAP8 WLDRVX8 INVX2 NAND2X2 CINVX4]]]
rows=[]
[['layout',netlist],['reference',schematic]].each do |side,nl|
  top=ns_find(nl,'soc_top');before=ns_count(top)
  specs.each do |prefix,macro,expected,npins,names|
    c=ns_find(nl,macro);m_before=ns_count(c);pins=c.each_pin.map { |p| p.name }
    raise "Macro primitive mismatch #{side}/#{macro}: #{m_before}" unless m_before==expected
    raise "Macro pin count mismatch #{side}/#{macro}: #{pins.size}" unless pins.size==npins
    names.each { |name| nl.flatten_circuit(ns_find(nl,prefix+'RSC_IHPSG13_'+name)) }
    after=ns_count(c);raise 'Macro flatten changed devices' unless m_before==after
    rows << {'side'=>side,'macro'=>macro,'before'=>m_before,'after'=>after,'pins'=>pins,'flattened_cells'=>names.map { |n| prefix+'RSC_IHPSG13_'+n }}
  end
  after=ns_count(top);raise 'Chip flatten changed devices' unless before==after
  rows << {'side'=>side,'top'=>top.name,'before'=>before,'after'=>after,'pins'=>top.each_pin.map { |p| p.name }}
end
File.write('out/derived/full-chip-normalization.json',JSON.pretty_generate({'rows'=>rows,'pairs'=>pairs,'full_chip_lvs_passed'=>false}))
lp=ns_find(netlist,'soc_top').each_pin.map { |p| p.name.upcase }.sort
rp=ns_find(schematic,'soc_top').each_pin.map { |p| p.name.upcase }.sort
raise 'Full chip top port contract mismatch' unless lp.size==354 && lp==rp
specs.each do |prefix,macro,expected,npins,names|
  a=ns_find(netlist,macro).each_pin.map { |p| p.name.upcase }.sort
  b=ns_find(schematic,macro).each_pin.map { |p| p.name.upcase }.sort
  raise "SRAM pin contract mismatch #{macro}" unless a==b
end
max_res(1e9)
min_caps(1e-18)
max_branch_complexity(2048)
logger.info('Starting full chip transistor LVS with flag_missing_ports')
success=compare && flag_missing_ports
File.write('out/derived/native-compare-result.json',JSON.pretty_generate({'native_compare_passed'=>success,'manufacturing_approval'=>false,'scope'=>'Full hierarchical transistor chip comparison against independent Verilog-derived reference, including engineering SRAM interiors.'}))
logger.info(success ? 'INFO : Netlists match.' : "ERROR : Netlists don't match")
