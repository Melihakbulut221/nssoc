from pathlib import Path
import hashlib,json,difflib
R=Path.cwd();B=R/'hw/soc/out/pcie-divider-v7-power-v1-20261005';F=R/'hw/soc/flow';T=R/'sw/tests'
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
bridges=[]
def save(old,new,text):
 assert not new.exists();before=old.read_text();new.write_text(text)
 a=before.splitlines(keepends=True);b=text.splitlines(keepends=True)
 ops=[{'tag':t,'before':''.join(a[i:j]),'after':''.join(b[k:l])} for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()]
 assert ''.join(x['before'] for x in ops)==before and ''.join(x['after'] for x in ops)==text
 bridges.append({'before':pin(old),'after':pin(new),'opcodes':ops})
old=F/'make_pcie_clock_div4_v7.py';s=old.read_text()
s=s.replace('Standalone native divider v7 with L4 conditioner; preserves all prior layouts.','Standalone divider v7 power v1: parallel upper-metal power straps only.')
s=s.replace('TOP = "nssoc_clock_div4_v7_layout"','TOP = "nssoc_clock_div4_v7_power_v1_layout"')
needle='    box = top.dbbox()\n    dx, dy = -box.left, -box.bottom\n'
assert s.count(needle)==1
block='''    # Add only supply routing above the original geometry. Long thin M5 buses
    # and M4 cross-row trunks caused measured ground rise in the frozen wire
    # simulation; primitive topology, placements and every old route stay exact.
    # MIM plates are in the isolated device bands, below these row bus tracks.
    power_straps, power_vias = [], []

    def power_rect(layer, net, x1, y1, x2, y2, role):
        b = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[layer], 0)).insert(b)
        power_straps.append(dict(net=net, layer=layer, role=role,
                                 rect_um=[b.left, b.bottom, b.right, b.top]))

    def power_via(bottom, upper, x, y, net, role):
        parameters = dict(b_layer=bottom, t_layer=upper,
                          vn_columns=3, vn_rows=3,
                          vt1_columns=2, vt1_rows=2,
                          vt2_columns=2, vt2_rows=2)
        cell = pc("via_stack", parameters)
        b = cell.dbbox()
        t = instance(cell, x - b.center().x, y - b.center().y)
        b = b.transformed(t)
        if b.width() > 6 or b.height() > 6:
            raise ValueError("Power native via array outside six-micron corridor")
        power_vias.append(dict(net=net, role=role, parameters=parameters,
                               center_um=[x, y], bbox_um=str(b)))

    for net, trunk_x in (("DIV_AVDD", 96.0), ("AVSS", 112.0)):
        selected = [b for b in buses if b["net"] == net]
        if [b["row"] for b in selected] != [0, 1, 2]:
            raise ValueError("All three actual power row buses required")
        power_rect("TopMetal1", net, trunk_x - 3, selected[0]["y_um"] - 3,
                   trunk_x + 3, selected[-1]["y_um"] + 3, "cross_row_trunk")
        for bus in selected:
            rid, y = bus["row"], bus["y_um"]
            left, right = bus["left_um"], bus["right_um"]
            if not (left <= trunk_x - 3 and trunk_x + 3 <= right):
                raise ValueError("Power trunk must overlap existing actual bus extent")
            power_rect("TopMetal2", net, left, y - 3, right, y + 3, "row_bus")
            power_via("TopMetal1", "TopMetal2", trunk_x, y, net, "trunk_join")
            for _, x, start in [t for t in terminals[net] if t[0] == rid]:
                if not row_starts[rid] <= start < row_starts[rid] + 85:
                    raise ValueError("Actual power branch outside original device band")
                power_via("Metal4", "TopMetal2", x, y, net, "actual_branch")
            if rid == 0:
                # Existing M5 pin and old bus remain unchanged; join at x=2 so
                # the entire native upper-via enclosure stays inside the macro.
                power_via("Metal5", "TopMetal2", 2.0, y, net, "public_port")
    if len(power_straps) != 8:
        raise ValueError("Exact six row straps and two cross-row power trunks")
    box = top.dbbox()
    dx, dy = -box.left, -box.bottom
'''
s=s.replace(needle,block)
s=s.replace('        local_buses=buses,','        local_buses=buses,\n        additive_power_straps=power_straps,\n        additive_power_vias=power_vias,')
s=s.replace('scope="Exact standalone divider v7, L4 first conditioner, 73 primitives and 18 finite substrate contacts. "','scope="Exact standalone divider v7 power v1, L4 first conditioner, 73 primitives and 18 finite substrate contacts. "\n        "Original geometry retained with additive TopMetal2 power row straps and TopMetal1 power trunks. "')
save(old,F/'make_pcie_clock_div4_v7_power_v1.py',s)
old=F/'check_pcie_clock_div4_v7_v2.py';s=old.read_text()
s=s.replace('Native divider v7 checker v2: exact extracted passive ps/area/perimeter fields.','Native divider v7 power v1: unchanged strict native circuit and fault checks.')
s=s.replace('from make_pcie_clock_div4_v7 import (','from make_pcie_clock_div4_v7_power_v1 import (')
s=s.replace('root / "hw/soc/flow/make_pcie_clock_div4_v7.py",','root / "hw/soc/flow/make_pcie_clock_div4_v7_power_v1.py",')
s=s.replace('        "make_pcie_clock_div4_v7.py",','        "make_pcie_clock_div4_v7.py",\n        "make_pcie_clock_div4_v7_power_v1.py",\n        "check_pcie_clock_div4_v7_power_v1.py",')
s=s.replace('Actual standalone divider v7 connectivity and main-rule screen only;','Actual standalone divider v7 power v1 connectivity and main-rule screen only;')
s=s.replace('PASS_DIV4_V7_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY','PASS_DIV4_V7_POWER_V1_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY')
save(old,F/'check_pcie_clock_div4_v7_power_v1.py',s)
old=T/'test_pcie_clock_div4_v7_layout.py';s=old.read_text().replace('import make_pcie_clock_div4_v7 as m','import make_pcie_clock_div4_v7_power_v1 as m').replace('import check_pcie_clock_div4_v7 as c','import check_pcie_clock_div4_v7_power_v1 as c')
save(old,T/'test_pcie_clock_div4_v7_power_v1_layout.py',s)
old=T/'test_pcie_clock_div4_v7_native_v2.py';s=old.read_text().replace('import check_pcie_clock_div4_v7_v2 as c','import check_pcie_clock_div4_v7_power_v1 as c')
save(old,T/'test_pcie_clock_div4_v7_power_v1_native.py',s)
(B/'source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n')
print(json.dumps([r['after'] for r in bridges],indent=2))
