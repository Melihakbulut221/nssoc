#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic controls. No OpenROAD, ODB, LEF, Liberty or native archive is acquired."""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
import mainchip_routed_view_admission as a
import mainchip_routed_view_export_native as native
import mainchip_routed_view_coverage as cov
SUMMARY={}

def envelope():
    return dict(run=a.RUN,attempt=1,source=a.PRODUCER,member=a.FINAL,
      candidate=dict(bytes=101,sha256="a"*64),archive=dict(bytes=202,sha256="b"*64),
      outputs_sha256="c"*64,parts_sha256="d"*64,receipt_sha256="e"*64)

def request():
    d=lambda path:dict(path="/work/routed-view-inputs/"+path,pin=dict(bytes=10,sha256="1"*64))
    return dict(envelope=envelope(),source=dict(path=str(native.SOURCE),pin=envelope()["candidate"]),
      lefs=[d("technology.lef"),d("cells.lef")],liberties={c:[d(c+".lib")]for c in a.CORNERS})

def tiny():
    pin=lambda net,sig="SIGNAL",io="INPUT":dict(net=net,sigtype=sig,io=io)
    return dict(block="soc_top",dbu=1000,
      nets={"n":dict(sigtype="SIGNAL",wire=True),"VDD":dict(sigtype="POWER",wire=False),"VSS":dict(sigtype="GROUND",wire=False),"unused":dict(sigtype="SIGNAL",wire=False),"single":dict(sigtype="SIGNAL",wire=False)},
      instances={"U":dict(master=["cells","buf"],master_type="CORE",pins={"A":pin("n"),"Y":pin("single",io="OUTPUT"),"VDD":pin("VDD","POWER","INOUT")}),
        "D":dict(master=["cells","sg13g2_antennanp"],master_type="CORE_ANTENNACELL",pins={"A":pin("n"),"VSS":pin("VSS","GROUND","INOUT")}),
        "F":dict(master=["cells","fill"],master_type="CORE_SPACER",pins={})},
      ports={"i":pin("n",io="INPUT")})

def model(v):
    pins=[]
    for inst,row in v["instances"].items():
        for pin,r in row["pins"].items():
            if r["sigtype"]not in a.PG:
                pins.append(dict(instance=inst,pin=pin,net=r["net"],path=inst+"/"+pin,driver=r["io"]in("OUTPUT","INOUT"),liberty_cell=row["master"][1],liberty_pin=pin,min=1e-15,max=2e-15))
    ports=[dict(port=p,net=r["net"],path=p,driver=r["io"]in("INPUT","INOUT"))for p,r in v["ports"].items()if r["sigtype"]not in a.PG]
    pins.sort(key=lambda r:(r["instance"],r["pin"]));ports.sort(key=lambda r:r["port"])
    return dict(pins=pins,ports=ports)

def records(v,models):
    """Independent synthetic producer framing; never native DB bytes."""
    h=lambda x:str(x).encode().hex()
    rows=[["BEGIN",h(v["block"]),str(v["dbu"])]]
    for n,r in sorted(v["nets"].items()):rows.append(["N",h(n),r["sigtype"],str(int(r["wire"]))])
    for n,r in sorted(v["instances"].items()):
        rows.append(["I",h(n),h(r["master"][0]),h(r["master"][1]),r["master_type"]])
        for p,t in sorted(r["pins"].items()):rows.append(["T",h(n),h(p),h(t["net"]or""),t["sigtype"],t["io"]])
    for p,t in sorted(v["ports"].items()):rows.append(["P",h(p),h(t["net"]or""),t["sigtype"],t["io"]])
    for r in models["pins"]:rows.append(["C",h(r["instance"]),h(r["pin"]),h(r["net"]or""),h(r["path"]),str(int(r["driver"])),h(r["liberty_cell"]),h(r["liberty_pin"]),str(r["min"]),str(r["max"])])
    for r in models["ports"]:rows.append(["B",h(r["port"]),h(r["net"]or""),h(r["path"]),str(int(r["driver"]))])
    rows.append(["END",str(len(v["instances"])),str(len(v["nets"])),str(len(v["ports"]))])
    return ("\n".join("\t".join(r)for r in rows)+"\n").encode()

