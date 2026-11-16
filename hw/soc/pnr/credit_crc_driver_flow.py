from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces, BoundedPostCTS
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set choices {
 {fanout9730} {sg13g2_buf_1 sg13g2_buf_4}
 {fanout9729} {sg13g2_buf_1 sg13g2_buf_4}
 {$abc$735341$auto$blifparse.cc:397:parse_blif$770552} {sg13g2_buf_1 sg13g2_buf_4}
}
set targets [dict keys $choices]
if {[llength $targets]!=3} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set ports_before {}
foreach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}
foreach name $targets {
 lassign [dict get $choices $name] old_master new_master
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}
 replace_cell $name $new_master
 if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}
}
if {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 lassign [dict get $before $name] master pins
 if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}
# Taper the measured high-capacitance buf8 input with native buf2.
set origin [$block findInst wire3244]
if {$origin eq "NULL" || [[$origin getMaster] getName] ne "sg13g2_buf_8"} {error "Taper sink mismatch"}
set sink [$origin findITerm A];set net [$sink getNet];set drivers {}
if {$net eq "NULL" || [llength [$net getBTerms]]!=0 || [llength [$net getITerms]]!=2} {error "Taper source is not isolated"}
foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers "[[$pin getInst] getName]/[[$pin getMTerm] getName]"}}
if {[llength $drivers]!=1 || [lindex $drivers 0] ne {$abc$735341$auto$blifparse.cc:397:parse_blif$770517/Y}} {error "Taper driver mismatch"}
set supply {}
foreach pin [$origin getITerms] {
 if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {
  if {[$pin getNet] eq "NULL"} {error "Taper supply missing"}
  dict set supply [[$pin getMTerm] getName] [$pin getNet]
 }
}
if {[dict size $supply]!=2} {error "Taper supply census"}
set master [[ord::get_db] findMaster sg13g2_buf_2]
if {$master eq "NULL" || [$block findInst nssoc_linkup_taper] ne "NULL" || [$block findNet nssoc_linkup_taper_out] ne "NULL"} {error "Taper master or collision"}
set cell [odb::dbInst_create $block $master nssoc_linkup_taper];set next [odb::dbNet_create $block nssoc_linkup_taper_out]
lassign [$origin getLocation] x y;$cell setLocation $x $y;$cell setOrient [$origin getOrient];$cell setPlacementStatus PLACED
foreach pin [$cell getITerms] {
 set pn [[$pin getMTerm] getName]
 if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {$pin connect [dict get $supply $pn]} elseif {$pn ni {A X}} {error "Taper terminal"}
}
[$cell findITerm A] connect $net;[$cell findITerm X] connect $next;$sink connect $next
if {[llength [$block getInsts]]!=[dict size $before]+1 || [llength [$net getITerms]]!=2 || [llength [$next getITerms]]!=2} {error "Taper census"}
foreach inst [$block getInsts] {
 set name [$inst getName];if {$name eq "nssoc_linkup_taper"} {continue}
 lassign [dict get $before $name] master pins
 foreach pin [$inst getITerms] {
  set pn [[$pin getMTerm] getName];set expected [dict get $pins $pn]
  if {$name eq "wire3244" && $pn eq "A"} {set expected $next}
  if {[$pin getNet] ne $expected} {error "Taper unrelated incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Taper port changed"}}
puts "NSSOC_LINKUP_TAPER_STRUCTURAL_PASS"

detailed_placement
check_placement -verbose
puts "NSSOC_SHARED_PCIE_DRIVERS_SAME_INCIDENCE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size measured new EOP link-up critical drivers"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "reset_buffer_eco.tcl"
        q.write_text(s)
        return str(q)

class SecondBoundedPostCTS(BoundedPostCTS):
    id = "NSSOC.SecondBoundedPostCTS"
    name = "Continue setup repair only after reproducing measured three-corner baseline"
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43789589953")
        assert run["head_sha"] == "919cd5b37c139296ee0740ed58e921c6a62ce9c4"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "337cc894ac328b82045555b663897c7a7ecbbb066bf01eb7590523bb546ff0f2"
        meta = api("actions/artifacts/14191533295")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14191533295/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-continuationbefore" + short.lower()))
            assert len(dirs) == 1, (short, dirs)
            assert not (dirs[0] / "unpropagated.rpt").read_text().strip()
            metrics = json.loads((dirs[0] / "state_out.json").read_text())["metrics"]
            reference = expected["measurements"][corner]
            assert reference
            for key, value in reference.items():
                actual = metrics[key]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-6), (key, actual, value)
                else:
                    assert actual == value, (key, actual, value)
            comparisons[corner] = reference
        (Path(self.step_dir) / "baseline-reproduction.json").write_text(
            json.dumps(dict(source_run=run["id"], artifact_sha256=digest,
                            measured_baseline_matches=True, corners=comparisons), indent=2))
        return super().run(state_in, **kwargs)

