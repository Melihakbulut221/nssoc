from pathlib import Path
import hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-divider-v8-cap-v1-20261006')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def names(s):return s.replace('V8_CAP_V1','V9_BIAS_V1').replace('v8_cap_v1','v9_bias_v1').replace('v8-cap-v1','v9-bias-v1').replace('hbt_v8','hbt_v9').replace('HBT_V8','HBT_V9').replace('v8 cap v1','v9 bias v1')
old=R/'hw/soc/analog/pcie/clock_div4_hbt_v8.spice';new=old.with_name('clock_div4_hbt_v9.spice')
s=names(old.read_text())
for inst,node in [('XDP','ckp'),('XDN','ckn')]:s=one(s,f'{inst} {node} avss sub rppd w=1u l=7u b=0 sw_et=1',f'{inst} {node} avss sub rppd w=1u l=8u b=0 sw_et=1')
s=s.replace('Separate v8: only two second-stage MIM feed-forward capacitors grow20x20 to24x24um.','Separate v9: only top-level second-stage XDP/XDN pull-downs change L7um to L8um; both24um MIMs retained.')
new.write_text(s);newsha=sha(new)
for kind in ['make','check','audit']:
 old=R/f'hw/soc/flow/{kind}_pcie_clock_div4_v8_cap_v1.py';new=old.with_name(f'{kind}_pcie_clock_div4_v9_bias_v1.py');s=names(old.read_text())
 s=s.replace('87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc',newsha)
 if kind=='make':
  s=s.replace('two larger native feed-forward caps; all DC devices unchanged.','two second-stage pull-down resistors L7um to L8um; all other devices unchanged.')
  s=s.replace('only two 20um MIMs enlarged to 24um; all 71 other circuit primitives, DC bias and 18 finite substrate contacts unchanged.','only second-stage XDP/XDN W1um pull-down lengths7um to8um; both24um MIMs and all71 other circuit primitives plus18 finite substrate contacts unchanged.')
 elif kind=='check':
  s=s.replace('/dev/shm/nssoc-div4-v7-compact-v2-layout-01','/dev/shm/nssoc-div4-v8-cap-v1-layout-01').replace('nssoc_clock_div4_v7_compact_v2_layout.gds','nssoc_clock_div4_v8_cap_v1_layout.gds')
  s=s.replace('Actual two-cap geometry delta','Actual two-pull-down geometry delta').replace('PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS','PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS')
 else:
  s=s.replace('Strict saved-GDS two-capacitor geometry delta','Strict saved-GDS two-pull-down resistor geometry delta')
  s=s.replace('nssoc_clock_div4_v7_compact_v2_layout','nssoc_clock_div4_v8_cap_v1_layout')
  s=s.replace('db400e586cadbedbea9ec8aec5466c0eba4789e262c90ebd0d321a1c2cbcf579','4361db967f0df1d340360f6b50461274b8a36cb49d208072a911cfd2077c78c1')
  s=s.replace('208d2063593a500aea6c840b4600228e1e4ae550d5f7c364e95b4d089c8e8380','0e6e0ed365a2c4373ef85dc9236be3f59639472a785b3165e38c077f0702966d')
  s=one(s,'CAPS = {"DIV__XCP", "DIV__XCN"}','CAPS = {"DIV__XCP", "DIV__XCN"}\nPULLDOWNS = {"DIV__XDP", "DIV__XDN"}')
  start=s.index('def compare_intrinsics(');end=s.index('\n\ndef power_arrays',start)
  s=s[:start]+(B/'resistor-and-comparison-fragment.py').read_text().rstrip()+s[end:]
  s=s.replace('Exact frozen CompactV2 baseline','Exact frozen Cap24 baseline')
  s=s.replace('hw/soc/analog/pcie/clock_div4_hbt_v7.spice','hw/soc/analog/pcie/clock_div4_hbt_v8.spice').replace('49226d5b3a40fc4f8faafbaee3adb5580d8346222a825b79daaddc0358b2c65c','87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc')
  s=s.replace('two-cap source graph','two-pull-down source graph')
  s=s.replace('Exact changed MIM equals independent native rectangle formula','Exact retained Cap24 MIM equals independent native rectangle formula')
  where='    require(inputs=={p:pin(p) for p in inputs},"Saved actual input bytes unchanged")'
  add='''    for fault,geometry in (("remove_actual_changed_resistor_body", dict(selected["DIV__XDP"]["geometry"])), ("restore_shorter_actual_pulldown", rppd_template(1,7,tech,dbu))):
        if fault == "remove_actual_changed_resistor_body":
            geometry[(128,0)] = pya.Region()
        bad=[dict(r,geometry=geometry) if r is selected["DIV__XDP"] else r for r in new_instances]
        reject(fault,"Exact changed pull-down equals independent native resistor rectangle formula",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
'''
  s=one(s,where,add+where)
  s=s.replace('PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS','PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS').replace('changed_mim_dimensions_um={n:[20,24] for n in sorted(CAPS)}','changed_pulldown_length_um={n:[7,8] for n in sorted(PULLDOWNS)},retained_cap24_mim_names=sorted(CAPS)')
 new.write_text(s)
