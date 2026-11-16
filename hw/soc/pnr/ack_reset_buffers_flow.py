from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset choices {\nTARGET_CHOICES\n}\nset targets [dict keys $choices]\nif {[llength $targets]!=4} {error "Wrong measured resize census"}\nif {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}\nforeach name $targets {\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Replay target preflight mismatch $name"}\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nforeach name $targets {\n lassign [dict get $choices $name] old_master new_master\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}\n replace_cell $name $new_master\n if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}\n}\nif {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n lassign [dict get $before $name] master pins\n if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}\n if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}\n foreach pin [$inst getITerms] {\n  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}\ndetailed_placement\ncheck_placement -verbose\nputs "NSSOC_REPLAY_4_MEASURED_BUFFERS_SAME_INCIDENCE"\n'

def measured_targets(step_dir):
    import hashlib,io,json,re,subprocess,zipfile
    repo="repos/Melihakbulut221/nssoc/"
    def api(path):return json.loads(subprocess.check_output(["gh","api",repo+path]))
    run=api("actions/runs/43837176874")
    assert run["head_sha"]=="c32ecf118f613cb5a0f4489edff1953c44130211" and run["run_attempt"]==1 and run["conclusion"]=="success"
    digest="5ad2b3bef9055f1df499f880ff809d726cde7312f33ec7fa6ef0f8ce7e048da3"
    meta=api("actions/artifacts/14211062453")
    assert not meta["expired"] and meta["digest"]=="sha256:"+digest and meta["workflow_run"]["id"]==run["id"] and meta["workflow_run"]["head_sha"]==run["head_sha"]
    blob=subprocess.check_output(["gh","api",repo+"actions/artifacts/14211062453/zip"])
    assert hashlib.sha256(blob).hexdigest()==digest
    z=zipfile.ZipFile(io.BytesIO(blob));report=json.loads(z.read("result.json"))
    data=z.read("slow-max.txt");assert hashlib.sha256(data).hexdigest()==report["reports"]["slow-max"]["excerpt_sha256"]
    assert report["producer"]==43834590445
    blocks=data.decode().split("Startpoint:")[1:4]
    assert len(blocks)==3
    assert blocks[0].splitlines()[0].strip()=="$auto$ff.cc:337:slice$343651"
    assert "u_pcie.flow.packets.retry.rst_ni (net)" in blocks[0] and "-1.063933" in blocks[0]
    assert "u_pcie.flow.packets.retry.ack_delta_q[3] (net)" in blocks[2]
    targets={}
    for block in blocks:
        for line in block.split("data arrival time")[0].splitlines():
            m=re.match(r"\s*\d+\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+[\^v]\s+(\S+)/X \(sg13g2_buf_1\)",line)
            if m and float(m[1])>=.30:
                targets[m[2]]=max(targets.get(m[2],0),float(m[1]))
    expected={"fanout9648","fanout2348","fanout4502","fanout3424"}
    assert set(targets)==expected
    (Path(step_dir)/"measured-buffer-targets.json").write_text(json.dumps(dict(source_run=run["id"],artifact=meta["id"],archive_sha256=digest,targets=targets,accepted=False),indent=2))
    return "\n".join(" {"+name+"} {sg13g2_buf_1 sg13g2_buf_4}"for name in sorted(targets))

class AckResetBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.AckResetBoundedPostCTS"
    name = "Size 4 measured slow-path buffers after reproducing RX buffer baseline"
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
        run = api("actions/runs/43834590445")
        assert run["head_sha"] == "eb18ae3599f828157b8f0e4da7c350f4432f2c37"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "0c4e12a532f509f60bdac7ef58acd0821edc7d62ef64201b20ce73c7332c9e16"
        meta = api("actions/artifacts/14211456069")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14211456069/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-ackresetbefore" + short.lower()))
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
class AckResetBuffers(Interfaces):
 Steps=([type('AckResetBefore'+n,(BranchSTA,),dict(id='NSSOC.AckResetBefore'+n,corner=c))for n,c in CORNERS]
       +[AckResetBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
