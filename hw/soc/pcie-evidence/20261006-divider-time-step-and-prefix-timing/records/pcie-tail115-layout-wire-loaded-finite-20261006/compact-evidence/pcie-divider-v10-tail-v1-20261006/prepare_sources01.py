# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.with_name('pcie-divider-v9-bias-v1-20261006')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def names(s):return s.replace('V9_BIAS_V1','V10_TAIL_V1').replace('v9_bias_v1','v10_tail_v1').replace('v9-bias-v1','v10-tail-v1').replace('hbt_v9','hbt_v10').replace('HBT_V9','HBT_V10').replace('v9 bias v1','v10 tail v1')
old=R/'hw/soc/analog/pcie/clock_div4_hbt_v9.spice';new=old.with_name('clock_div4_hbt_v10.spice');assert not new.exists()
parentcore=(R/'hw/soc/analog/pcie/clock_div2_hbt.spice').read_text();start=parentcore.index('.subckt ');core=parentcore[start:].replace('nssoc_clock_div2_hbt','nssoc_clock_div2_tail_v10')
core=one(core,'XBIAS avdd ref sub rppd w=1u l=12.7u b=0 sw_et=1','XBIAS avdd ref sub rppd w=1u l=11.5u b=0 sw_et=1')
s=names(old.read_text());s=one(s,'XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt','XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_tail_v10')
s=s.replace('Separate v9: only top-level second-stage XDP/XDN pull-downs change L7um to L8um; both24um MIMs retained.','Separate v10: only second-stage reference XBIAS length12.7um to11.5um; clock pull-downs8um and both24um MIMs retained.')
s=one(s,'.subckt nssoc_clock_div4_hbt_v10',core+'\n.subckt nssoc_clock_div4_hbt_v10');new.write_text(s);newsha=sha(new)
g=Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01');oldgsha=sha(g/'nssoc_clock_div4_v9_bias_v1_layout.gds');oldrsha=sha(g/'result.json')
for kind in ['make','check','audit']:
 old=R/f'hw/soc/flow/{kind}_pcie_clock_div4_v9_bias_v1.py';new=old.with_name(f'{kind}_pcie_clock_div4_v10_tail_v1.py');assert not new.exists();s=names(old.read_text()).replace('5fc944cb5683dda328e6b3aedd21b2e206f03575a232394e8cb528d280e69c9a',newsha)
 if kind=='make':
  s=s.replace('two second-stage pull-down resistors L7um to L8um; all other devices unchanged.','one second-stage reference resistor L12.7um to L11.5um; all other devices unchanged.')
  s=s.replace('only second-stage XDP/XDN W1um pull-down lengths7um to8um; both24um MIMs and all71 other circuit primitives plus18 finite substrate contacts unchanged.','only second-stage XBIAS W1um reference length12.7um to11.5um; both24um MIMs, L8 clock pull-downs and all72 other circuit primitives plus18 finite substrate contacts unchanged.')
 elif kind=='check':
  s=s.replace('/dev/shm/nssoc-div4-v8-cap-v1-layout-01','/dev/shm/nssoc-div4-v9-bias-v1-layout-01').replace('nssoc_clock_div4_v8_cap_v1_layout.gds','nssoc_clock_div4_v9_bias_v1_layout.gds')
  s=s.replace('Actual two-pull-down geometry delta','Actual one-reference-resistor geometry delta').replace('PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS','PASS_ACTUAL_TAIL115_ONE_RPPD_DELTA_BIAS8_CAP24_AND_TEN_GEOMETRY_CONTROLS')
 else:
  s=s.replace('Strict saved-GDS two-pull-down resistor geometry delta','Strict saved-GDS one second-stage reference resistor geometry delta')
  s=s.replace('nssoc_clock_div4_v8_cap_v1_layout','nssoc_clock_div4_v9_bias_v1_layout')
  s=s.replace('4361db967f0df1d340360f6b50461274b8a36cb49d208072a911cfd2077c78c1',oldgsha).replace('0e6e0ed365a2c4373ef85dc9236be3f59639472a785b3165e38c077f0702966d',oldrsha)
  s=one(s,'PULLDOWNS = {"DIV__XDP", "DIV__XDN"}','PULLDOWNS = {"DIV__XDP", "DIV__XDN"}\nREFERENCE = {"DIV__XSECOND__XBIAS"}')
  s=s.replace('frozen straight W1/L7-or8 PCell','frozen straight W1/L7,8,11.5,12.7 PCell').replace('length in (D(7), D(8))','length in (D(7), D(8), D("11.5"), D("12.7"))').replace('Only declared straight pull-down geometry and exact DBU','Only declared straight resistor geometry and exact DBU')
  start=s.index('def compare_intrinsics(');end=s.index('\n\ndef power_arrays',start)
  s=s[:start]+(B/'comparison-fragment.py').read_text().rstrip()+s[end:]
  s=s.replace('Exact frozen Cap24 baseline','Exact frozen Bias8 baseline')
  s=s.replace('clock_div4_hbt_v8.spice','clock_div4_hbt_v9.spice').replace('87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc','5fc944cb5683dda328e6b3aedd21b2e206f03575a232394e8cb528d280e69c9a')
  s=s.replace('two-pull-down source graph','one-reference-resistor source graph')
  s=s.replace('Exact changed pull-down equals independent native resistor rectangle formula','Exact retained Bias8 pull-down equals independent native resistor rectangle formula')
  where='    require(inputs=={p:pin(p) for p in inputs},"Saved actual input bytes unchanged")'
  add='''    for fault,geometry in (("remove_actual_reference_resistor_body", dict(selected["DIV__XSECOND__XBIAS"]["geometry"])), ("restore_old_reference_length", rppd_template(1,12.7,tech,dbu))):
        if fault == "remove_actual_reference_resistor_body":
            geometry[(128,0)] = pya.Region()
        bad=[dict(r,geometry=geometry) if r is selected["DIV__XSECOND__XBIAS"] else r for r in new_instances]
        reject(fault,"Exact changed reference equals independent native resistor rectangle formula",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
'''
  s=one(s,where,add+where)
  s=s.replace('PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS','PASS_ACTUAL_TAIL115_ONE_RPPD_DELTA_BIAS8_CAP24_AND_TEN_GEOMETRY_CONTROLS').replace('changed_pulldown_length_um={n:[7,8] for n in sorted(PULLDOWNS)},retained_cap24_mim_names=sorted(CAPS)','changed_reference_length_um={n:[12.7,11.5] for n in sorted(REFERENCE)},retained_bias8_pulldown_names=sorted(PULLDOWNS),retained_cap24_mim_names=sorted(CAPS)').replace('unchanged_intrinsics=89','unchanged_intrinsics=90')
 new.write_text(s)