def timing_view(v):
    out=copy.deepcopy(v)
    for row in out["instances"].values():row["pins"]={p:r for p,r in row["pins"].items()if r["sigtype"]not in a.PG}
    out["ports"]={p:r for p,r in out["ports"].items()if r["sigtype"]not in a.PG}
    out["nets"]={n:r for n,r in out["nets"].items()if r["sigtype"]not in a.PG}
    for r in out["nets"].values():r["wire"]=False;r["sigtype"]="SIGNAL"
    return out

def small_spef():
    return b'''*SPEF "IEEE 1481-1998"
*DESIGN "soc_top"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*DESIGN_FLOW "PIN_CAP NONE"
*C_UNIT 1 PF
*R_UNIT 1 OHM
*NAME_MAP
*1 n
*2 U
*3 D
*4 i
*D_NET *1 0.1
*CONN
*P *4 I
*I *2:A I
*I *3:A I
*CAP
1 *2:A 0.1
*RES
1 *2:A *3:A 1
*END
'''

def full_snapshots():
    # Full census is actually enumerated; fillers and unused nets are explicit.
    def inst(master,typ,pins):return dict(master=["cells",master],master_type=typ,pins=pins,status="PLACED",location=[0,0],origin=[0,0],orientation="R0")
    def p(net,sig="SIGNAL",io="INPUT"):return dict(net=net,sigtype=sig,io=io)
    original={f"B{i:06}":inst("fill","CORE_SPACER",{})for i in range(153128)}
    for i in range(608):original[f"B{i:06}"]=inst("buf","CORE",{"Y":p("m"+str(i),io="OUTPUT")})
    template=inst("sg13g2_antennanp","CORE_ANTENNACELL",{"A":p("m607"),"VDD":p("VDD","POWER","INOUT"),"VSS":p("VSS","GROUND","INOUT")})
    original["ANTENNA_1573"]=template
    names=[f"m{i}"for i in range(608)]+[f"clk{i}"for i in range(1691)]+["VDD","VSS"]
    names +=[f"unconnected{i}"for i in range(143820-len(names))]
    nets={}
    for n in names:
        sig="POWER"if n=="VDD"else"GROUND"if n=="VSS"else"CLOCK"if n.startswith("clk")else"SIGNAL"
        wired=n.startswith("m")or n=="clk0"
        nets[n]=dict(identity=dict(name=n,sigtype=sig,terminals=[],bterms=[],rule=None),
          encoded=dict(wire_present=wired,metadata="ROUTED"if wired else None,paths=["ROUTED"]if wired else[]),
          wire=dict(pin={"bytes":1,"sha256":"1"*64},opcode_count=int(wired)))
    for i,row in original.items():
        for pin,r in row["pins"].items():nets[r["net"]]["identity"]["terminals"].append([i,pin])
    for row in nets.values():row["identity"]["terminals"].sort()
    nets["clk0"]["identity"]["bterms"]=[["clk_i","INPUT","CLOCK",[]]]
    protected=[f"clk{i}"for i in range(1691)]
    base=dict(instances=original,nets=nets,masters={"cells/fill":{},"cells/buf":{},"cells/sg13g2_antennanp":{}},
      block=dict(name="soc_top",dbu=1000,tech_dbu=1000,rows=[]),immutable={},protected=protected,
      diode_template=template,clock_record_pins={n:{"bytes":1,"sha256":"2"*64}for n in protected})
    inserted=dict(base,instances=dict(original),nets=dict(nets))
    changed=set([f"m{i}"for i in range(608)]+["VDD","VSS"])
    for n in changed:
        r=nets[n];inserted["nets"][n]=dict(r,identity=dict(r["identity"],terminals=list(r["identity"]["terminals"])))
    added={}
    for i in range(1351):
        n=f"D{i:04}";net="m"+str(i%608);added[n]=net
        row=copy.deepcopy(template);row["pins"]["A"]["net"]=net;row["location"]=[i,0]
        inserted["instances"][n]=row
        for pin,r in row["pins"].items():inserted["nets"][r["net"]]["identity"]["terminals"].append([n,pin])
    for n in changed:inserted["nets"][n]["identity"]["terminals"].sort()
    plan=dict(added_instances=sorted(added),attachments=added,mutable_nets=sorted(set(added.values())),
      baseline_violating_nets=sorted(set(added.values())),repaired_margin_only_nets=[],ratio_margin=10,
      original_instances_preserved=153129,protected_nets=protected,**a.inherited.p.FLAGS)
    final=dict(inserted,nets=dict(inserted["nets"]))
    for n in plan["mutable_nets"]:
        final["nets"][n]=dict(inserted["nets"][n],wire=dict(pin={"bytes":2,"sha256":"3"*64},opcode_count=2))
    violations=[dict(net=n)for n in plan["mutable_nets"]]
    return base,inserted,final,plan,violations

