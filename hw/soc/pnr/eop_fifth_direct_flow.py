from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset choices {\n {$auto$ff.cc:337:slice$164559} {sg13g2_dfrbpq_1 sg13g2_dfrbpq_2}\n {$abc$735341$auto$blifparse.cc:397:parse_blif$762643} {sg13g2_buf_1 sg13g2_buf_4}\n {fanout8221} {sg13g2_buf_1 sg13g2_buf_4}\n {$abc$735341$auto$blifparse.cc:397:parse_blif$762805} {sg13g2_buf_1 sg13g2_buf_4}\n {fanout7273} {sg13g2_buf_1 sg13g2_buf_4}\n}\nset targets [dict keys $choices]\nif {[llength $targets]!=5} {error "Wrong measured resize census"}\nif {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}\nforeach name $targets {\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Replay target preflight mismatch $name"}\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nforeach name $targets {\n lassign [dict get $choices $name] old_master new_master\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}\n replace_cell $name $new_master\n if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}\n}\nif {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n lassign [dict get $before $name] master pins\n if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}\n if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}\n foreach pin [$inst getITerms] {\n  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}\ndetailed_placement\ncheck_placement -verbose\nputs "NSSOC_REPLAY_FIVE_DRIVERS_SAME_INCIDENCE"\n'

class EighthBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.EighthBoundedPostCTS"
    name = "Size five measured replay drivers after reproducing seventh baseline"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index('# Buffer I/O');b=s.index('report_floating_nets -verbose',a)
        s=s[:a]+ECO+'\n'+s[b:]
        if 'log_cmd repair_design' in s or 'unset_propagated_clock [all_clocks]' in s:
            raise RuntimeError('Unexpected broad repair or ideal clock')
        p=Path(self.step_dir)/'replay_five_drivers.tcl';p.write_text(s);return str(p)
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43804619916")
        assert run["head_sha"] == "bcc9ed076aa249a52b2c40604c9799803ceb593d"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "0fd15cdc771252a03e491e315591432968f0560c1b637a35e95afe5daf32c59e"
        meta = api("actions/artifacts/14197719218")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14197719218/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-eighthbefore" + short.lower()))
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
class EopEighthDirect(Interfaces):
 Steps=([type('EighthBefore'+n,(BranchSTA,),dict(id='NSSOC.EighthBefore'+n,corner=c))for n,c in CORNERS]
       +[EighthBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