for kind in ['layout','native']:
 old=R/f'sw/tests/test_pcie_clock_div4_v9_bias_v1_{kind}.py';new=old.with_name(f'test_pcie_clock_div4_v10_tail_v1_{kind}.py');assert not new.exists();s=names(old.read_text())
 oldreturn='    return text.replace("rppd w=1u l=7u", "rppd w=1u l=8u")'
 newreturn='''    text=text.replace("rppd w=1u l=7u", "rppd w=1u l=8u")
    # Parser-only saved syntax fixture: replace exactly one of two W1/L12.7
    # records. Actual native/source identity is separately checked by LVS.
    assert text.count("rppd w=1u l=12.7u") == 2
    return text.replace("rppd w=1u l=12.7u", "rppd w=1u l=11.5u", 1)'''
 s=one(s,oldreturn,newreturn)
 if kind=='layout':
  s=s.replace('import make_pcie_clock_div4_v8_cap_v1 as old','import make_pcie_clock_div4_v9_bias_v1 as old')
  s=one(s,'assert before["width_um"] == 1 and before["length_um"] == 7\n            assert after == dict(before, length_um=8)','assert before["width_um"] == 1 and before["length_um"] == 12.7\n            assert after == dict(before, length_um=11.5)')
  s=one(s,'assert changed == ["DIV__XDP", "DIV__XDN"]','assert changed == ["DIV__XSECOND__XBIAS"]')
  start=s.index('def test_only_two_pulldown_lengths_change_and_cap24_pitch_is_36um():')
  s=s[:start]+(B/'reference-test-fragment.py').read_text()
 else:
  s=s.replace('("rppd w=1u l=8u", "rppd w=1u l=7u"),','("rppd w=1u l=8u", "rppd w=1u l=7u"),\n        ("rppd w=1u l=11.5u", "rppd w=1u l=12.7u"),')
 new.write_text(s)
for name in ['launch01.py','prepare_launch01.py']:
 p=B/name;assert not p.exists();p.write_text(names((P/name).read_text()))
print(newsha)
