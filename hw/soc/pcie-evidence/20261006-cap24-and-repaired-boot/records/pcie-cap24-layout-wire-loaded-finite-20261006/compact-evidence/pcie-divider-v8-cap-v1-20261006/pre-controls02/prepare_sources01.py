from pathlib import Path
import hashlib
R=Path.cwd();F=R/'hw/soc/flow';B=Path(__file__).resolve().parent
old=F/'audit_pcie_clock_div4_v7_compact_v2.py';s=old.read_text()
s=s.replace('Strict saved-GDS compact placement, intrinsic geometry and power-via audit.','Strict saved-GDS two-capacitor geometry delta and unchanged intrinsic audit.')
s=s.replace('from collections import Counter','from collections import Counter\nfrom decimal import Decimal, ROUND_FLOOR')
s=s.replace('OLD_TOP = "nssoc_clock_div4_v7_power_v2_layout"','OLD_TOP = "nssoc_clock_div4_v7_compact_v2_layout"').replace('NEW_TOP = "nssoc_clock_div4_v7_compact_v2_layout"','NEW_TOP = "nssoc_clock_div4_v8_cap_v1_layout"')
s=s.replace('663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c','db400e586cadbedbea9ec8aec5466c0eba4789e262c90ebd0d321a1c2cbcf579').replace('bf34cad3dbdee3f443c275f50fb7008d612f1f970b6c3c63abd51df2582513be','208d2063593a500aea6c840b4600228e1e4ae550d5f7c364e95b4d089c8e8380')
start=s.index('def compare_intrinsics(');end=s.index('\ndef power_arrays(',start)
s=s[:start]+'''CAPS = {"DIV__XCP", "DIV__XCN"}


def mim_template(width, length, tech, dbu):
    """Independent Decimal rectangles from frozen SG13 cmim rules, no PCell call."""
    D = lambda value: Decimal(str(value))
    w, length, unit = D(width), D(length), D(dbu)
    grid, epsilon = D("0.005"), D(tech["epsilon1"])
    cut, over, enclosure = (D(tech[k]) for k in ("TV1_a", "Mim_d", "TV1_d"))
    spacing, bottom = D("0.84"), D(tech["Mim_c"])
    require((cut, over, enclosure, bottom, epsilon) == tuple(map(D, ["0.42", "0.36", "0.42", "0.6", "0.001"])), "Frozen native MIM technology constants")
    require(w in (D(20), D(24)) and length == w and unit == D("0.001"), "Only declared old/new square MIM at actual DBU")
    def axis(size):
        count = int(((size - 2 * over + spacing) / (cut + spacing) + epsilon).to_integral_value(rounding=ROUND_FLOOR))
        span = count * (cut + spacing) - spacing + 2 * over
        offset = (((size - span) / 2 / grid + epsilon).to_integral_value(rounding=ROUND_FLOOR)) * grid
        points = []
        at = over + offset
        while at + cut + over <= size + epsilon:
            points.append(at)
            at += cut + spacing
        require(len(points) == count, "Independent native MIM cut count")
        return points, over - enclosure + offset, at + enclosure - spacing
    xs, left, right = axis(w)
    ys, lower, upper = axis(length)
    regions = {}
    def box(layer, coordinates):
        integer = [v / unit for v in coordinates]
        require(all(v == v.to_integral_value() for v in integer), "All native MIM coordinates lie on exact DBU")
        regions.setdefault((layer, 0), pya.Region()).insert(pya.Box(*map(int, integer)))
    for x in xs:
        for y in ys:
            box(129, (x, y, x + cut, y + cut))
    box(36, (D(0), D(0), w, length))
    box(67, (-bottom, -bottom, w + bottom, length + bottom))
    box(126, (left, lower, right, upper))
    return {key: region.merged() for key, region in regions.items()}


def compare_intrinsics(old_instances, new_instances, before, after, dbu, tech):
    ignored = {"placement_um", "bbox_um"}
    a = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in before["instances"]}
    b = {r["name"]: {k: v for k, v in r.items() if k not in ignored} for r in after["instances"]}
    require(set(a) == set(b) and len(a) == 91, "Exact 91 original intrinsic identities")
    for name, old_metadata in a.items():
        expected = dict(old_metadata)
        if expected.get("source_subcircuit") == "NSSOC_CLOCK_DIV4_HBT_V7":
            expected["source_subcircuit"] = "NSSOC_CLOCK_DIV4_HBT_V8"
        if name in CAPS:
            require(expected["kind"] == "capacitor" and expected["width_um"] == expected["length_um"] == 20, "Exact two original second-stage 20um MIMs")
            expected.update(width_um=24.0, length_um=24.0)
        require(b[name] == expected, "Only two declared MIM dimensions change; all 91-device connections and DC bias retained")
    old, oldvias = primitive_matches(old_instances, before["instances"], before["origin_translation_um"], dbu)
    new, newvias = primitive_matches(new_instances, after["instances"], after["origin_translation_um"], dbu)
    for name in old:
        if name in CAPS:
            require(geometry_key(old[name]["geometry"]) == geometry_key(mim_template(20, 20, tech, dbu)), "Exact original MIM equals independent native rectangle formula")
            require(geometry_key(new[name]["geometry"]) == geometry_key(mim_template(24, 24, tech, dbu)), "Exact changed MIM equals independent native rectangle formula")
        else:
            require(geometry_key(old[name]["geometry"]) == geometry_key(new[name]["geometry"]), "Exact unchanged intrinsic native geometry")
    require(Counter(geometry_key(v["geometry"]) for v in oldvias) == Counter(geometry_key(v["geometry"]) for v in newvias), "Exact unchanged native via geometry multiset")
    return newvias

''' + s[end:]
s=s.replace('Exact frozen PowerV2 baseline','Exact frozen CompactV2 baseline')
s=s.replace('    require(before["source_circuit_sha256"]==after["source_circuit_sha256"] and before["primitive_counts"]==after["primitive_counts"],"Exact frozen source graph and primitive counts")', '''    expected_sources = dict(before["source_circuit_sha256"])
    require(expected_sources.pop("hw/soc/analog/pcie/clock_div4_hbt_v7.spice") == "49226d5b3a40fc4f8faafbaee3adb5580d8346222a825b79daaddc0358b2c65c", "Exact prior top circuit")
    expected_sources["hw/soc/analog/pcie/clock_div4_hbt_v8.spice"] = "87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc"
    require(expected_sources == after["source_circuit_sha256"] and before["primitive_counts"]==after["primitive_counts"],"Exact separately frozen two-cap source graph and primitive counts")''')
