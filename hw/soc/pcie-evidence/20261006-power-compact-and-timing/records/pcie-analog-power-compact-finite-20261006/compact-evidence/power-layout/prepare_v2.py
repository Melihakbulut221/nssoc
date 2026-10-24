from pathlib import Path
R=Path.cwd();F=R/'hw/soc/flow';T=R/'sw/tests';B=Path(__file__).resolve().parent
p=F/'make_pcie_clock_div4_v7_power_v1.py';s=p.read_text().replace('power v1','power v2').replace('nssoc_clock_div4_v7_power_v1_layout','nssoc_clock_div4_v7_power_v2_layout');assert s.count('vn_columns=3,')==1;s=s.replace('vn_columns=3,','vn_columns=2,');q=F/'make_pcie_clock_div4_v7_power_v2.py';assert not q.exists();q.write_text(s)
p=F/'check_pcie_clock_div4_v7_power_v1.py';s=p.read_text().replace('power v1','power v2').replace('make_pcie_clock_div4_v7_power_v1','make_pcie_clock_div4_v7_power_v2').replace('check_pcie_clock_div4_v7_power_v1','check_pcie_clock_div4_v7_power_v2').replace('audit_pcie_clock_div4_v7_power_v1','audit_pcie_clock_div4_v7_power_v2').replace('POWER_V1','POWER_V2').replace('THREE_GEOMETRY_CONTROLS','FOUR_GEOMETRY_CONTROLS');s=s.replace('"--baseline",\n                "/dev/shm/nssoc-div4-v7-layout-01",','"--baseline",\n                "/dev/shm/nssoc-div4-v7-layout-01",\n                "--pdk",\n                pdk,');q=F/'check_pcie_clock_div4_v7_power_v2.py';assert not q.exists();q.write_text(s)
for n in ['layout','native']:
 p=T/f'test_pcie_clock_div4_v7_power_v1_{n}.py';q=T/f'test_pcie_clock_div4_v7_power_v2_{n}.py';assert not q.exists();q.write_text(p.read_text().replace('power_v1','power_v2'))
