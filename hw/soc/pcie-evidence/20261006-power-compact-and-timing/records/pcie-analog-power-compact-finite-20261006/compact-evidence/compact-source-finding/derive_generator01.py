from pathlib import Path
import json,hashlib,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;p=R/'hw/soc/flow/make_pcie_clock_div4_v7_power_v2.py';q=R/'hw/soc/flow/make_pcie_clock_div4_v7_compact_v1.py';old=p.read_text();s=old
s=s.replace('Standalone divider v7 power v2: parallel upper-metal power straps only.','Standalone divider v7 compact v1: unchanged devices with shorter local routes.').replace('nssoc_clock_div4_v7_power_v2_layout','nssoc_clock_div4_v7_compact_v1_layout')
a=s.index('def placement_plan(rows):');b=s.index('\n\ndef main():',a)
s=s[:a]+'''def bus_offset(ordered, net):
    """Four-micron signal pitch; eight beside each six-micron supply strap."""
    y = 72.0
    for index, current in enumerate(ordered):
        if index:
            previous = ordered[index - 1]
            y += 8.0 if {previous, current} & {"DIV_AVDD", "AVSS"} else 4.0
        if current == net:
            return y
    raise ValueError("Declared row bus absent")


def placement_plan(rows):
    """Unchanged three topology groups, local device order and 73 identities."""
    by_name = {r["name"]: r for r in rows}
    if len(rows) != 73 or len(by_name) != len(rows):
        raise ValueError("Exact 73 primitive placement census required")
    first = [n for n in by_name if n.startswith("DIV__XFIRST__")]
    second = [n for n in by_name if n.startswith("DIV__XSECOND__")]
    interstage = [n for n in by_name if n not in first + second]
    groups = [list(reversed(first)), interstage, list(reversed(second))]
    if [len(g) for g in groups] != [30, 17, 26] or set(sum(groups, [])) != set(by_name):
        raise ValueError("Topology group identities changed")
    # Explicit ordering selected from saved actual endpoint losses; it changes
    # physical track locations, never the source graph, models, or bias values.
    priority = [
        ["DIV__XFIRST__XCORE__XS__SE", "DIV__XFIRST__XCORE__XS__TE",
         "DIV__S1P", "DIV__XFIRST__XCORE__MN", "DIV__S1N",
         "DIV__XFIRST__XCORE__MP", "DIV__XFIRST__XCORE__XS__HE",
         "DIV__XFIRST__XCORE__XM__SE", "DIV__XFIRST__XCORE__XM__TE",
         "DIV__XFIRST__XCORE__XM__HE", "DIV__XFIRST__CKP",
         "DIV__XFIRST__CKN", "DIV__XFIRST__XCORE__REF"],
        ["DIV__LP", "DIV__S1P", "DIV__S1N", "DIV__LN", "DIV__LT",
         "DIV__CKP", "DIV__CKN", "DIV__LREF", "DIV__BIP", "DIV__BIN"],
        ["DIV__XSECOND__XS__TE", "DIV__XSECOND__XM__TE",
         "DIV__XSECOND__MN", "DIV__XSECOND__XS__HE",
         "DIV__XSECOND__XM__SE", "DIV__XSECOND__MP",
         "DIV__XSECOND__XS__SE", "DIV__XSECOND__XM__HE",
         "DIV__CKP", "DIV__CKN", "DIV__XSECOND__REF"],
    ]
    starts, net_rows, plan = {}, {}, {}
    base = 0.0
    for rid, group in enumerate(groups):
        nets = {"SUB"}
        for name in group:
            row = by_name[name]
            count = {"hbt": 3, "resistor": 2, "capacitor": 2}[row["kind"]]
            nets.update(row["nets"][:count])
        ordered = [n for n in PORTS if n in nets] + priority[rid]
        if len(ordered) != len(set(ordered)) or set(ordered) != nets:
            raise ValueError("Exact topology-local row net census")
        starts[rid], net_rows[rid] = base, ordered
        x = 160.0
        for name in group:
            row = by_name[name]
            if row["kind"] == "hbt":
                y = 56.0
            elif row["kind"] == "resistor":
                y = 60.0 - row["length_um"] - 0.61
            else:
                y = 60.0 - row["length_um"] - 0.60
            plan[name] = (rid, x, round((base + y) / 0.005) * 0.005)
            x += 36.0 if row["kind"] == "capacitor" and row["width_um"] == 20 else 24.0
        if x > 900.0:
            raise ValueError("Compact device band exceeds fixed 960 micron width")
        base += bus_offset(ordered, ordered[-1]) + 24.0
    return plan, starts, net_rows
''' +s[b:]
s=s.replace('180 + (index % 6) * 200.0','180 + (index % 6) * 120.0').replace('width = 1520.0','width = 960.0').replace('row_starts[rid] + 90 + row_nets[rid].index(net) * 10','row_starts[rid] + bus_offset(row_nets[rid], net)').replace('row_starts[rid] + 85','row_starts[rid] + 70')
s=s.replace('    # Add only supply routing above the original geometry. Long thin M5 buses\n    # and M4 cross-row trunks caused measured ground rise in the frozen wire\n    # simulation; primitive topology, placements and every old route stay exact.\n    # MIM plates are in the isolated device bands, below these row bus tracks.','    # Retain the validated power strap topology in the compact coordinate plan.\n    # Exact intrinsic geometry and all source connections remain unchanged;\n    # all placements and bus routes require fresh DRC/LVS/RC measurements.\n    # MIM plates remain in the isolated device bands below the bus tracks.')
s=s.replace('Three topology groups with row-local escapes/buses and peripheral cross-row trunks','Three unchanged topology groups, width-aware compact placement and loss-prioritized local tracks')
s=s.replace('Exact standalone divider v7 power v2, L4 first conditioner, 73 primitives and 18 finite substrate contacts. ','Exact standalone divider v7 compact v1, L4 first conditioner, 73 unchanged primitives and 18 finite substrate contacts. ').replace('Original geometry retained with additive TopMetal2 power row straps and TopMetal1 power trunks. ','Compact placements and shorter local signal tracks; same native primitive geometry and power strap topology. ')
assert q!=p and not q.exists();q.write_text(s)
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
a=p.read_text();b=q.read_text();ops=[dict(tag=t,before=a[i:j],after=b[k:l]) for t,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()];(B/'generator-source-bridge.json').write_text(json.dumps(dict(before=pin(p),after=pin(q),opcodes=ops),indent=2)+'\n');print(pin(q))
