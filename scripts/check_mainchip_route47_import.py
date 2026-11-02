"""Cloud regression for the actual /work versus hosted-root import failure."""
import ast, hashlib, json, tempfile
from pathlib import Path
import mainchip_route47_import as adapter
from mainchip_route47_import import WORK, STEMS, import_program, owned_path

def main():
    path = Path("original/scripts/mainchip_original_clock_restoration_native.py")
    raw = path.read_bytes()
    manifest = json.loads(Path("original/scripts/mainchip-bounded-route-host-pins.json").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == manifest["files"]["scripts/mainchip_original_clock_restoration_native.py"]
    tree = ast.parse(raw)
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("tcl_path", "import_tcl")]
    assert len(selected) == 2
    namespace = {"Path": Path}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    original = namespace["import_tcl"]
    original_encoder = namespace["tcl_path"]
    cases = []
    stem = "narrow47-fixed"; source = WORK/(stem+"-base.odb"); patch = WORK/(stem+"-patch.def")
    try: original(source, patch, WORK, stem)
    except AssertionError: cases.append("reproduce actual hosted-root rejection before any native route")
    else: raise AssertionError("frozen regression missing")
    for stem in sorted(STEMS):
        source = WORK/(stem+"-base.odb"); patch = WORK/(stem+"-patch.def")
        got = import_program(original, source, patch, WORK, stem)
        q = lambda p: "{"+str(p)+"}"
        expected = "\n".join(("read_db "+q(source), "read_def -floorplan_initialize "+q(patch),
            "write_def "+q(WORK/(stem+"-single.def")), "read_def -floorplan_initialize "+q(patch),
            "write_def "+q(WORK/(stem+".def")), "write_db "+q(WORK/(stem+".odb"))))+"\n"
        assert got == expected and got.count("read_def -floorplan_initialize ") == 2
        assert namespace["tcl_path"] is original_encoder and original.__globals__ is namespace
        cases.append(stem+" preserves exact six-command two-import sequence and original globals")
    stem="narrow47-fixed";source=WORK/(stem+"-base.odb");patch=WORK/(stem+"-patch.def")
    for label,args in [
        ("foreign-source",(original,Path("/tmp/a.odb"),patch,WORK,stem)),
        ("foreign-patch",(original,source,Path("/tmp/a.def"),WORK,stem)),
        ("foreign-output",(original,source,patch,Path("/tmp"),stem)),
        ("unknown-stem",(original,source,patch,WORK,"bad")),
        ("injected-stem",(original,source,patch,WORK,"x}\nexit")),
        ("wrong-source",(original,WORK/"narrow47-reversed-base.odb",patch,WORK,stem)),
        ("wrong-patch",(original,source,WORK/"narrow47-reversed-patch.def",WORK,stem)),
        ("nonfunction",(None,source,patch,WORK,stem))]:
        try: import_program(*args)
        except ValueError: cases.append("refuse "+label)
        else: raise AssertionError(label)
    for value in ["/tmp/x", str(WORK)+"/../x", str(WORK)+"/sub/x", str(WORK)+"/x}\nexit", str(WORK)+"/$x", str(WORK)+"/[exit]", str(WORK)+"/x\\y"]:
        try: owned_path(value)
        except ValueError: cases.append("refuse unsafe path "+repr(value))
        else: raise AssertionError(value)
    # A real escaping symlink under the owned path must be rejected.
    with tempfile.TemporaryDirectory() as temporary:
        owned = Path(temporary)/"owned";owned.mkdir()
        link=owned/"route47-control-link";link.symlink_to("/tmp")
        adapter.WORK=owned
        try:
            try: owned_path(link)
            except ValueError: cases.append("refuse actual symlink escape")
            else: raise AssertionError("symlink")
        finally: adapter.WORK=WORK
    assert len(cases)==20
    out=Path("route47-import-controls");out.mkdir()
    (out/"result.json").write_text(json.dumps(dict(count=len(cases),cases=cases,
        original_function_source_sha256=hashlib.sha256(raw).hexdigest(),native_executed=False,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")

if __name__=="__main__": main()
