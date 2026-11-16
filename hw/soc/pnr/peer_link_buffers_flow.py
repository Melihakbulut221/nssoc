from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS,GuardedPropagated
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = "\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset choices {\nTARGET_CHOICES\n}\nset targets [dict keys $choices]\nif {[llength $targets]!=1} {error \"Wrong measured resize census\"}\nif {[llength [info commands replace_cell]] != 1} {error \"Missing native replace_cell\"}\nforeach name $targets {\n set inst [$block findInst $name]\n if {$inst eq \"NULL\" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error \"Replay target preflight mismatch $name\"}\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nforeach name $targets {\n lassign [dict get $choices $name] old_master new_master\n set inst [$block findInst $name]\n if {$inst eq \"NULL\" || [[$inst getMaster] getName] ne $old_master} {error \"Unexpected measured driver $name\"}\n set driver [$block findInst {$abc$735378$auto$blifparse.cc:397:parse_blif$770345}]\n if {$driver eq \"NULL\" || [[$driver getMaster] getName] ne \"sg13g2_nor3_2\"} {error \"Wrong advertiser driver\"}\n if {[[$inst findITerm A] getNet] ne [[$driver findITerm Y] getNet]} {error \"Buffer is not on measured driver net\"}\n lassign [$driver getLocation] dx dy\n lassign [$inst getLocation] bx by\n set old_distance [expr {abs($bx-$dx)+abs($by-$dy)}]\n set box [$driver getBBox]\n set nx [expr {[$box xMax]+[$block getDbUnitsPerMicron]}]\n puts \"NSSOC_ADVERTISER_BUFFER_BEFORE driver=[$driver getLocation] buffer=[$inst getLocation] distance=$old_distance\"\n $inst setLocation $nx $dy\n $inst setPlacementStatus PLACED\n if {[[$inst getMaster] getName] ne $new_master} {error \"Replacement failed\"}\n}\nif {[llength [$block getInsts]] != [dict size $before]} {error \"Instance census changed\"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n lassign [dict get $before $name] master pins\n if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}\n if {[[$inst getMaster] getName] ne $master} {error \"Unexpected master change\"}\n foreach pin [$inst getITerms] {\n  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error \"Incidence changed\"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error \"Port incidence changed\"}}\ndetailed_placement\ncheck_placement -verbose\nset buffer [$block findInst wire7226]\nlassign [$driver getLocation] dx dy\nlassign [$buffer getLocation] bx by\nset new_distance [expr {abs($bx-$dx)+abs($by-$dy)}]\nputs \"NSSOC_ADVERTISER_BUFFER_AFTER driver=[$driver getLocation] buffer=[$buffer getLocation] distance=$new_distance\"\nif {$new_distance >= $old_distance} {error \"Legalized buffer did not get closer to the measured driver\"}\nputs \"NSSOC_ADVERTISER_BUFFER_MOVED_SAME_MASTERS_AND_INCIDENCE\"\n"

def measured_targets(step_dir):
    import hashlib,io,json,re,subprocess,zipfile
    repo="repos/Melihakbulut221/nssoc/"
    def api(path):return json.loads(subprocess.check_output(["gh","api",repo+path]))
    run=api("actions/runs/43858944925")
    assert run["head_sha"]=="dffbd7410f062992d61a5971046caf999c6bce1c" and run["run_attempt"]==1 and run["conclusion"]=="success"
    digest="a749ede36baf1d45700a08d6b5916ff4ce2c3b64695c2f4dd673784aacb9d9e3"
    meta=api("actions/artifacts/14222692165")
    assert not meta["expired"] and meta["digest"]=="sha256:"+digest and meta["workflow_run"]["id"]==run["id"] and meta["workflow_run"]["head_sha"]==run["head_sha"]
    blob=subprocess.check_output(["gh","api",repo+"actions/artifacts/14222692165/zip"])
    assert hashlib.sha256(blob).hexdigest()==digest
    z=zipfile.ZipFile(io.BytesIO(blob));report=json.loads(z.read("result.json"))
    assert report["producer"]==43856498799 and report["odb_sha256"]=="6cc9bcd0a353ddcd24073560d75413f109386b8236a42ca4ff124566412458b3"
    data=z.read("slow-max.txt");assert hashlib.sha256(data).hexdigest()==report["reports"]["slow-max"]["excerpt_sha256"]
    block=data.decode().split("Startpoint:")[1]
    assert block.splitlines()[0].strip()=="$auto$ff.cc:337:slice$160053"
    assert "u_pcie.advertiser.index[1]"in block and "-0.944498"in block
    driver="$abc$735378$auto$blifparse.cc:397:parse_blif$770345"
    lines=[line for line in block.split("data arrival time")[0].splitlines() if driver+"/Y (sg13g2_nor3_2)" in line]
    assert len(lines)==1 and float(lines[0].split()[1])>=.08 and float(lines[0].split()[3])>=.7
    assert "wire7226/A (sg13g2_buf_8)" in block
    targets={"wire7226":("sg13g2_buf_8","sg13g2_buf_8","X")}
    (Path(step_dir)/"measured-buffer-targets.json").write_text(json.dumps(dict(source_run=run["id"],artifact=meta["id"],archive_sha256=digest,targets=targets,accepted=False),indent=2))
    return "\n".join(" {"+name+"} {"+old+" "+new+"}"for name,(old,new,pin)in sorted(targets.items()))

class PeerLinkBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.PeerLinkBoundedPostCTS"
    name = "Move measured advertiser buffer next to driver with unchanged connectivity"
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
        run = api("actions/runs/43856498799")
        assert run["head_sha"] == "a8e22a4ee7c7483d7fb0e82099d79c54f69e3be7"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "cf9b4755b4fa872ae721e77927bdf49d061e07add60ba4883f146c35dcd0b304"
        meta = api("actions/artifacts/14222406423")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14222406423/zip"])
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