class SourceControls(unittest.TestCase):
    def test_exact_protected_source_and_real_cloud_context(self):
        m=a.source_gate();self.assertIsNone(m["terminal_binding"])
        self.assertEqual(os.environ["GITHUB_REF"],"refs/heads/"+a.BRANCH)
        self.assertEqual(os.environ["GITHUB_REPOSITORY"],"Melihakbulut221/nssoc")
        self.assertEqual(os.environ["GITHUB_EVENT_NAME"],"workflow_dispatch")
        self.assertEqual(os.environ["GITHUB_RUN_ATTEMPT"],"1")
        self.assertEqual(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),os.environ["GITHUB_SHA"])
    def test_native_entrypoints_refuse_before_side_effects(self):
        with mock.patch.object(Path,"mkdir",side_effect=AssertionError("mkdir forbidden")),mock.patch.object(subprocess,"run",side_effect=AssertionError("process forbidden")):
            with self.assertRaises(PermissionError):native.execute(request(),tiny(),{},None)
            with self.assertRaises(PermissionError):native.main()
        with mock.patch.object(a,"source_gate",return_value={"native_export_authorized":True}):
            with self.assertRaises(PermissionError):a.authorize_native()
    def test_original_qualified373_sources_still_protected(self):
        m=a.source_gate();old=a.inherited.source_gate()
        self.assertTrue(set(old["files"])<=set(m["files"]))
        for path,digest in old["files"].items():self.assertEqual(m["files"][path],digest)
    def test_envelope_rejects_wrong_producer_member_or_pin(self):
        good=envelope();self.assertEqual(a.validate_envelope(good),good)
        changes={"run":1,"attempt":True,"source":"0"*40,"member":"work/route-partial.odb","candidate":{"bytes":0,"sha256":"a"*64},"archive":{"bytes":2,"sha256":"x"},"receipt_sha256":"x"}
        for k,v in changes.items():
            bad=copy.deepcopy(good);bad[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):a.validate_envelope(bad)
    def test_json_duplicate_nonfinite_and_path_injection_refused(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):a.decode(raw)
        for path in("/tmp/a","/work/../x","/work/thing;exec","/work/a\nb","/work/a[bad]"):
            with self.assertRaises(ValueError):native.q(path)
    def test_request_all_corner_and_input_identity_refusals(self):
        r=request();self.assertTrue(native.validate_request(r))
        for mutate in (lambda q:q["liberties"].pop(a.CORNERS[0]),lambda q:q["source"].update(path="/work/routed-view-inputs/other.odb"),
                       lambda q:q["source"]["pin"].update(sha256="0"*64),lambda q:q["lefs"].append(q["lefs"][0])):
            bad=copy.deepcopy(r);mutate(bad)
            with self.assertRaises(ValueError):native.validate_request(bad)
    def test_render_exact_export_flags_and_no_design_mutators(self):
        s=native.render(request(),"candidate",a.CORNERS[0])
        self.assertEqual(s.count("write_verilog "),2)
        self.assertIn("write_verilog -include_pwr_gnd {/work/routed-views/full.v}",s)
        self.assertIn("write_verilog {/work/routed-views/timing.v}",s)
        for command in("repair_","detailed_route","global_route","estimate_parasitics","set_clock","remove_cells","write_db"):
            self.assertNotIn(command,s)
        self.assertIn("$sp liberty_port",s);self.assertIn("$lp capacitance $corner min",s)
        for mode in("full","timing"):
            reload=native.render(request(),mode,a.CORNERS[1]);self.assertIn("link_design soc_top",reload);self.assertNotIn("read_db ",reload)
    def test_native_source_has_no_enabled_cli_or_download(self):
        tree=ast.parse(Path(native.__file__).read_text());self.assertTrue(tree)
        for node in ast.walk(tree):
            if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute):
                self.assertNotIn(node.func.attr,("urlopen","request","Popen","run","check_call","check_output"))
        self.assertNotIn("read_sdc",native.CAPTURE)

