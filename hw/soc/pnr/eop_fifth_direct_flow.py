from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS,ElectricalPostCTS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset choices {\nTARGET_CHOICES\n}\nset targets [dict keys $choices]\nif {[llength $targets]!=143} {error "Wrong measured resize census"}\nif {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}\nforeach name $targets {\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Replay target preflight mismatch $name"}\n}\nset ports_before {}\nforeach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}\nforeach name $targets {\n lassign [dict get $choices $name] old_master new_master\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}\n replace_cell $name $new_master\n if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}\n}\nif {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n lassign [dict get $before $name] master pins\n if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}\n if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}\n foreach pin [$inst getITerms] {\n  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}\n }\n}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}\ndetailed_placement\ncheck_placement -verbose\nputs "NSSOC_REPLAY_143_MEASURED_BUFFERS_SAME_INCIDENCE"\n'

def measured_targets(step_dir):
    import hashlib,io,json,re,subprocess,zipfile
    repo="repos/Melihakbulut221/nssoc/"
    def api(path):return json.loads(subprocess.check_output(["gh","api",repo+path]))
    run=api("actions/runs/43811737658")
    assert run["head_sha"]=="62cc4ec36c78fa5f28dc800b87fc1f6bef7a00cc" and run["run_attempt"]==1 and run["conclusion"]=="success"
    digest="1a52bd600e592d12bbe76302a86d942c0e7a47451c26d841dda1f51b5296df6a"
    meta=api("actions/artifacts/14201212608")
    assert not meta["expired"] and meta["digest"]=="sha256:"+digest and meta["workflow_run"]["id"]==run["id"] and meta["workflow_run"]["head_sha"]==run["head_sha"]
    blob=subprocess.check_output(["gh","api",repo+"actions/artifacts/14201212608/zip"])
    assert hashlib.sha256(blob).hexdigest()==digest
    z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
    report=json.loads(z.read("result.json"))
    name="run/5-nssoc-sizedslow/max.rpt"
    data=z.read(name)
    assert hashlib.sha256(data).hexdigest()==report["outputs"][name]
    assert report["source_head"]==run["head_sha"] and report["candidate_odb_sha256"]=="06e3133ffbcea6eabe156cbe7107f0a081a01dc31846e3858cc095817121d476"
    targets={};paths=0
    for block in data.decode().split("Startpoint:")[1:]:
        if not re.search(r"(-[\d.]+)\s+slack \(VIOLATED\)",block):continue
        paths+=1
        for line in block.split("data arrival time")[0].splitlines():
            m=re.match(r"\s*\d+\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+[\^v]\s+(\S+)/X \(sg13g2_buf_1\)",line)
            if m and float(m[1])>=0.30:
                targets[m[2]]=max(targets.get(m[2],0),float(m[1]))
    assert paths==1000 and len(targets)==143
    assert all(not any(c in n for c in "{}\\\n\r") for n in targets)
    (Path(step_dir)/"measured-buffer-targets.json").write_text(json.dumps(dict(source_run=run["id"],artifact=meta["id"],archive_sha256=digest,report_sha256=hashlib.sha256(data).hexdigest(),reported_violating_paths=paths,threshold_ns=0.30,targets=targets,scope="Measured slow-path buf1 only. Full three-corner setup/hold and electrical review still required."),indent=2))
    return "\n".join(" {"+name+"} {sg13g2_buf_1 sg13g2_buf_4}"for name in sorted(targets))

class BufferBatchBoundedPostCTS(ElectricalPostCTS):
    id = "NSSOC.BufferBatchBoundedPostCTS"
    name = "Size 143 measured slow-path buffers after reproducing eleventh baseline"
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
        run = api("actions/runs/43811737658")
        assert run["head_sha"] == "62cc4ec36c78fa5f28dc800b87fc1f6bef7a00cc"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "978b62a9ca93737d45ca7e5a7e9b216a81ebbe3d78f6616ed15515c9cfa67066"
        meta = api("actions/artifacts/14201381248")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14201381248/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-bufferbatchbefore" + short.lower()))
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
class EopBufferBatchDirect(Interfaces):
 Steps=([type('BufferBatchBefore'+n,(BranchSTA,),dict(id='NSSOC.BufferBatchBefore'+n,corner=c))for n,c in CORNERS]
       +[BufferBatchBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
