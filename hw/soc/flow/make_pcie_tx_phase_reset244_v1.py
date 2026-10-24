#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""New physical candidate for the passed244 intrinsic source; no old55 layout reuse."""
import copy,hashlib,inspect,json,os,sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve()
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent))
import make_pcie_clock_div4_v10_tail_v1 as m
BASE=HERE.parent/"make_pcie_clock_div4_v10_tail_v1.py"
BASE_SHA="d81291d4607608853700223e73fb49f10005584cb31542464659e261d148aec2"
CIRCUIT="hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice"
CIRCUIT_SHA="3b4aa82387b5e532437dc592feceea699b4d283570751d6e983f0949fe7095f4"
OLD="hw/soc/analog/pcie/clock_div2_fast_assert_firstfall_v3.spice"
OLD_SHA="78f3413256b2b2769cebbcda3319762f5ff8a769f8bafd4246bec040de519130"
PORTS=("CLKP","CLKN","MP","MN","QP","QN","ARM_P","ARM_N","DIV_AVDD","AVSS","SUB")
TARGET="PHASE__XRUN__XAND_SKEW"
WIDTH=1440.0
DEVICE_START_X=320.0
GROUP_COUNT=15
TAPS=6*GROUP_COUNT
MAX_CROSSING=48
PRESET=None
GROUP_CENSUS=(17,17,17,17,17,11,17,17,24,11,17,17,11,17,17)
SCOPE=("Fresh244 compact devices plus90 finite native substrate contacts. "
 "Both P and N preset variants derive from the exact four-case passing intrinsic schematic. "
 "All other243 device identities, terminals and dimensions are unchanged from rejected v3. "
 "Only XRUN.XAND_SKEW W1um/L32um becomes W1um/L20um. "
 "This is a new physical layout with new reset/select/first-fall routes, not old55 extracted RC. "
 "Every PCell and terminal,560-rule DRC,deep/flat LVS,wire graph,MIM ownership,two-order RC,"
 "loaded reset/phase/device safety and physical startup must pass before qualification. "
 "No real31-tree,actual PLL or fullPHY acceptance.")
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def exact_replace(source,edits):
    original=source
    for old,new in edits:
        assert old!=new and source.count(old)==1,("Ambiguous parent derivation",old)
        source=source.replace(old,new,1)
    recovered=source
    for old,new in reversed(edits):
        assert recovered.count(new)==1,("Nonreversible derivation",new)
        recovered=recovered.replace(new,old,1)
    assert recovered==original
    return source
FLATTEN_EDITS=[
 ('"NSSOC_CLOCK_DIV4_HBT_V10",','"NSSOC_PHASE_ASYNC_PRESET_PARENT_"+PRESET.upper()+"_V2",'),
 ('        "DIV",\n        ["CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB"],','        "PHASE",\n        list(PORTS),'),
 ('dict(hbt=34, resistor=33, capacitor=6)','dict(hbt=106, resistor=130, capacitor=8)')]
MAIN_EDITS=[
 ('    args = parser.parse_args()','    parser.add_argument("--preset",choices=("p","n"),required=True)\n    args = parser.parse_args()\n    configure(args.preset)'),
 ('    width = 960.0','    width = WIDTH'),
 ('    if len(crossing) > 24:','    if len(crossing) > MAX_CROSSING:'),
 ('        if [b["row"] for b in selected] != [0, 1, 2]:','        if [b["row"] for b in selected] != list(range(GROUP_COUNT)):'),
 ('    if len(power_straps) != 8:','    if len(power_straps) != 2*(GROUP_COUNT+1):'),
 ('        primitive_counts=dict(hbt=34, rppd=33, cmim=6, physical_ptap=TAPS),','        primitive_counts=dict(hbt=106, rppd=130, cmim=8, physical_ptap=TAPS),'),
 ('        placement_method="Three unchanged topology groups, width-aware compact placement and loss-prioritized local tracks",','        placement_method="Fifteen explicit244 reset/selector/release groups; native PCell escape and full device routes, fresh physical qualification required",'),
 ('        scope="Exact standalone divider v10 tail v1: only second-stage XBIAS W1um reference length12.7um to11.5um; both24um MIMs, L8 clock pull-downs and all72 other circuit primitives plus18 finite substrate contacts unchanged. "\n        "Compact placements and shorter local signal tracks; same native primitive geometry and power strap topology. "\n        "No oscillator, CMOS feedback chain, extracted division, qualified RC, PLL or complete PHY acceptance.",','        scope=SCOPE,')]