s=s.replace('    vias=compare_intrinsics(old_instances,new_instances,before,after,dbu)\n    tech=json.loads(techpath.read_text())["techParams"]','    tech=json.loads(techpath.read_text())["techParams"]\n    vias=compare_intrinsics(old_instances,new_instances,before,after,dbu,tech)')
s=s.replace('compare_intrinsics(old_instances,bad,before,after,dbu)', 'compare_intrinsics(old_instances,bad,before,after,dbu,tech)')
needle='    require(inputs=={p:pin(p) for p in inputs},"Saved actual input bytes unchanged")'
extra='''    selected,_=primitive_matches(new_instances,after["instances"],after["origin_translation_um"],dbu)
    for fault,geometry in (("remove_actual_changed_mim_plate", dict(selected["DIV__XCP"]["geometry"], **{})), ("restore_undersized_actual_mim", mim_template(20,20,tech,dbu))):
        if fault == "remove_actual_changed_mim_plate":
            geometry[(36,0)] = pya.Region()
        bad=[dict(r,geometry=geometry) if r is selected["DIV__XCP"] else r for r in new_instances]
        reject(fault,"Exact changed MIM equals independent native rectangle formula",lambda:compare_intrinsics(old_instances,bad,before,after,dbu,tech))
'''
s=s.replace(needle,extra+needle)
s=s.replace('PASS_ACTUAL_COMPACT_INTRINSICS_POWER_AND_FOUR_GEOMETRY_CONTROLS','PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS')
s=s.replace('physical_primitives=91,native_instances=725','changed_mim_dimensions_um={n:[20,24] for n in sorted(CAPS)},unchanged_intrinsics=89,physical_primitives=91,native_instances=725')
(F/'audit_pcie_clock_div4_v8_cap_v1.py').write_text(s)
s=(F/'check_pcie_clock_div4_v7_compact_v2.py').read_text().replace('v7_compact_v2','v8_cap_v1').replace('v7 compact v2','v8 cap v1').replace('V7_COMPACT_V2','V8_CAP_V1')
s=s.replace('/dev/shm/nssoc-div4-v7-power-v2-layout-01','/dev/shm/nssoc-div4-v7-compact-v2-layout-01').replace('nssoc_clock_div4_v7_power_v2_layout.gds','nssoc_clock_div4_v7_compact_v2_layout.gds')
s=s.replace('PASS_ACTUAL_COMPACT_INTRINSICS_POWER_AND_FOUR_GEOMETRY_CONTROLS','PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS').replace('Actual unchanged intrinsic geometry and compact power topology verified','Actual two-cap geometry delta and all remaining intrinsic geometry verified')
(F/'check_pcie_clock_div4_v8_cap_v1.py').write_text(s)
# Test harness retains all actual lifecycle controls; native syntax fixture is
# explicitly a two-field synthetic derivative, never new extraction evidence.
for suffix in ['layout','native']:
 p=R/f'sw/tests/test_pcie_clock_div4_v7_compact_v2_{suffix}.py';s=p.read_text().replace('v7_compact_v2','v8_cap_v1')
 if suffix=='layout':
  s=s.replace('nssoc_clock_div4_hbt_v7','nssoc_clock_div4_hbt_v8').replace('clock_div4_hbt_v7.spice','clock_div4_hbt_v8.spice')
  a=s.index('    # Keep all connection');b=s.index('\n\ndef test_compact_planner',a)
  s=s[:a]+'''    import make_pcie_clock_div4_v7_compact_v2 as old
    changed = []
    for before, after in zip(old.devices(ROOT), m.devices(ROOT), strict=True):
        before = dict(before, source_subcircuit=after["source_subcircuit"])
        if before != after:
            assert before["width_um"] == before["length_um"] == 20
            assert after == dict(before, width_um=24, length_um=24)
            changed.append(after["name"])
    assert changed == ["DIV__XCP", "DIV__XCN"]
''' +s[b:]
  s=s.replace('    assert rows == old.devices(ROOT)','    assert len(rows) == len(old.devices(ROOT)) == 73')
  # Wider cap uses same36pitch, so minimum envelope is2.4 ratherthan6.4um;
  # retain old5um expectation for every unchanged primitive.
  s=s.replace('assert plan[after][1]-9-(plan[before][1]+right) >= 5','assert plan[after][1]-9-(plan[before][1]+right) >= (2.4 if before in {"DIV__XCP", "DIV__XCN"} else 5)')
  s=s.replace('    return data.decode()', '    text=data.decode()\n    assert text.count("w=20u l=20u A=400p P=80u") == 2\n    return text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")')
 else:
  s=s.replace('    return text\n','    assert text.count("w=20u l=20u A=400p P=80u") == 2\n    return text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")\n')
  s=s.replace('w=20u l=20u A=400p P=80u", "w=10u','w=24u l=24u A=576p P=96u", "w=10u')
  # Only mutation targets in parametrization become new A/P; fixture transform stays literal.
  a=s.index('@pytest.mark.parametrize(');s=s[:a]+s[a:].replace('A=400p','A=576p').replace('P=80u','P=96u')
 (R/f'sw/tests/test_pcie_clock_div4_v8_cap_v1_{suffix}.py').write_text(s)