class InventoryControls(unittest.TestCase):
    def test_independent_wire_records_roundtrip_and_pg_accounting(self):
        v=tiny();r=records(v,model(v));actual,loads=native.parse_records(r)
        self.assertEqual(actual,v);self.assertEqual(loads,model(v))
        projection,account=a.projection(v,False)
        self.assertEqual(account["physical_only_instances"],["F"])
        self.assertEqual(account["excluded_pg_terminals"],[["D","VSS"],["U","VDD"]])
        self.assertEqual(set(projection["nets"]),{"n","single"})
        self.assertEqual(set(account["unreferenced_physical_nets"]),{"VDD","VSS","unused"})
    def test_records_truncated_duplicate_unknown_or_census_refused(self):
        raw=records(tiny(),model(tiny()))
        for bad in(raw.rsplit(b"END",1)[0],raw+raw,raw.replace(b"END\t3\t5\t1",b"END\t4\t5\t1"),raw.replace(b"N\t6e\t",b"ALIEN\t6e\t",1),raw.replace(b"BEGIN\t736f635f746f70",b"BEGIN\tzz")):
            with self.subTest(length=len(bad)),self.assertRaises(ValueError):native.parse_records(bad)
    def test_unknown_net_duplicate_pg_and_port_alias_refused(self):
        for modify in(lambda v:v["instances"]["D"]["pins"]["A"].update(net="missing"),
                      lambda v:v["instances"]["D"]["pins"]["VSS"].update(net="VDD"),
                      lambda v:v["ports"]["i"].update(net="missing")):
            v=tiny();modify(v)
            with self.assertRaises(ValueError):a.validate_inventory(v)
    def test_actual_liberty_cell_pin_capacitance_and_corner_refusals(self):
        v=tiny();loads={c:model(v)for c in a.CORNERS}
        a.validate_loads(v,loads,{"D":"n"})
        mutations=[lambda x:x.pop(a.CORNERS[0]),lambda x:x[a.CORNERS[0]]["pins"].pop(),
          lambda x:x[a.CORNERS[0]]["pins"][0].update(liberty_cell="missing"),lambda x:x[a.CORNERS[0]]["pins"][0].update(net="wrong"),
          lambda x:x[a.CORNERS[0]]["pins"][0].update(min=float("nan")),lambda x:x[a.CORNERS[0]]["pins"][0].update(min=-1),
          lambda x:x[a.CORNERS[0]]["pins"][0].update(min=0),lambda x:x[a.CORNERS[0]]["ports"].clear()]
        for fn in mutations:
            bad=copy.deepcopy(loads);fn(bad)
            with self.assertRaises(ValueError):a.validate_loads(v,bad,{"D":"n"})

