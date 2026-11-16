from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
class AfterBatchFourthBoundedPostCTS(BoundedPostCTS):
    id = "NSSOC.AfterBatchFourthBoundedPostCTS"
    name = "Continue setup repair only after reproducing measured three-corner baseline"
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43821353089")
        assert run["head_sha"] == "e89e1020e518428d4db12dde0905cb7e0dc56329"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "8988f4c396c5f9e162764670719ac5e0d49baec60cbf637d8d8ae0439640c3fc"
        meta = api("actions/artifacts/14205930008")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14205930008/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-afterbatchfourthbefore" + short.lower()))
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
class EopAfterBatchFourthDirect(Interfaces):
 Steps=([type('AfterBatchFourthBefore'+n,(BranchSTA,),dict(id='NSSOC.AfterBatchFourthBefore'+n,corner=c))for n,c in CORNERS]
       +[AfterBatchFourthBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
