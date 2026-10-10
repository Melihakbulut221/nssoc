def test_only_second_reference_changes_in_explicit_cloned_subcircuit():
    parent=(ROOT/"hw/soc/analog/pcie/clock_div4_hbt_v9.spice").read_text()
    core=(ROOT/"hw/soc/analog/pcie/clock_div2_hbt.spice").read_text()
    actual=(ROOT/"hw/soc/analog/pcie/clock_div4_hbt_v10.spice").read_text()
    child=core[core.index('.subckt '):].replace('nssoc_clock_div2_hbt','nssoc_clock_div2_tail_v10')
    assert child.count('XBIAS avdd ref sub rppd w=1u l=12.7u b=0 sw_et=1')==1
    child=child.replace('XBIAS avdd ref sub rppd w=1u l=12.7u b=0 sw_et=1','XBIAS avdd ref sub rppd w=1u l=11.5u b=0 sw_et=1')
    expected=parent.replace('nssoc_clock_div4_hbt_v9','nssoc_clock_div4_hbt_v10')
    expected=expected.replace('XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt','XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_tail_v10')
    expected=expected.replace('.subckt nssoc_clock_div4_hbt_v10',child+'\n.subckt nssoc_clock_div4_hbt_v10')
    meaningful=lambda s:[l for l in s.splitlines() if l and not l.startswith('*')]
    assert meaningful(actual)==meaningful(expected)
    rows={r['name']:r for r in m.devices(ROOT)}
    assert rows['DIV__XFIRST__XCORE__XBIAS']['length_um']==12.7
    assert rows['DIV__XSECOND__XBIAS']['length_um']==11.5
    assert rows['DIV__XDP']['length_um']==rows['DIV__XDN']['length_um']==8
    for name in ('DIV__XCP','DIV__XCN'):
        assert rows[name]['width_um']==rows[name]['length_um']==24