def derivations():
    assert sha_bytes(BASE.read_bytes())==BASE_SHA
    f=inspect.getsource(m.flatten)
    assert f.startswith("def flatten(texts):")
    # Capture the original pure function before any configuration replaces main.
    return exact_replace(f,FLATTEN_EDITS),exact_replace(ORIGINAL_MAIN,MAIN_EDITS)
ORIGINAL_MAIN=inspect.getsource(m.main)
def flatten_source(text,preset):
    assert preset in ("p","n")
    f,_=derivations()
    ns=dict(m.__dict__);ns.update(PORTS=PORTS,PRESET=preset)
    exec(compile(f,str(HERE)+"#exact-flat","exec"),ns)
    rows=ns["flatten"]({CIRCUIT:text})
    assert len(rows)==244 and Counter(r["kind"]for r in rows)==dict(hbt=106,resistor=130,capacitor=8)
    assert len({r["name"]for r in rows})==244
    return rows
def source_rows(root,preset):
    root=Path(root);new=(root/CIRCUIT).read_bytes();old=(root/OLD).read_bytes()
    assert sha_bytes(new)==CIRCUIT_SHA and sha_bytes(old)==OLD_SHA
    before=flatten_source(old.decode(),preset);after=flatten_source(new.decode(),preset)
    validate_delta(before,after)
    return after
def validate_delta(before,after):
    assert len(before)==len(after)==244
    assert Counter(r["kind"]for r in before)==Counter(r["kind"]for r in after)==dict(hbt=106,resistor=130,capacitor=8)
    assert len({r["name"]for r in before})==len({r["name"]for r in after})==244
    differences=[(a,b)for a,b in zip(before,after,strict=True)if a!=b]
    assert len(differences)==1
    a,b=differences[0]
    assert a["name"]==b["name"]==TARGET and a["kind"]==b["kind"]=="resistor"
    assert a["nets"]==b["nets"]==["PHASE__XRUN__BIP","AVSS","SUB"]
    assert a["width_um"]==b["width_um"]==1 and a["length_um"]==32 and b["length_um"]==20
    assert {k:v for k,v in a.items()if k!="length_um"}=={k:v for k,v in b.items()if k!="length_um"}
    restored=copy.deepcopy(after)
    next(r for r in restored if r["name"]==TARGET)["length_um"]=32.0
    assert restored==before,"Changed one of the other243 compact devices"
    return {"unchanged_compact_devices":243,"target":TARGET,"old_L_um":32,"new_L_um":20}
def group_id(name):
    assert name.startswith("PHASE__"),"Wrong canonical source root"
    tail=name[len("PHASE__"):]
    if tail.startswith("XCLK__"):return 0
    if tail.startswith("XRELEASE__XARM__"):return 1
    if tail in ("XRELEASE__XBIAS","XRELEASE__XREF")or tail.startswith("XRELEASE__XSEED__"):return 2
    for prefix,base in (("XRELEASE__XM__",2),("XRELEASE__XS__",5),("XM__",9),("XS__",12)):
        if tail.startswith(prefix):
            rest=tail[len(prefix):]
            return base+1 if rest.startswith("XDATA__")else base+2 if rest.startswith("XHOLD__")else base
    if tail.startswith("XRUN__")or tail in ("XBIAS","XREF","XSEEDP","XSEEDN"):return 8
    raise AssertionError("Unassigned source device "+name)
