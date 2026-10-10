def reference_rows(nominal, texts):
    """Bind V7→Cap24 V8→two-pull-down Bias8 V9 without changing other records."""
    require(n.common.sha(REFERENCE) == REFERENCE_SHA, "Exact V9 reference bytes")
    require(n.common.sha(REFERENCE_PARENT) == REFERENCE_PARENT_SHA, "Exact saved Cap24 V8 reference bytes")
    require(n.common.sha(previous.DIVIDER) == PREVIOUS_REFERENCE_SHA, "Exact original V7 reference bytes")
    original = previous.DIVIDER.read_text()
    parent = REFERENCE_PARENT.read_text()
    actual = REFERENCE.read_text()
    expected_parent = original.replace("nssoc_clock_div4_hbt_v7", "nssoc_clock_div4_hbt_v8")
    for name, left, right in (("XCP", "lp", "ckp"), ("XCN", "ln", "ckn")):
        before = f"{name} {left} {right} cap_cmim w=20u l=20u"
        after = f"{name} {left} {right} cap_cmim w=24u l=24u"
        require(expected_parent.count(before) == 1, "Unique original MIM reference")
        expected_parent = expected_parent.replace(before, after)
    circuit = lambda text: [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    require(circuit(parent) == circuit(expected_parent), "Exact historical two-MIM V7 to V8 delta")
    expected = parent.replace("nssoc_clock_div4_hbt_v8", "nssoc_clock_div4_hbt_v9")
    for name, node in (("XDP", "ckp"), ("XDN", "ckn")):
        before = f"{name} {node} avss sub rppd w=1u l=7u b=0 sw_et=1"
        after = f"{name} {node} avss sub rppd w=1u l=8u b=0 sw_et=1"
        require(expected.count(before) == 1, "Unique top-level second-stage pull-down")
        expected = expected.replace(before, after)
    require(circuit(actual) == circuit(expected), "Only exact two-pull-down V8 to V9 reference delta")
    reference_texts = {k: v for k, v in texts.items() if k not in ("hybrid-open.spice", previous.CHAIN.name)}
    reference_texts[REFERENCE.name] = actual
    rows = n.graph(reference_texts, [("nssoc_clock_div4_hbt_v9", "xchain.xdiv", ["clkp", "clkn", "qp", "qn", "dvdd", "0", "0"])])
    old = {r["path"]: r for r in nominal if r["path"].startswith("xchain.xdiv.")}
    new = {r["path"]: r for r in rows}
    require(len(rows) == len(new) == len(old) == 73 and set(new) == set(old), "All73 exact source identities")
    changed = {name for name in new if new[name] != old[name]}
    caps = {"xchain.xdiv.xcp", "xchain.xdiv.xcn"}
    pulls = {"xchain.xdiv.xdp", "xchain.xdiv.xdn"}
    require(changed == caps | pulls, "Historical two Cap24 plus only two Bias8 pull-downs")
    for name in caps:
        require(old[name]["model"] == "cap_cmim" and old[name]["params"] == {"w": "20u", "l": "20u"}, "Exact original two-MIM parameters")
        require(new[name] == dict(old[name], params={"w": "24u", "l": "24u"}), "Retain exact two Cap24 widths and lengths")
    for name in pulls:
        require(old[name]["model"] == "rppd" and old[name]["params"] == {"w": "1u", "l": "7u", "b": "0", "sw_et": "1"}, "Exact original top-level pull-down parameters")
        require(new[name] == dict(old[name], params=dict(old[name]["params"], l="8u")), "Only top-level pull-down lengths become8um")
    return rows, actual
