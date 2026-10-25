from pathlib import Path
import json,hashlib,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;F=R/'hw/soc/flow'
p=F/'audit_pcie_clock_div4_v7_power_v2.py';s=p.read_text().replace('import json\n','import json\nimport struct\n')
s=s.replace('return layout.dbu, cell.bbox(), regions, texts','return layout, cell.bbox(), regions, texts').replace('return layout.dbu, result','return layout, result')
s=s.replace('olddbu, oldbox, old, oldtexts = read_layout(oldg, OLD_TOP)','old_layout, oldbox, old, oldtexts = read_layout(oldg, OLD_TOP)\n    olddbu = old_layout.dbu').replace('newdbu, newbox, new, newtexts = read_layout(newg, NEW_TOP)','new_layout, newbox, new, newtexts = read_layout(newg, NEW_TOP)\n    newdbu = new_layout.dbu')
s=s.replace('idbu, old_instances = top_instances(oldg, OLD_TOP)','old_instance_layout, old_instances = top_instances(oldg, OLD_TOP)\n    idbu = old_instance_layout.dbu').replace('jdbu, new_instances = top_instances(newg, NEW_TOP)','new_instance_layout, new_instances = top_instances(newg, NEW_TOP)\n    jdbu = new_instance_layout.dbu')
insert='''def raw_gds_regions(path, wanted):
    """Independent GDS boundary-record read, not the Layout/recursive iterator."""
    data = Path(path).read_bytes()
    at, cell, element = 0, None, None
    result = {}
    while at < len(data):
        require(at + 4 <= len(data), "Complete raw GDS header")
        size, kind, dtype = struct.unpack(">HBB", data[at:at+4])
        require(size >= 4 and at + size <= len(data), "Complete raw GDS record")
        payload = data[at+4:at+size]
        at += size
        if kind == 6:
            cell = payload.rstrip(b"\\x00").decode("ascii")
        elif kind == 8:
            element = {} if cell in wanted else None
        elif cell in wanted and kind in (9, 10, 11, 12, 45):
            raise ValueError("Selected native via cell must contain only boundary geometry")
        elif kind == 13 and element is not None:
            element["layer"] = struct.unpack(">h", payload)[0]
        elif kind == 14 and element is not None:
            element["datatype"] = struct.unpack(">h", payload)[0]
        elif kind == 16 and element is not None:
            require(len(payload) % 8 == 0, "Whole raw GDS XY point pairs")
            element["xy"] = list(struct.unpack(">" + "i" * (len(payload)//4), payload))
        elif kind == 17:
            if element is not None:
                require(set(element) == {"layer", "datatype", "xy"}, "Complete raw native via polygon")
                coordinates = element["xy"]
                points = [pya.Point(coordinates[i], coordinates[i+1]) for i in range(0, len(coordinates), 2)]
                require(len(points) == 5 and points[0] == points[-1], "Exact native via rectangular boundary")
                polygon = pya.Polygon(points[:-1])
                require(polygon.area() == polygon.bbox().area(), "Actual raw via rectangle")
                key = (element["layer"], element["datatype"])
                result.setdefault(cell, {}).setdefault(key, pya.Region()).insert(polygon)
            element = None
    require(set(result) == wanted, "All actual native via cell classes in raw GDS")
    return {name: {layer: region.merged() for layer, region in rows.items()} for name, rows in result.items()}


'''
s=s.replace('def main():\n',insert+'def main():\n')
needle='    controls = []\n';s=s.replace(needle,'''    raw_vias = raw_gds_regions(newg, {row["cell"] for row in extras})
    for row in extras:
        raw = raw_vias[row["cell"]]
        require(set(raw) == set(row["geometry"]) and
                all((raw[k] ^ row["geometry"][k]).is_empty() for k in raw),
                "All 47 retained-layout via regions equal independent raw GDS boundaries")
    controls = []
''')
s=s.replace('exact_native_cut_and_enclosure_geometry=True,','exact_native_cut_and_enclosure_geometry=True,\n        retained_layout_owners_through_audit=True,\n        independent_raw_gds_boundary_instances_verified=47,')
q=F/'audit_pcie_clock_div4_v7_power_v3.py';assert not q.exists();q.write_text(s)
p=F/'check_pcie_clock_div4_v7_power_v2.py';s=p.read_text().replace('audit_pcie_clock_div4_v7_power_v2.py','audit_pcie_clock_div4_v7_power_v3.py').replace('"check_pcie_clock_div4_v7_power_v2.py",','"check_pcie_clock_div4_v7_power_v2.py",\n        "check_pcie_clock_div4_v7_power_v2_audit_v3.py",');q=F/'check_pcie_clock_div4_v7_power_v2_audit_v3.py';assert not q.exists();q.write_text(s)
p=B/'launch02.py';s=p.read_text().replace('manifest02','manifest03').replace('checkpoint02','checkpoint03').replace('PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2','PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2_AUDIT_V3').replace('check_pcie_clock_div4_v7_power_v2.py','check_pcie_clock_div4_v7_power_v2_audit_v3.py').replace(", '--generate'",'')
a="""    if any(p.exists() or p.parent != Path('/dev/shm') or not p.name.startswith('nssoc-div4-v7-power-v2-') for p in roots):
        raise ValueError('Exact fresh native scratch roots required')"""
z="""    if not roots[0].is_dir() or roots[1].exists() or any(p.parent != Path('/dev/shm') or not p.name.startswith('nssoc-div4-v7-power-v2-') for p in roots):
        raise ValueError('Exact saved generated layout and fresh native checker root required')
    if {str(p.relative_to(roots[0])):pin(p) for p in roots[0].rglob('*') if p.is_file()} != manifest['layout_files']:
        raise ValueError('Every actual generated layout byte remains exact')"""
assert a in s;s=s.replace(a,z);q=B/'launch03.py';assert not q.exists();q.write_text(s)