for kind in ['layout','native']:
 old=R/f'sw/tests/test_pcie_clock_div4_v8_cap_v1_{kind}.py';new=old.with_name(f'test_pcie_clock_div4_v9_bias_v1_{kind}.py');s=names(old.read_text())
 if kind=='layout':
  s=s.replace('import make_pcie_clock_div4_v7_compact_v2 as old','import make_pcie_clock_div4_v8_cap_v1 as old')
  s=one(s,'assert before["width_um"] == before["length_um"] == 20\n            assert after == dict(before, width_um=24, length_um=24)','assert before["width_um"] == 1 and before["length_um"] == 7\n            assert after == dict(before, length_um=8)')
  s=one(s,'assert changed == ["DIV__XCP", "DIV__XCN"]','assert changed == ["DIV__XDP", "DIV__XDN"]')
  a='    return text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")'
  b='''    text=text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")
    assert text.count("rppd w=1u l=7u") == 2
    return text.replace("rppd w=1u l=7u", "rppd w=1u l=8u")'''
  s=one(s,a,b)
  s=s.replace('test_only_two_capacitor_source_dimensions_change_and_pitch_is_36um','test_only_two_pulldown_lengths_change_and_cap24_pitch_is_36um')
  s=s.replace('clock_div4_hbt_v7.spice','clock_div4_hbt_v8.spice')
  s=one(s,'line=line.replace("nssoc_clock_div4_hbt_v7", "nssoc_clock_div4_hbt_v9")\n        if line.startswith(("XCP ", "XCN ")):\n            assert "w=20u l=20u" in line\n            line=line.replace("w=20u l=20u", "w=24u l=24u")','line=line.replace("nssoc_clock_div4_hbt_v8", "nssoc_clock_div4_hbt_v9")\n        if line.startswith(("XDP ", "XDN ")):\n            assert "rppd w=1u l=7u" in line\n            line=line.replace("rppd w=1u l=7u", "rppd w=1u l=8u")')
 else:
  s=s.replace('("ps=0u", "ps=1u"),', '("ps=0u", "ps=1u"),\n        ("rppd w=1u l=8u", "rppd w=1u l=7u"),')
  # Same immutable old native fixture is converted to the exact declared new geometry before syntax controls.
  s=s.replace('return text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")','text=text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")\n    assert text.count("rppd w=1u l=7u") == 2\n    return text.replace("rppd w=1u l=7u", "rppd w=1u l=8u")')
 new.write_text(s)
for name in ['launch01.py','prepare_launch01.py']:(B/name).write_text(names((P/name).read_text()))
print(newsha)
