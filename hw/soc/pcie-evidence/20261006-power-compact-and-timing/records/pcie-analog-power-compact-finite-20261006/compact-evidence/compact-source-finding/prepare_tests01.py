from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
p=R/'sw/tests/test_pcie_clock_div4_v7_power_v2_layout.py';q=R/'sw/tests/test_pcie_clock_div4_v7_compact_v1_layout.py';s=p.read_text().replace('make_pcie_clock_div4_v7_power_v2','make_pcie_clock_div4_v7_compact_v1').replace('check_pcie_clock_div4_v7_power_v2','check_pcie_clock_div4_v7_compact_v1')
a=s.index('def test_three_rows_retain_divider_mirroring');b=s.index('\n\n@pytest.mark.parametrize',a)
s=s[:a]+'''def test_compact_planner_preserves_graph_and_orders_with_separated_tracks():
    import make_pcie_clock_div4_v7_power_v2 as old
    rows = m.devices(ROOT)
    assert rows == old.devices(ROOT)
    plan, starts, nets = m.placement_plan(rows)
    original, _, _ = old.placement_plan(rows)
    assert set(plan) == set(original)
    assert Counter(p[0] for p in plan.values()) == {0: 30, 1: 17, 2: 26}
    assert len({(p[1], p[2]) for p in plan.values()}) == 73
    assert max(p[1] for p in plan.values()) == 856
    assert starts == {0: 0.0, 1: 176.0, 2: 332.0}
    for rid in range(3):
        names = [n for n in plan if plan[n][0] == rid]
        assert sorted(names,key=lambda n:plan[n][1]) == sorted(names,key=lambda n:original[n][1])
        tracks = [m.bus_offset(nets[rid],n) for n in nets[rid]]
        assert tracks[0] == 72
        for i in range(1,len(tracks)):
            wide = bool(set(nets[rid][i-1:i+1]) & {"DIV_AVDD", "AVSS"})
            assert tracks[i]-tracks[i-1] == (8 if wide else 4)
        if rid < 2:
            assert starts[rid+1] == starts[rid]+tracks[-1]+24
    assert nets[0][5:7] == ["DIV__XFIRST__XCORE__XS__SE", "DIV__XFIRST__XCORE__XS__TE"]
    assert nets[1][3] == "DIV__LP"
    assert nets[2][5:7] == ["DIV__XSECOND__XS__TE", "DIV__XSECOND__XM__TE"]
    assert [rid for rid in nets if "CLKP" in nets[rid]] == [0]
    assert [rid for rid in nets if "DIV__S1P" in nets[rid]] == [0, 1]
    # Conservative intrinsic + left escape envelopes, independent of the
    # generated GDS. Actual DRC will verify native polygons and all routes.
    by = {r["name"]:r for r in rows}
    for rid in range(3):
        ordered = sorted((n for n in plan if plan[n][0]==rid), key=lambda n:plan[n][1])
        for before,after in zip(ordered,ordered[1:]):
            a = by[before]
            right = 8.9 if a["kind"]=="hbt" else a["width_um"]+0.6
            assert plan[after][1]-9-(plan[before][1]+right) >= 5
        for name in ordered:
            row=by[name];y=plan[name][2]-starts[rid]
            top = 3.78 if row["kind"]=="hbt" else row["length_um"]+(0.61 if row["kind"]=="resistor" else 0.60)
            assert 59.77 <= y+top <= 60.001
    with pytest.raises(ValueError,match="row bus absent"):
        m.bus_offset(nets[0],"UNKNOWN")
''' +s[b:]
q.write_text(s)
p=R/'sw/tests/test_pcie_clock_div4_v7_power_v2_native.py';q=R/'sw/tests/test_pcie_clock_div4_v7_compact_v1_native.py';q.write_text(p.read_text().replace('import check_pcie_clock_div4_v7_power_v2 as m','import check_pcie_clock_div4_v7_compact_v1 as m'))