class CoverageControls(unittest.TestCase):
    def test_exact_spef_coverage_with_explicit_non_netcount_exclusions(self):
        result=cov.coverage(tiny(),small_spef())
        self.assertEqual(result["required_nets"],1);self.assertEqual(result["inventory_nets"],5)
        self.assertEqual(result["excluded"],{"VDD":"power-or-ground","VSS":"power-or-ground","unused":"no-signal-terminals","single":"unwired-single-terminal"})
    def test_required_net_or_diode_terminal_omission_refused(self):
        for bad in(small_spef().replace(b"*I *3:A I\n",b""),small_spef().replace(b"*1 n\n",b"*1 unused\n"),small_spef().replace(b"*I *3:A I",b"*I *3:B I")):
            with self.assertRaises(ValueError):cov.coverage(tiny(),bad)
    def test_unknown_duplicate_mismatched_spef_records_refused(self):
        variants=[small_spef().replace(b"*4 i",b"*4 wrong"),small_spef().replace(b"*3 D",b"*3 D\n*3 D"),
          small_spef().replace(b"*I *3:A I",b"*I *3:A I\n*I *3:A I"),small_spef().replace(b"*I *3:A I",b"*I *3:A O"),
          small_spef().replace(b"*END\n",b""),small_spef().replace(b"0.1",b"NaN"),small_spef().replace(b"*DESIGN \"soc_top\"",b"*DESIGN \"other\""),
          small_spef().replace(b"*DESIGN_FLOW \"PIN_CAP NONE\"",b"*DESIGN_FLOW \"PIN_CAP INCLUDED\"")]
        for bad in variants:
            with self.assertRaises(ValueError):cov.coverage(tiny(),bad)
    def test_native_annotation_driver_counts_and_explicit_singleton(self):
        v=tiny();loads={c:model(v)for c in a.CORNERS}
        report=b"Found 1 unannotated drivers.\n U/Y\nFound 0 partially unannotated drivers.\n"
        r=cov.annotation(v,loads,a.CORNERS[0],report)
        self.assertEqual(r["excluded_driver_nets"],{"U/Y":"single"});self.assertEqual(r["native_driver_count"],2)
    def test_annotation_missing_required_unknown_partial_or_truncated_refused(self):
        v=tiny();loads={c:model(v)for c in a.CORNERS}
        for raw in(b"Found 1 unannotated drivers.\n i\nFound 0 partially unannotated drivers.\n",
                   b"Found 1 unannotated drivers.\n wrong\nFound 0 partially unannotated drivers.\n",
                   b"Found 0 unannotated drivers.\nFound 1 partially unannotated drivers.\n i\n  U/A\n",
                   b"Found 0 unannotated drivers.\n",b"Found 1 unannotated drivers.\nFound 0 partially unannotated drivers.\n"):
            with self.assertRaises(ValueError):cov.annotation(v,loads,a.CORNERS[0],raw)
    def test_full_coverage_contract_requires_three_actual_model_and_report_corners(self):
        v=tiny();loads={c:model(v)for c in a.CORNERS};reports={c:b"Found 0 unannotated drivers.\nFound 0 partially unannotated drivers.\n"for c in a.CORNERS}
        r=cov.verify_all(v,loads,{"D":"n"},small_spef(),reports);self.assertEqual(len(r["annotation"]),3)
        reports.pop(a.CORNERS[0])
        with self.assertRaises(ValueError):cov.verify_all(v,loads,{"D":"n"},small_spef(),reports)

class CompleteCandidateControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before,cls.inserted,cls.final,cls.plan,cls.violations=full_snapshots()
        cls.inventory=a.inventory_from_snapshot(cls.final)
    def test_full_actual_enumeration_lineage_and_1351_delta(self):
        r=a.lineage(self.before,self.inserted,self.final,self.plan,self.violations)
        self.assertEqual((r["baseline_instances"],r["added_diodes"],r["final_instances"],r["nets"]),(153129,1351,154480,143820))
        self.assertEqual(len(r["delta"]["changed_nets"]),608)
        SUMMARY.update(full_lineage=True,baseline_instances=153129,added_diodes=1351,final_instances=154480,nets=143820,mutable_nets=608,protected_nets=1691)
    def test_full_original_instance_or_unowned_net_changes_refused(self):
        bad=dict(self.final,instances=dict(self.final["instances"]));bad["instances"]["B000000"]=dict(bad["instances"]["B000000"],master=["cells","wrong"])
        with self.assertRaises(AssertionError):a.lineage(self.before,self.inserted,bad,self.plan,self.violations)
        bad=dict(self.final,nets=dict(self.final["nets"]));bad["nets"]["clk0"]=dict(bad["nets"]["clk0"],wire={"pin":"changed"})
        with self.assertRaises(AssertionError):a.lineage(self.before,self.inserted,bad,self.plan,self.violations)
    def test_full_count_or_diode_incidence_changes_refused(self):
        bad=dict(self.final,instances=dict(self.final["instances"]));bad["instances"].pop("D0000")
        with self.assertRaises(ValueError):a.lineage(self.before,self.inserted,bad,self.plan,self.violations)
        plan=copy.deepcopy(self.plan);plan["attachments"]["D0000"]="m1"
        with self.assertRaises(AssertionError):a.lineage(self.before,self.inserted,self.final,plan,self.violations)
    def test_complete_nine_capture_export_reload_admission_without_native_bytes(self):
        v=self.inventory;full=copy.deepcopy(v)
        for row in full["nets"].values():row["wire"]=False
        timing=timing_view(v);data={}
        for mode,view in(("candidate",v),("full",full),("timing",timing)):
            raw=records(view,model(view))
            for corner in a.CORNERS:data[(mode,corner)]=raw
        before=a.pin_bytes(a.encode(v));r=native.collect(v,self.plan["attachments"],data)
        self.assertEqual(a.pin_bytes(a.encode(v)),before)
        self.assertEqual(r["topology"]["actual_physical_instances"],154480)
        self.assertTrue(r["topology"]["all1351_added_diode_A_pins_preserved"])
        self.assertEqual(len(r["record_pins"]),9)
        SUMMARY.update(complete_nine_capture_collect=True,complete_inventory_nonmutation=True,native_bytes_generated=False)
    def test_complete_saved_capsule_admission_uses_original373_audit_and_full_lineage(self):
        import check_mainchip_stale_wire_admission as original_fixture
        with tempfile.TemporaryDirectory(prefix="synthetic-routed-view-")as temporary:
            root=Path(temporary);original_fixture.synthetic_capsule(root)
            data=root/"bulk-postdrt-antenna"
            def write(name,value):(data/name).write_bytes(a.encode(value))
            fixed=dict(self.inserted,def_pin=dict(bytes=12,sha256="4"*64))
            cleared=dict(fixed,nets=dict(fixed["nets"]),def_pin=dict(bytes=13,sha256="5"*64))
            for net in self.plan["mutable_nets"]:
                row=copy.deepcopy(fixed["nets"][net])
                row["encoded"].update(wire_present=False,paths=[])
                row["wire"]=dict(opcode_count=0,pin=a.inherited.p.pin(a.inherited.p.encode(None)))
                cleared["nets"][net]=row
            for name,value in(("baseline-snapshot.json",self.before),("insertion-snapshot.json",self.inserted),
                ("restored-snapshot.json",self.final),("baseline-antenna-violations.json",self.violations),
                ("insertion-plan.json",self.plan),("fixed-snapshot.json",fixed),("stale-wire-cleared-snapshot.json",cleared),
                ("stale-wire-original-guides.json",{n:[]for n in fixed["nets"]})):write(name,value)
            mutation=a.decode((data/"stale-wire-mutation.json").read_bytes())
            mutation["removed"]=sorted(self.plan["mutable_nets"])
            mutation["delta"]["cleared_nets"]=sorted(self.plan["mutable_nets"])
            write("stale-wire-mutation.json",mutation)
            binding=envelope();binding["candidate"]=a.pin(root/a.FINAL)
            before={str(p.relative_to(root)):a.pin(p)for p in root.rglob("*")if p.is_file()}
            result=a.audit_saved_candidate(root,binding)
            self.assertEqual(result["inventory"],self.inventory)
            self.assertEqual(result["previous"]["command_count"],17)
            self.assertEqual(result["lineage"]["final_instances"],154480)
            self.assertEqual({str(p.relative_to(root)):a.pin(p)for p in root.rglob("*")if p.is_file()},before)
            bad=copy.deepcopy(binding);bad["candidate"]["sha256"]="0"*64
            with self.assertRaises(ValueError):a.audit_saved_candidate(root,bad)
            SUMMARY.update(complete_saved_capsule_audit=True,original17command_audit_used=True)
    def test_missing_export_instance_and_pin_or_master_refused(self):
        v=self.inventory;timing=timing_view(v)
        for k in("instance","pin","master"):
            bad=dict(v,instances=dict(v["instances"]))
            if k=="instance":bad["instances"].pop("D0000")
            else:
                row=copy.deepcopy(v["instances"]["D0000"])
                if k=="pin":row["pins"]["A"]["net"]="m607"
                else:row["master"][1]="buf"
                bad["instances"]["D0000"]=row
            with self.subTest(k=k),self.assertRaises(ValueError):a.compare_views(v,bad,timing,self.plan["attachments"])

