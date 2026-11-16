from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS,GuardedPropagated
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset choices {\nTARGET_CHOICES\n}\nset targets [dict keys $choices]\nif {[llength $targets]!=4} {error "Wrong measured resize census"}\nif {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}\nforeach name $targets {\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Replay target preflight mismatch $name"}\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nforeach name $targets {\n lassign [dict get $choices $name] old_master new_master\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}\n replace_cell $name $new_master\n if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}\n}\nif {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n lassign [dict get $before $name] master pins\n if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}\n if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}\n foreach pin [$inst getITerms] {\n  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}\ndetailed_placement\ncheck_placement -verbose\nputs "NSSOC_PEER_PACKET_4_MEASURED_DRIVERS_SAME_INCIDENCE"\n'

def measured_targets(step_dir):
    import hashlib,io,json,re,subprocess,zipfile
    repo="repos/Melihakbulut221/nssoc/"
    def api(path):return json.loads(subprocess.check_output(["gh","api",repo+path]))
    run=api("actions/runs/43849778016")
    assert run["head_sha"]=="1e83a403b9f0e5114f3d6467307aab1f0fdd473d" and run["run_attempt"]==1 and run["conclusion"]=="success"
    digest="6514d46800cb41621812e3cae5271cb65d14037d70251d4073aee3314a3cb7b1"
    meta=api("actions/artifacts/14217051881")
    assert not meta["expired"] and meta["digest"]=="sha256:"+digest and meta["workflow_run"]["id"]==run["id"] and meta["workflow_run"]["head_sha"]==run["head_sha"]
    blob=subprocess.check_output(["gh","api",repo+"actions/artifacts/14217051881/zip"])
    assert hashlib.sha256(blob).hexdigest()==digest
    z=zipfile.ZipFile(io.BytesIO(blob));report=json.loads(z.read("result.json"))
    assert report["producer"]==43846553091 and report["odb_sha256"]=="19336c05731f493d36db8f54585c9f9002e1242ec24bf3115e85658c35e81c82"
    data=z.read("slow-max.txt");assert hashlib.sha256(data).hexdigest()==report["reports"]["slow-max"]["excerpt_sha256"]
    block=data.decode().split("Startpoint:")[1]
    assert block.splitlines()[0].strip()=="$auto$ff.cc:337:slice$310834"
    assert "u_pcie.flow.packets.link_up_i (net)"in block and "-1.546445"in block
    targets={name:("sg13g2_buf_1","sg13g2_buf_4","X")for name in ["fanout9872","fanout9871","fanout1672"]}
    targets["$abc$735378$auto$blifparse.cc:397:parse_blif$739984"]=("sg13g2_nor2_1","sg13g2_nor2_2","Y")
    for name,(old,new,pin)in targets.items():
        lines=[line for line in block.split("data arrival time")[0].splitlines()if name+"/"+pin+" ("+old+")"in line]
        assert len(lines)==1
        assert float(lines[0].split()[3])>=.30
    (Path(step_dir)/"measured-buffer-targets.json").write_text(json.dumps(dict(source_run=run["id"],artifact=meta["id"],archive_sha256=digest,targets=targets,accepted=False),indent=2))
    return "\n".join(" {"+name+"} {"+old+" "+new+"}"for name,(old,new,pin)in sorted(targets.items()))

class PeerLinkBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.PeerLinkBoundedPostCTS"
    name = "Size four measured packet path drivers after exact baseline reproduction"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index('# Buffer I/O');b=s.index('report_floating_nets -verbose',a)
        assert ECO.count('TARGET_CHOICES')==1
        eco=ECO.replace('TARGET_CHOICES',measured_targets(self.step_dir))
        s=s[:a]+eco+'\n'+s[b:]
        if 'log_cmd repair_design' in s or 'unset_propagated_clock [all_clocks]' in s:
            raise RuntimeError('Unexpected broad repair or ideal clock')
        p=Path(self.step_dir)/'replay_four_drivers.tcl';p.write_text(s);return str(p)
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43846553091")
        assert run["head_sha"] == "5e59db61a03dec59fc0f5aa1bd04c3bc76ce6cdd"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "5342f56810a5be9302ac6a64a466f655d60e41b911af4ff6fd94a5c370f51256"
        meta = api("actions/artifacts/14215899737")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14215899737/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-peerlinkbefore" + short.lower()))
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

class PeerLinkTiming(GuardedPropagated,BoundedPostCTS):
    pass

@Flow.factory.register()
class PeerLinkBuffers(Interfaces):
 Steps=([type('PeerLinkBefore'+n,(BranchSTA,),dict(id='NSSOC.PeerLinkBefore'+n,corner=c))for n,c in CORNERS]
       +[PeerLinkBoundedPostCTS,PeerLinkTiming]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
