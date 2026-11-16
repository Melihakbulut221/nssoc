from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = "\nset block [ord::get_db_block]\nif {[llength [info commands insert_buffer]]!=1} {error \"Pinned runtime lacks native insert_buffer\"}\nset driver_name {$abc$735303$auto$blifparse.cc:397:parse_blif$736297}\nset sink_name {$abc$735303$auto$blifparse.cc:397:parse_blif$736298}\nset driver [$block findInst $driver_name]\nset sink [$block findInst $sink_name]\nif {$driver eq \"NULL\" || $sink eq \"NULL\"} {error \"Missing measured endpoints\"}\nif {[[$driver getMaster] getName] ne \"sg13g2_o21ai_1\" || [[$sink getMaster] getName] ne \"sg13g2_nand4_1\"} {error \"Measured master mismatch\"}\nset output [$driver findITerm Y]\nset input [$sink findITerm D]\nset original_net [$output getNet]\nif {$original_net eq \"NULL\" || [$input getNet] ne $original_net} {error \"Measured arc missing\"}\nif {[$original_net getName] ne {$abc$735303$new_n38990}} {error \"Measured net mismatch\"}\nif {[llength [$original_net getITerms]]!=2 || [llength [$original_net getBTerms]]!=0} {error \"Unexpected load incidence\"}\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nset nets_before [llength [$block getNets]]\nset newname nssoc_rx_ownership_wire_buf\nif {[$block findInst $newname] ne \"NULL\"} {error \"Buffer name collision\"}\ninsert_buffer -buffer_cell sg13g2_buf_8 -net [$original_net getName] -buffer_name $newname -net_name nssoc_rx_ownership_wire_split\nset added {}\nforeach inst [$block getInsts] {\n if {![dict exists $before [$inst getName]]} {lappend added $inst}\n}\nif {[llength $added]!=1} {error \"Expected exactly one newly inserted instance\"}\nset buf [lindex $added 0]\nset newname [$buf getName]\nif {[[$buf getMaster] getName] ne \"sg13g2_buf_8\"} {error \"Unexpected inserted master\"}\nputs \"NSSOC_INSERTED_BUFFER_ACTUAL_NAME $newname\"\nif {[llength [$block getInsts]]!=[expr {[dict size $before]+1}] || [llength [$block getNets]]!=[expr {$nets_before+1}]} {error \"Unexpected topology count\"}\nset upstream [$output getNet]\nset downstream [$input getNet]\nif {$upstream eq $downstream || [[$buf findITerm A] getNet] ne $upstream || [[$buf findITerm X] getNet] ne $downstream} {error \"Buffer polarity/connectivity mismatch\"}\nforeach net [list $upstream $downstream] {\n if {[llength [$net getITerms]]!=2 || [llength [$net getBTerms]]!=0} {error \"Unexpected buffered arc incidence\"}\n}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n if {$name eq $newname} {continue}\n lassign [dict get $before $name] master pins\n if {[[$inst getMaster] getName] ne $master} {error \"Unintended cell replacement\"}\n if {[llength [$inst getITerms]]!=[dict size $pins]} {error \"Pin census changed\"}\n foreach pin [$inst getITerms] {\n  set pname [[$pin getMTerm] getName]\n  if {($name eq $driver_name && $pname eq \"Y\") || ($name eq $sink_name && $pname eq \"D\")} {continue}\n  if {[$pin getNet] ne [dict get $pins $pname]} {error \"Unrelated connectivity changed\"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error \"Port incidence changed\"}}\ndetailed_placement\ncheck_placement -verbose\nputs \"NSSOC_RX_SINGLE_NONINVERTING_BUFFER_TOPOLOGY_VERIFIED\"\n"

class AckRxWireBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.AckRxWireBoundedPostCTS"
    name = "Insert one noninverting buffer on authenticated RX ownership arc"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index('# Buffer I/O');b=s.index('report_floating_nets -verbose',a)
        eco=ECO
        s=s[:a]+eco+'\n'+s[b:]
        if 'log_cmd repair_design' in s or 'unset_propagated_clock [all_clocks]' in s:
            raise RuntimeError('Unexpected broad repair or ideal clock')
        p=Path(self.step_dir)/'replay_four_drivers.tcl';p.write_text(s);return str(p)
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43830177430")
        assert run["head_sha"] == "d18e699335cee1bdbd24696c2f085ece7164636e"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "d892bd679d734b78f4adf919abea3d5db93e8d05f446cb6721171139ace1f421"
        meta = api("actions/artifacts/14208688760")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14208688760/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-ackrxwirebefore" + short.lower()))
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
class AckRxWireBuffer(Interfaces):
 Steps=([type('AckRxWireBefore'+n,(BranchSTA,),dict(id='NSSOC.AckRxWireBefore'+n,corner=c))for n,c in CORNERS]
       +[AckRxWireBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
