def rppd_template(width, length, tech, dbu):
    """Independent Decimal geometry of only the frozen straight W1/L7-or8 PCell.

    SG13G2 rppd_code.py rules: one unbent stripe with bar contacts, no dogbone.
    Actual native polygons must equal all nine drawing/pin layer rectangles.
    """
    D = lambda value: Decimal(str(value))
    w, length, unit = D(width), D(length), D(dbu)
    require(w == D(1) and length in (D(7), D(8)) and unit == D("0.001"), "Only declared straight pull-down geometry and exact DBU")
    keys = ("grid", "M1_c1", "Cnt_a", "Cnt_b", "Cnt_d", "Rppd_b", "Sal_e", "Sal_c", "CntB_a1", "CntB_d", "rppd_met_over_cont", "epsilon1")
    values = tuple(D(tech[k]) for k in keys)
    require(values == tuple(map(D,[".005", ".05", ".16", ".18", ".07", ".18", ".2", ".2", ".34", ".07", ".07", ".001"])), "Exact frozen native straight resistor constants")
    grid, endcap, cut, spacing, polyover, psdover, salgap, salover, barmin, barover, metover, epsilon = values
    require(w - 2 * barover + epsilon >= barmin, "Actual W1 resistor uses native bar contacts")
    polyend = cut + polyover
    regions = {}
    def box(layer, datatype, coords):
        integer = [v / unit for v in coords]
        require(all(v == v.to_integral_value() for v in integer), "All independent resistor rectangles use exact DBU")
        regions.setdefault((layer, datatype), pya.Region()).insert(pya.Box(*map(int,integer)))
    # Body layers and both end enclosures are merged, just like native regions.
    for layer in (128,52): box(layer,0,(D(0),D(0),w,length))
    for layer in (28,111): box(layer,0,(-salover,D(0),w+salover,length))
    box(14,0,(-psdover,D(0),w+psdover,length))
    for y0,y1 in ((-salgap-polyend,D(0)),(length,length+salgap+polyend)):
        box(5,0,(D(0),y0,w,y1))
    for y0,y1 in ((-salgap-psdover-polyend,D(0)),(length,length+salgap+psdover+polyend)):
        for layer in (14,111): box(layer,0,(-psdover,y0,w+psdover,y1))
    for y0,y1 in ((-salgap-cut,-salgap),(length+salgap,length+salgap+cut)):
        box(6,0,(barover,y0,w-barover,y1))
        for datatype in (0,2): box(8,datatype,(barover-endcap,y0-metover,w-barover+endcap,y1+metover))
    return {key:region.merged() for key,region in regions.items()}


def compare_intrinsics(old_instances, new_instances, before, after, dbu, tech):
    ignored = {"placement_um", "bbox_um"}
    a = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in before["instances"]}
    b = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in after["instances"]}
    require(set(a) == set(b) and len(a) == 91, "Exact 91 original intrinsic identities")
    for name, old_metadata in a.items():
        expected = dict(old_metadata)
        if expected.get("source_subcircuit") == "NSSOC_CLOCK_DIV4_HBT_V8":
            expected["source_subcircuit"] = "NSSOC_CLOCK_DIV4_HBT_V9"
        if name in PULLDOWNS:
            require(expected["kind"] == "resistor" and expected["width_um"] == 1 and expected["length_um"] == 7, "Exact two original second-stage W1/L7 pull-downs")
            expected.update(length_um=8.0)
        require(b[name] == expected, "Only two declared pull-down lengths change; all 91-device connections and other bias retained")
    old, oldvias = primitive_matches(old_instances, before["instances"], before["origin_translation_um"], dbu)
    new, newvias = primitive_matches(new_instances, after["instances"], after["origin_translation_um"], dbu)
    for name in old:
        if name in PULLDOWNS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(rppd_template(1,7,tech,dbu)), "Exact original pull-down equals independent native resistor rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(rppd_template(1,8,tech,dbu)), "Exact changed pull-down equals independent native resistor rectangle formula")
        elif name in CAPS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact original Cap24 MIM equals independent native rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact retained Cap24 MIM equals independent native rectangle formula")
        else:
            require(geometry_key(old[name]["geometry"]) == geometry_key(new[name]["geometry"]), "Exact unchanged intrinsic native geometry")
    require(Counter(geometry_key(v["geometry"]) for v in oldvias) == Counter(geometry_key(v["geometry"]) for v in newvias), "Exact unchanged native via geometry multiset")
    return newvias
