from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces,BoundedPostCTS
from corrpre_postcts_flow import CORNERS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
class SixthBoundedPostCTS(BoundedPostCTS):
    id = "NSSOC.SixthBoundedPostCTS"
    name = "Continue setup repair only after reproducing measured three-corner baseline"
    def run(self, state_in, **kwargs):
        import hashlib, io, json, math, subprocess, zipfile
        repo = "repos/Melihakbulut221/nssoc/"
        def api(path):
            return json.loads(subprocess.check_output(["gh", "api", repo + path]))
        run = api("actions/runs/43801167959")
        assert run["head_sha"] == "119b202942c561b7797acdb9e9cc10f879c5ac3d"
        assert run["conclusion"] == "success" and run["run_attempt"] == 1
        digest = "e210cd85d9e9d7231b9935f124922eb116ca5b0d87f29cf900dbf5869132f269"
        meta = api("actions/artifacts/14196543944")
        assert not meta["expired"] and meta["digest"] == "sha256:" + digest
        assert meta["workflow_run"]["id"] == run["id"]
        assert meta["workflow_run"]["head_sha"] == run["head_sha"]
        data = subprocess.check_output(["gh", "api", repo + "actions/artifacts/14196543944/zip"])
        assert hashlib.sha256(data).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = json.loads(archive.read("result.json"))
        assert expected["source_head"] == run["head_sha"]
        assert expected["sources_unchanged"] and expected["returncode"] == 0
        assert expected["accepted"] is False
        comparisons = {}
        for short, corner in CORNERS:
            dirs = list(Path(self.step_dir).parent.glob("*-nssoc-sixthbefore" + short.lower()))
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
class EopSixthDirect(Interfaces):
 Steps=([type('SixthBefore'+n,(BranchSTA,),dict(id='NSSOC.SixthBefore'+n,corner=c))for n,c in CORNERS]
       +[SixthBoundedPostCTS]
       +[type('Sized'+n,(BranchSTA,),dict(id='NSSOC.Sized'+n,corner=c))for n,c in CORNERS])
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
