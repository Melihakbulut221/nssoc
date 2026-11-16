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

class DriverAdjacentTaper(ElectricalPostCTS):
    id = "NSSOC.DriverAdjacentTaper"
    name = "Move existing taper beside weak source after reproducing measured baseline"

    def get_script_path(self):
        source = Path(super().get_script_path()).read_text()
        a = source.index("# Buffer I/O")
        b = source.index("report_floating_nets -verbose", a)
        move = r"""
set block [ord::get_db_block]
set taper [$block findInst nssoc_linkup_taper]
set driver [$block findInst {$abc$735341$auto$blifparse.cc:397:parse_blif$770517}]
set sink [$block findInst wire3244]
if {$taper eq "NULL" || $driver eq "NULL" || $sink eq "NULL"} {error "Missing measured taper path"}
if {[[$taper getMaster] getName] ne "sg13g2_buf_2" || [[$driver getMaster] getName] ne "sg13g2_o21ai_1"} {error "Taper source master drift"}
set input [[$taper findITerm A] getNet]
set output [[$taper findITerm X] getNet]
if {$input eq "NULL" || $output eq "NULL" || $input ne [[$driver findITerm Y] getNet] || $output ne [[$sink findITerm A] getNet]} {error "Taper connectivity drift"}
if {[llength [$input getITerms]]!=2 || [llength [$output getITerms]]!=2 || [llength [$input getBTerms]] || [llength [$output getBTerms]]} {error "Taper branch is not isolated"}
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set ports {}
foreach port [$block getBTerms] {dict set ports [$port getName] [$port getNet]}
lassign [$driver getLocation] dx dy
lassign [$taper getLocation] tx ty
set old_distance [expr {abs($dx-$tx)+abs($dy-$ty)}]
$taper setLocation $dx $dy
$taper setOrient [$driver getOrient]
$taper setPlacementStatus PLACED
detailed_placement
check_placement -verbose
lassign [$driver getLocation] dx dy
lassign [$taper getLocation] tx ty
set new_distance [expr {abs($dx-$tx)+abs($dy-$ty)}]
if {$new_distance >= $old_distance} {error "Legalized taper did not move closer to source"}
if {[llength [$block getInsts]]!=[dict size $before]} {error "Taper move changed instance census"}
foreach inst [$block getInsts] {
 lassign [dict get $before [$inst getName]] master pins
 if {[[$inst getMaster] getName] ne $master} {error "Taper move changed master"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Taper move changed connectivity"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports [$port getName]]} {error "Taper move changed port"}}
puts "NSSOC_DRIVER_ADJACENT_TAPER_PASS old_distance_dbu=$old_distance new_distance_dbu=$new_distance"
"""
        source = source[:a] + move + chr(10) + source[b:]
        if "log_cmd repair_design" in source or "unset_propagated_clock [all_clocks]" in source:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        out = Path(self.step_dir) / "driver_adjacent_taper.tcl"
        out.write_text(source)
        return str(out)

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

@Flow.factory.register()
class AckChipResetSized(Interfaces):
 Steps=([ResetBufferECO, BoundedPostCTS]
        +[type("ContinuationBefore"+n,(BranchSTA,),dict(id="NSSOC.ContinuationBefore"+n,corner=c))for n,c in CORNERS]
        +[DriverAdjacentTaper]
        +[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS])
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