def placement_plan(rows):
    assert len(rows)==244 and len({r["name"]for r in rows})==244
    byname={r["name"]:r for r in rows};groups=[[]for _ in range(GROUP_COUNT)]
    for r in rows:groups[group_id(r["name"])].append(r["name"])
    assert tuple(map(len,groups))==GROUP_CENSUS
    assert set(sum(groups,[]))==set(byname)
    starts={};net_rows={};plan={};base=0.0
    for rid,group in enumerate(groups):
        nets={"SUB"}
        for name in group:
            r=byname[name];count={"hbt":3,"resistor":2,"capacitor":2}[r["kind"]]
            nets.update(r["nets"][:count])
        ordered=[n for n in PORTS if n in nets]+sorted(nets-set(PORTS))
        assert set(ordered)==nets and len(ordered)==len(nets)
        assert {"DIV_AVDD","AVSS","SUB"}<=nets,"Every real group needs both native power buses and body contacts"
        starts[rid]=base;net_rows[rid]=ordered;x=DEVICE_START_X
        for name in group:
            r=byname[name]
            y=56.0 if r["kind"]=="hbt"else 60.0-r["length_um"]-(.61 if r["kind"]=="resistor"else .60)
            assert 0<=y<70
            plan[name]=(rid,x,round((base+y)/.005)*.005)
            x+=36.0 if r["kind"]=="capacitor"and r["width_um"]==24 else 24.0
        assert x<WIDTH-224.0,"Source device bands enter peripheral trunk region"
        base+=m.bus_offset(ordered,ordered[-1])+24.0
    allnets=set().union(*(set(ns)for ns in net_rows.values()))
    assert set(PORTS)<=allnets
    crossing=[n for n in allnets if sum(n in ns for ns in net_rows.values())>1]
    assert len(crossing)<=MAX_CROSSING,"Need a new physical routing plan; never waive capacity"
    # Original routing's global crossing index remains safe on either side.
    assert 12+(MAX_CROSSING-1)*4+1.0<DEVICE_START_X-12
    return plan,starts,net_rows
def substrate_tap_position(index,starts):
    assert 0<=index<TAPS and set(starts)==set(range(GROUP_COUNT))
    # Native centers331+120i remain outside peripheral M4 trunks and away
    # from320+24i device escape lanes; real native DRC/ownership still required.
    return 330.0+(index%6)*120.0,starts[index//6]+4.0
def devices(root):
    assert PRESET in ("p","n")
    return source_rows(root,PRESET)
def use_direction(name):
    if name=="DIV_AVDD":return "POWER","INOUT"
    if name in("AVSS","SUB"):return "GROUND","INOUT"
    assert name in PORTS
    return "SIGNAL","OUTPUT"if name in("MP","MN","QP","QN")else"INPUT"
def configure(preset):
    global PRESET
    assert preset in ("p","n");PRESET=preset
    m.TOP="nssoc_tx_phase_reset244_"+preset+"_v1"
    m.PORTS=PORTS;m.TAPS=TAPS;m.SOURCES={CIRCUIT:CIRCUIT_SHA,OLD:OLD_SHA}
    m.WIDTH=WIDTH;m.GROUP_COUNT=GROUP_COUNT;m.MAX_CROSSING=MAX_CROSSING;m.SCOPE=SCOPE
    m.devices=devices;m.placement_plan=placement_plan;m.substrate_tap_position=substrate_tap_position;m.use_direction=use_direction
    m.configure=configure
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    # Exactly the inherited native PCell/pin/via/route implementation; only
    # declared source/census/placement bounds and external port policy change.
    configure("p")
    _,body=derivations();exec(compile(body,str(HERE)+"#exact-native-main","exec"),m.__dict__)
    m.main()
    out=Path(sys.argv[sys.argv.index("--out")+1]);p=out/"result.json";r=json.loads(p.read_text())
    rows=source_rows(ROOT,PRESET);plan,starts,nets=placement_plan(rows)
    assert r["primitive_counts"]==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
    assert len(r["instances"])==334 and set(r["ports"])==set(PORTS)
    actual=[v for v in r["instances"]if v["kind"]!="substrate_tap"]
    assert [{k:v[k]for k in row}for row,v in zip(rows,actual,strict=True)]==rows
    assert all(tuple(v["placement_um"])==tuple(plan[v["name"]][1:])for v in actual)
    r["input_sha256"].update({str(HERE):m.sha(HERE),str(BASE):BASE_SHA})
    r.update(preset_polarity=PRESET,compact_devices=244,finite_body_contacts=90,actual_expected_LVS_devices=334,
      candidate_source_sha256=CIRCUIT_SHA,previous_rejected_source_sha256=OLD_SHA,
      exactly243_other_compact_devices_unchanged=True,sole_device_dimension_delta={"name":TARGET,"old_L_um":32,"new_L_um":20,"W_um":1},
      explicit_source_device_map=rows,explicit_row_net_map=nets,
      native_geometry_reused="Only unchanged generic PCell creation and measured pin/via escape implementation; every source device is generated anew. No old55 GDS, LVS IDs or RC nodes reused.",
      native_DRC_passed=False,native_LVS_passed=False,native_wire_ownership_passed=False,fresh_MIM_RC_passed=False,
      real_selector_load_accepted=False,physical_reset_qualified=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
    p.write_text(json.dumps(r,indent=2)+"\n")
if __name__=="__main__":main()
