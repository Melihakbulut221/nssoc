def compare_intrinsics(old_instances, new_instances, before, after, dbu, tech):
    ignored = {"placement_um", "bbox_um"}
    a = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in before["instances"]}
    b = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in after["instances"]}
    require(set(a) == set(b) and len(a) == 91, "Exact 91 original intrinsic identities")
    for name, old_metadata in a.items():
        expected = dict(old_metadata)
        if expected.get("source_subcircuit") == "NSSOC_CLOCK_DIV4_HBT_V9":
            expected["source_subcircuit"] = "NSSOC_CLOCK_DIV4_HBT_V10"
        if name.startswith("DIV__XSECOND__") and expected.get("source_subcircuit") == "NSSOC_CLOCK_DIV2_HBT":
            expected["source_subcircuit"] = "NSSOC_CLOCK_DIV2_TAIL_V10"
        if name in REFERENCE:
            require(expected["kind"] == "resistor" and expected["width_um"] == 1 and expected["length_um"] == 12.7, "Exact original second-stage W1/L12.7 reference")
            expected.update(length_um=11.5)
        require(b[name] == expected, "Only declared second-stage reference length changes; all91 connections and other parameters retained")
    old, oldvias = primitive_matches(old_instances, before["instances"], before["origin_translation_um"], dbu)
    new, newvias = primitive_matches(new_instances, after["instances"], after["origin_translation_um"], dbu)
    for name in old:
        if name in REFERENCE:
            require(geometry_key(old[name]["geometry"]) == geometry_key(rppd_template(1,12.7,tech,dbu)), "Exact original reference equals independent native resistor rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(rppd_template(1,11.5,tech,dbu)), "Exact changed reference equals independent native resistor rectangle formula")
        elif name in PULLDOWNS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(rppd_template(1,8,tech,dbu)), "Exact original Bias8 pull-down equals independent native resistor rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(rppd_template(1,8,tech,dbu)), "Exact retained Bias8 pull-down equals independent native resistor rectangle formula")
        elif name in CAPS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact original Cap24 MIM equals independent native rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(mim_template(24,24,tech,dbu)), "Exact retained Cap24 MIM equals independent native rectangle formula")
        else:
            require(geometry_key(old[name]["geometry"]) == geometry_key(new[name]["geometry"]), "Exact unchanged intrinsic native geometry")
    require(Counter(geometry_key(v["geometry"]) for v in oldvias) == Counter(geometry_key(v["geometry"]) for v in newvias), "Exact unchanged native via geometry multiset")
    return newvias