p=B/'launch01.py';q=B/'launch02.py';assert not q.exists();q.write_text(p.read_text().replace('manifest01','manifest02').replace('checkpoint01','checkpoint02').replace('POWER_V1','POWER_V2').replace('power-v1-','power-v2-').replace('power_v1.py','power_v2.py'))
p=F/'audit_pcie_clock_div4_v7_power_v1.py';q=F/'audit_pcie_clock_div4_v7_power_v2.py';s=p.read_text().replace('power_v1_layout','power_v2_layout').replace('Three\nin-memory','Four\nin-memory').replace('THREE_GEOMETRY_CONTROLS','FOUR_GEOMETRY_CONTROLS').replace('Three actual in-memory','Four actual in-memory')
insert='''def via_template(parameters, tech, dbu):
    """Independent layer/cut rectangles for only the declared 2x3/2x2 stacks."""
    bottom = parameters["b_layer"]
    require(parameters == dict(b_layer=bottom, t_layer="TopMetal2",
                              vn_columns=2, vn_rows=3, vt1_columns=2,
                              vt1_rows=2, vt2_columns=2, vt2_rows=2),
            "Exact declared native power via parameters")
    require(bottom in ("Metal4", "Metal5", "TopMetal1"), "Supported power via bottom")
    regions = {}
    def rectangle(layer, box):
        regions.setdefault((layer, 0), pya.Region()).insert(pya.DBox(*box).to_itype(dbu))
    def array(layer, nx, ny, size, space):
        wx, wy = nx * size + (nx - 1) * space, ny * size + (ny - 1) * space
        for i in range(nx):
            for j in range(ny):
                x, y = i * (size + space) - wx / 2, j * (size + space) - wy / 2
                rectangle(layer, (x, y, x + size, y + size))
        return wx, wy
    if bottom == "Metal4":
        wx, wy = array(66, 2, 3, tech["Vn_a"], tech["Vn_b"])
        enc = tech["Vn_c1"]
        rectangle(50, (-wx/2-enc, -wy/2-enc, wx/2+enc, wy/2+enc))
    if bottom in ("Metal4", "Metal5"):
        wx, wy = array(125, 2, 2, tech["TV1_a"], tech["TV1_b"])
        enc = tech["TV1_c"]
        rectangle(67, (-wx/2-enc, -wy/2-enc, wx/2+enc, wy/2+enc))
        # The inner generic M5 rectangle and the Top1 lower-via enclosure
        # are wholly covered by these larger declared outer enclosures.
    wx, wy = array(133, 2, 2, tech["TV2_a"], tech["TV2_b"])
    for layer, enc in ((126, tech["TV2_c"]), (134, tech["TV2_d"])):
        rectangle(layer, (-wx/2-enc, -wy/2-enc, wx/2+enc, wy/2+enc))
    return {k: v.merged() for k, v in regions.items()}


def top_instances(path, topname):
    layout = pya.Layout()
    layout.read(str(path))
    top = layout.cell(topname)
    result = []
    for instance in top.each_inst():
        require(not instance.is_regular_array(), "Only original explicit native instances")
        cell = layout.cell(instance.cell_index)
        require(not list(cell.each_inst()), "All original native cells are leaves")
        shapes = {}
        for index in layout.layer_indexes():
            info = layout.get_info(index)
            region = pya.Region(cell.begin_shapes_rec(index)).merged()
            if not region.is_empty():
                shapes[(info.layer, info.datatype)] = region
        result.append(dict(key=(cell.name, instance.cplx_trans.to_s()),
                           cell=cell.name, transform=instance.cplx_trans,
                           geometry=shapes))
    return layout.dbu, result


def compare_instances(oldrows, newrows, declared, translation, dbu, tech):
    old = Counter(row["key"] for row in oldrows)
    new = Counter(row["key"] for row in newrows)
    require(sum(old.values()) == 678 and sum(new.values()) == 725,
            "Exact original 678 and new 725 native instances")
    require(not (old - new), "Every original native instance retained")
    oldmap = {row["key"]: row["geometry"] for row in oldrows}
    remaining = Counter(old)
    extras = []
    for row in newrows:
        if remaining[row["key"]]:
            before = oldmap[row["key"]]
            require(set(before) == set(row["geometry"]) and
                    all((before[k] ^ row["geometry"][k]).is_empty() for k in before),
                    "Every original native cell geometry unchanged")
            remaining[row["key"]] -= 1
        else:
            extras.append(row)
    require(len(extras) == len(declared) == 47, "Exact 47 added via instances")
    used = set()
    for target in declared:
        x, y = [target["center_um"][i] + translation[i] for i in (0, 1)]
        trans = pya.ICplxTrans(1.0, 0.0, False, round(x/dbu), round(y/dbu))
        found = [i for i, row in enumerate(extras) if row["transform"] == trans]
        require(len(found) == 1 and found[0] not in used, "Unique actual power via at every declared center")
        index = found[0]
        used.add(index)
        row = extras[index]
        require(row["cell"].split("$")[0] == "via_stack", "Actual native via cell class")
        expected = via_template(target["parameters"], tech, dbu)
        require(set(row["geometry"]) == set(expected) and
                all((row["geometry"][k] ^ expected[k]).is_empty() for k in expected),
                "Actual native power via cut/enclosure geometry differs")
    require(len(used) == 47, "Every new native via instance bound")
    return extras


'''
s=s.replace('def main():\n',insert+'def main():\n')
s=s.replace('    parser.add_argument("--out", type=Path, required=True)','    parser.add_argument("--out", type=Path, required=True)\n    parser.add_argument("--pdk", type=Path, required=True)')
s=s.replace('    before = json.loads(oldr.read_text())','    techpath = args.pdk / "libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json"\n    inputs[str(techpath)] = pin(techpath)\n    tech = json.loads(techpath.read_text())["techParams"]\n    before = json.loads(oldr.read_text())')
s=s.replace('    controls = []\n','''    idbu, old_instances = top_instances(oldg, OLD_TOP)
    jdbu, new_instances = top_instances(newg, NEW_TOP)
    require(idbu == jdbu == newdbu, "Actual instance and drawing grids equal")
    extras = compare_instances(old_instances, new_instances, after["additive_power_vias"],
                              after["origin_translation_um"], newdbu, tech)
    controls = []
''')
s=s.replace('    require(inputs == {p: pin(p) for p in inputs}, "Saved native input bytes unchanged")','''    # Drop only one added branch's actual Via4 geometry, keeping all original
    # instances and every upper strap. Broad region/subset or LVS can miss this;
    # the exact added instance binding must reject it for the declared cause.
    victim = next(row for row in extras if (66, 0) in row["geometry"])
    bad_instances = [dict(row, geometry=dict(row["geometry"])) for row in new_instances]
    matching = [row for row in bad_instances if row["key"] == victim["key"]]
    require(len(matching) == 1, "Unique actual Via4 corruption target")
    del matching[0]["geometry"][(66, 0)]
    try:
        compare_instances(old_instances, bad_instances, after["additive_power_vias"],
                          after["origin_translation_um"], newdbu, tech)
    except ValueError as error:
        require(str(error) == "Actual native power via cut/enclosure geometry differs",
                "Via4 corruption rejected for exact intended cause")
        controls.append(dict(fault="remove_one_added_via4_array", status="EXPECTED_REJECTION",
                             diagnostic=str(error), instance=list(victim["key"])))
    else:
        raise ValueError("Actual added Via4 removal was accepted")
    require(inputs == {p: pin(p) for p in inputs}, "Saved native input bytes unchanged")''')
s=s.replace('        native_via_arrays=47,','        native_via_arrays=47,\n        original_native_instances=678,\n        added_native_instances=47,\n        exact_native_cut_and_enclosure_geometry=True,')
assert not q.exists();q.write_text(s)