class ThirdBoundedPostCTS(BoundedPostCTS):
    id = "NSSOC.ThirdBoundedPostCTS"
    name = "Continue setup repair only after reproducing measured three-corner baseline"
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43791735845")
        assert run["head_sha"] == "dc057ddbca86530214846164e767b53b9cc1165f"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "6b1283de222e8621f0f06380d4c0beb9f4121decd79399a510bc417c62d2aba2"
        meta = api("actions/artifacts/14193400320")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14193400320/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-thirdbefore" + short.lower()))
            assert len(dirs) == 1, (short, dirs)
            assert not (dirs[0] / "unpropagated.rpt").read_text().strip()
            metrics = json.loads((dirs[0] / "state_out.json").read_text())["metrics"]
            reference = expected["measurements"][corner]
            assert reference
            for key, value in reference.items():
                actual = metrics[key]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-6), (key, actual, value)
                else:
                    assert actual == value, (key, actual, value)
            comparisons[corner] = reference
        (Path(self.step_dir) / "baseline-reproduction.json").write_text(
            json.dumps(dict(source_run=run["id"], artifact_sha256=digest,
                            measured_baseline_matches=True, corners=comparisons), indent=2))
        return super().run(state_in, **kwargs)

class FourthBoundedPostCTS(BoundedPostCTS):
    id = "NSSOC.FourthBoundedPostCTS"
    name = "Continue setup repair only after reproducing measured three-corner baseline"
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43793144949")
        assert run["head_sha"] == "b5c8c83a38a2630e0832d07874e32e92f6e8c851"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "148c7344d012ccf9472572f5f02192c59516e5d88364ceb3c676baeecf6cb812"
        meta = api("actions/artifacts/14194550822")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14194550822/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-fourthbefore" + short.lower()))
            assert len(dirs) == 1, (short, dirs)
            assert not (dirs[0] / "unpropagated.rpt").read_text().strip()
            metrics = json.loads((dirs[0] / "state_out.json").read_text())["metrics"]
            reference = expected["measurements"][corner]
            assert reference
            for key, value in reference.items():
                actual = metrics[key]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    assert math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-6), (key, actual, value)
                else:
                    assert actual == value, (key, actual, value)
            comparisons[corner] = reference
        (Path(self.step_dir) / "baseline-reproduction.json").write_text(
            json.dumps(dict(source_run=run["id"], artifact_sha256=digest,
                            measured_baseline_matches=True, corners=comparisons), indent=2))
        return super().run(state_in, **kwargs)

@Flow.factory.register()
class AckChipResetSized(Interfaces):
 Steps=([ResetBufferECO, BoundedPostCTS]
        +[type("ContinuationBefore"+n,(BranchSTA,),dict(id="NSSOC.ContinuationBefore"+n,corner=c))for n,c in CORNERS]
        +[SecondBoundedPostCTS]
        +[type("ThirdBefore"+n,(BranchSTA,),dict(id="NSSOC.ThirdBefore"+n,corner=c))for n,c in CORNERS]
        +[ThirdBoundedPostCTS]
        +[type("FourthBefore"+n,(BranchSTA,),dict(id="NSSOC.FourthBefore"+n,corner=c))for n,c in CORNERS]
        +[FourthBoundedPostCTS]
        +[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS])
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