class TclAdapterControls(unittest.TestCase):
    def test_actual_rendered_tcl_with_instrumented_native_boundary(self):
        # Real Tcl parser/execution, explicit fake object graph; no native modules.
        fixture=r"""
set captured ""
set calls {}
proc record_call {name args} {global calls; lappend calls [linsert $args 0 $name]}
foreach cmd {read_liberty read_db read_lef read_verilog link_design write_def write_verilog set_thread_count} {
  proc $cmd {args} [format {record_call %s {*}$args} $cmd]
}
rename open original_open
proc open {args} {return fixture-channel}
rename close original_close
proc close {channel} {if {$channel ne "fixture-channel"} {error "unexpected channel"}}
rename puts original_puts
proc puts {args} {
  global captured
  if {[llength $args] == 2 && [lindex $args 0] eq "fixture-channel"} {append captured [lindex $args 1] "\n"} else {original_puts {*}$args}
}
rename exit original_exit
proc exit {args} {global captured calls;original_puts -nonewline $captured;original_puts "RV_FAKE_CALLS [binary encode hex [join $calls \n]]"}
namespace eval ord {proc get_db_block {} {return block}}
namespace eval sta {
  proc network_leaf_instances {} {return si}
  proc sta_to_db_inst {i} {if {$i ne "si"} {error "unexpected STA instance"};return d}
  proc cmd_corner {} {return corner}
  proc get_full_name {p} {if {$p eq "sp"} {return D/A};if {$p eq "bp"} {return i};error "unknown native path"}
  proc find_pin {p} {if {$p eq "i"} {return bp};return NULL}
}
proc block {m args} {
  switch -- $m {
    getName {return soc_top} getChildren {return {}} getDbUnitsPerMicron {return 1000}
    getNets {return {n g}} getInsts {return d} getBTerms {return port}
    default {error "unknown block method $m"}
  }
}
proc n {m args} {switch -- $m {getName {return n} getSigType {return SIGNAL} getWire {return wire} default {error "net method"}}}
proc g {m args} {switch -- $m {getName {return VSS} getSigType {return GROUND} getWire {return NULL} default {error "net method"}}}
proc d {m args} {switch -- $m {getName {return D} getMaster {return master} getITerms {return {ia ig}} default {error "inst method"}}}
proc master {m args} {switch -- $m {getName {return sg13g2_antennanp} getLib {return lib} getType {return CORE_ANTENNACELL} default {error "master method"}}}
proc lib {m args} {if {$m eq "getName"} {return cells};error "library method"}
proc ia {m args} {switch -- $m {getMTerm {return ma} getNet {return n} default {error "iterm method"}}}
proc ig {m args} {switch -- $m {getMTerm {return mg} getNet {return g} default {error "iterm method"}}}
proc ma {m args} {switch -- $m {getName {return A} getSigType {return SIGNAL} getIoType {return INPUT} default {error "mterm method"}}}
proc mg {m args} {switch -- $m {getName {return VSS} getSigType {return GROUND} getIoType {return INOUT} default {error "mterm method"}}}
proc port {m args} {switch -- $m {getName {return i} getNet {return n} getSigType {return SIGNAL} getIoType {return INPUT} default {error "port method"}}}
proc si {m args} {switch -- $m {find_pin {if {$args eq "A"} {return sp};return NULL} liberty_cell {return lc} default {error "STA instance method"}}}
proc sp {m args} {switch -- $m {liberty_port {return lp} port_name {return A} is_driver {return 0} default {error "STA pin method"}}}
proc bp {m args} {switch -- $m {is_top_level_port {return 1} is_driver {return 1} default {error "STA boundary method"}}}
proc lc {m args} {switch -- $m {name {return sg13g2_antennanp} find_liberty_port {if {$args eq "A"} {return lp};return NULL} default {error "Liberty cell method"}}}
proc lp {m args} {
  if {$m ne "capacitance" || [lindex $args 0] ne "corner"} {error "Liberty port method"}
  if {[lindex $args 1] eq "min"} {return 1e-15};if {[lindex $args 1] eq "max"} {return 2e-15}
  error "Liberty corner mode"
}
"""
        for mode in("candidate","full","timing"):
            proc=subprocess.run(["tclsh"],input=(fixture+native.render(request(),mode,a.CORNERS[0])).encode(),capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr.decode());self.assertEqual(proc.stderr,b"")
            raw,marker=proc.stdout.split(b"RV_FAKE_CALLS ",1)
            v,m=native.parse_records(raw)
            self.assertEqual(v["instances"]["D"]["pins"]["A"]["net"],"n")
            self.assertEqual(m["pins"][0]["liberty_pin"],"A")
            self.assertEqual(m["pins"][0]["min"],1e-15)
            calls=bytes.fromhex(marker.decode().strip()).decode()
            if mode=="candidate":
                self.assertIn("write_verilog -include_pwr_gnd /work/routed-views/full.v",calls)
                self.assertIn("write_verilog /work/routed-views/timing.v",calls)
            else:
                self.assertNotIn("read_db",calls)
                self.assertIn("read_verilog /work/routed-views/"+mode+".v",calls)
        SUMMARY["actual_tcl_render_executed_with_synthetic_api"]=True

def main():
    actual=dict(os.environ);out=Path("routed-view-controls");out.mkdir(exist_ok=True)
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status="PASS"if result.wasSuccessful()else"FAIL",source=os.environ["GITHUB_SHA"],
      run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
      tests=result.testsRun,failures=[(t.id(),s)for t,s in result.failures],
      errors=[(t.id(),s)for t,s in result.errors],skipped=[(t.id(),s)for t,s in result.skipped],
      synthetic=SUMMARY,environment_unchanged=dict(os.environ)==actual,**a.FLAGS)
    (out/"controls.json").write_bytes(a.encode(report))
    if dict(os.environ)!=actual:raise AssertionError("real source environment changed")
    return 0 if result.wasSuccessful()else 1
if __name__=="__main__":sys.exit(main())
