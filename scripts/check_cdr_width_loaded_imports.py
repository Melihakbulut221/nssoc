#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted isolated imports of the exact execution successor; no native calls."""
import argparse,ast,hashlib,json,os,re,subprocess,sys,tempfile,traceback
from pathlib import Path,PurePosixPath
import cdr_width_loaded_execution_admission as a

ROOT=Path(__file__).resolve().parents[1]
SELF="scripts/check_cdr_width_loaded_imports.py"
REVIEW="docs/evidence/cdr-width-loaded-import-unit-source-review-20261029.json"
ENTRIES=["scripts/cloud_cdr_width_loaded.py","scripts/cloud_cdr_width_loaded_stage.py",
 "scripts/cdr_width_loaded_execution_admission.py","scripts/cdr_width_loaded_result.py"]
EXPECTED={'scripts/audit_cloud_route_annotation.py': {'bytes': 9326, 'sha256': '88e5c8ae53fdfe03fae68b35983ebf63784c325cdf143a4f04c6d8096a3be64b'}, 'scripts/audit_cloud_routed_endpoints.py': {'bytes': 10224, 'sha256': '7ac4b12b49e25b276e57cdbe98cf401b19868713cdbfa1f40217d8116bb0c076'}, 'scripts/audit_cloud_routed_hold_conflicts.py': {'bytes': 6850, 'sha256': '5aab0a1aa2e12515a6ffe5c94d0920672b50aafd7bcdee4e8c853f26d90818ee'}, 'scripts/branch_hold_targets.py': {'bytes': 5633, 'sha256': '4a6fc92fd4ec974cfa3ec36ae5ad6e01f7c6ad3b2419e1651a0bc48b87568cbc'}, 'scripts/build_pcie_local_vco_hybrid_v6.py': {'bytes': 18968, 'sha256': 'ab2962f0c47cc89029866761992bfdd87ab1d5649920b8bc8edaa1c54bbe5a3f'}, 'scripts/candidate_hold_conflicts.py': {'bytes': 5623, 'sha256': '1ab6d7159278e68370f20a2bd6c6943e4df4efbe315a8764871559f63cedf3f5'}, 'scripts/cdr_v59_binding_rc_source.py': {'bytes': 20136, 'sha256': 'bec7865bded1e56fc373dc57cd52758efa70702ffc98b30e67274c720cdd728f'}, 'scripts/cdr_v59_font_roundtrip_contract.py': {'bytes': 13654, 'sha256': 'efa50460da1756dc4b1711083967a657e72079cb7e500d899f05a9d807169b10'}, 'scripts/cdr_v59_serialized_shape_diagnostic.py': {'bytes': 10893, 'sha256': '1c63677847ff2d91ad940f82919775a6a0a48e7122be69be9482b7d0834e668f'}, 'scripts/cdr_v59_tail_access_runtime.py': {'bytes': 3862, 'sha256': '946c08060f099e99f49ac35e559324b1e445d4c3865cfa7be954fa6e75db6176'}, 'scripts/cdr_v59_tail_loaded_admission.py': {'bytes': 15756, 'sha256': 'b81a711cb1ee261f4aad22e3920438b3dcd30bd71733e058f75c1fb78a62692e'}, 'scripts/cdr_v59_tail_loaded_terminal.py': {'bytes': 5526, 'sha256': 'b98959e391a614f10969a2430f89d9ee6379e7e0f4a968846ae420c89a210e90'}, 'scripts/cdr_width_loaded_admission.py': {'bytes': 26301, 'sha256': '45f5beecc013eeeb839214888b427745910b04bed3bb9d111c3ea5d56c32eb63'}, 'scripts/cdr_width_loaded_execution_admission.py': {'bytes': 15809, 'sha256': '21efaad5ef1a90cfa7de4e9675be1e2d7ebdd550f6dbd88ea59055a87f9d74e8'}, 'scripts/cdr_width_loaded_publication.py': {'bytes': 12475, 'sha256': '49cf14ad46b418fe44f8044f510ad0c9fa5e75e42b96db053554e5880bfcac74'}, 'scripts/cdr_width_loaded_result.py': {'bytes': 6377, 'sha256': '468dd60192add0313bd64bef27a0829e6aa0bc15381e9f81b051048681dbb00f'}, 'scripts/cloud_cdr500_input_access_v58_physical.py': {'bytes': 14338, 'sha256': '559d340a818d5ecfd8bc9965c25e0942fe98cb956087b419c4463e296e794898'}, 'scripts/cloud_cdr500_resistor_v59_physical.py': {'bytes': 12688, 'sha256': 'c17f43e8896e62e4f7e088821e87143e51cd9e5771184f85ce72802bbc99e315'}, 'scripts/cloud_cdr_pd_vi.py': {'bytes': 22182, 'sha256': 'a319d6ba9b7a26964e29355e76b34685fff7ff35199ca5a8dbdd4a62031d9c33'}, 'scripts/cloud_cdr_v59_annotation_diagnostic.py': {'bytes': 14312, 'sha256': 'ade3551da4e78eaf02920e688e7886fa55b1f2ee9c4c798854f181402ef0f825'}, 'scripts/cloud_cdr_v59_binding_rc.py': {'bytes': 15761, 'sha256': '647af19c78158045739b2589d61a2962bbff69e230b593ccb33019550edbd709'}, 'scripts/cloud_cdr_v59_font_recovery.py': {'bytes': 18284, 'sha256': '968ed10148f855d1fa1f9a9533d923ea3c0010889387d87e16e58ac87793758e'}, 'scripts/cloud_cdr_v59_serialized_shape_diagnostic.py': {'bytes': 15771, 'sha256': '7bcfc52160657696e5aeca72fbf68b2c21bc4ad284fc598e3d63d049ec6e52c4'}, 'scripts/cloud_cdr_v59_static_source_recovery.py': {'bytes': 14205, 'sha256': 'e1b99a76b9c20d760528f3bc35c2ab39d52786c7f0192aaba75888b7d683eaac'}, 'scripts/cloud_cdr_width_loaded.py': {'bytes': 29922, 'sha256': 'ebf92a9842280587a437de161425f49f6ce4a82c9d76a0ce2532075d0e309bf5'}, 'scripts/cloud_cdr_width_loaded_stage.py': {'bytes': 18242, 'sha256': '958256378226ec8d64453e72fb7d52b1d00df16d28c9fe4c656644a8aa6847c0'}, 'scripts/cloud_cdr_xor.py': {'bytes': 10437, 'sha256': '3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'}, 'scripts/cloud_chunked_results.py': {'bytes': 4885, 'sha256': 'fe414dcd92c233554a82a2151232bab8803e6ec7863df3872fbde009d3905816'}, 'scripts/cloud_contact_release.py': {'bytes': 3043, 'sha256': '6a1e50e9cb4e1fb18bc4ef19a821096952fc50b382c25b0d655e537e55e35f11'}, 'scripts/cloud_pll_pump_current.py': {'bytes': 14089, 'sha256': '0ec3faf3820264560f195cab1e7371b16a066eac2ffa59682145b4a089c9688f'}, 'scripts/cloud_tx_companion_replay.py': {'bytes': 15895, 'sha256': '5933ebfc9cb6fff9f86d312e9317fcd9581a138b9974e656ad304396e913f090'}, 'scripts/cloud_tx_data_driver.py': {'bytes': 14510, 'sha256': 'b85660408b95e79669335e128ba06ed5f07f96ac73f051cd9d5eada3b03c9912'}, 'scripts/cloud_tx_step_factorial.py': {'bytes': 23280, 'sha256': 'e44edf18492c901851396099f56c0af718423dc171b2a1c2112bcc0b83c05193'}, 'scripts/cloud_tx_stream.py': {'bytes': 19383, 'sha256': '2894eede2e5e087c23cadee9cec9dbdca359315a786cec0cabfe7f8da37449cb'}, 'scripts/cloud_vbic_tree32_backend.py': {'bytes': 14504, 'sha256': '472c0c14d1a55785c3d0e9823e2bac94a97216781c530fdb8e8562bd0b805639'}, 'scripts/cloud_verified_parts.py': {'bytes': 5017, 'sha256': '64b6655bfd6f8c348af62e9179268eafb84c9150cbba895989bcdfb2c6b5b795'}, 'scripts/compare_cloud_routed_endpoints.py': {'bytes': 24976, 'sha256': '15ead8483a372a713a4d68aa36e00a7ee05b5c9528c6ece4f5b4bd2d5c20ad42'}, 'scripts/diagnose_cdr_v59_annotation_native.py': {'bytes': 19164, 'sha256': '156fea2f555922d1b5f80637404d635118f2b008571226825ca79f5a42432c15'}, 'scripts/ensure_cloud_tested_source_release.py': {'bytes': 6349, 'sha256': 'ff213cb47a28b65207ef280be8ab4a0059622a3daa6a1e2c81f781c81ff2876e'}, 'scripts/expanded_load_targets.py': {'bytes': 7696, 'sha256': '1ef4d51a8be52f5621ed594a6fb4e0c5a24c078e54759dae227226dbe0cc6fd8'}, 'scripts/generate_cdr500_resistor_v59.py': {'bytes': 18410, 'sha256': '73d2eb18f3ceb4425668584f86b5e64a4c262af25c638114a4f18fcac36fb81d'}, 'scripts/materialize_cdr_v59_static_annotations.py': {'bytes': 12986, 'sha256': 'fb51f63f3e934747ba1fbc6af8a06a176b7d6e47e52794abaaa5108d2989d217'}, 'scripts/measured_hold_targets.py': {'bytes': 5108, 'sha256': '91138b2c0f590b151ed93f12aeabb17fa5406e1286754498ad14b694e423efdf'}, 'scripts/migrate_outputs_to_cloud.py': {'bytes': 12452, 'sha256': '52fa3ef7adc92b6e6071b304ccb1b07908f31ccde7dacf39a7258e07356fa512'}, 'scripts/read_opensta_phase_slacks.py': {'bytes': 3670, 'sha256': 'dfade1f0ac09bcbaa9a0c5f63869e0d2a545324003538a5dcb847d1dbc950273'}, 'scripts/refined_hold_targets.py': {'bytes': 6219, 'sha256': 'd3d985cc4b16add202815a745aebcd952723c296ce7e2d7a2b9eabc0eb72592a'}, 'scripts/refined_load_targets.py': {'bytes': 6693, 'sha256': 'd942cecb77d1b3394c53d5bc7f3e0d9e117843882d37c59fbb42909f24da5cb9'}, 'scripts/route_cloud_newer_postcts.py': {'bytes': 49174, 'sha256': '29997f34ca6e764c40a40b5203388993b890f6d838cbe2651d5ce5c018042b40'}, 'scripts/run_cloud_tx_layout_repair.py': {'bytes': 75555, 'sha256': '312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f'}, 'scripts/run_cloud_tx_mux4.py': {'bytes': 68790, 'sha256': 'bb7f5c5ef736dd54c5ed560424d97d248894f4aa6fa6119f1e95c5f5c3df4b52'}, 'scripts/run_cloud_tx_operating_point.py': {'bytes': 18463, 'sha256': 'e8c4f4b9c723217bdbb0be17f6c77cfd2e459928e07a7b6ff2c17dfcf1759a1e'}, 'scripts/wait_cloud_tested_source_release.py': {'bytes': 3571, 'sha256': '4c749e3f6f072c053f2dd5d45e9ad4f8cb2eca1e7c7b1cf480177f637fb04b73'}}
DATA={'docs/evidence/cloud-refined-load-hold-targets-20261016.json': {'module': 'scripts/refined_hold_targets.py', 'read_line': 31, 'hash_line': 32, 'bytes': 53179, 'sha256': '8eabcf9f3e0ace7ec6240474f1a5a0758c31f0350d559c5ef70a64b43572342b'}, 'docs/evidence/route146-all-reachable-branch-recipe-20261016.json': {'module': 'scripts/branch_hold_targets.py', 'read_line': 32, 'hash_line': 32, 'bytes': 110689, 'sha256': '12795513c5d9694eaae9daed4ca6b2c6209a42040c1ff8bdba9a23f249e8b31a'}, 'docs/evidence/cloud-measured-load-hold-conflicts-20261016.json': {'module': 'scripts/measured_hold_targets.py', 'read_line': 30, 'hash_line': 31, 'bytes': 382341, 'sha256': '55046b17b57dc82eeecbd26783ac62241bde725fce3eab21f9f271dd9a76565b'}}
WORKER_SHA="ebf92a9842280587a437de161425f49f6ce4a82c9d76a0ce2532075d0e309bf5"
STATUS="PASS_WIDTH_LOADED_ACTUAL_IMPORT_SOURCE_CONTROLS"
CHILD='import hashlib,importlib,json,os,pathlib,socket,subprocess,sys\nimport numpy\nassert numpy.__version__=="2.3.3"\nroot=pathlib.Path(sys.argv[1]).resolve()\nexpected=json.loads(sys.argv[2])\nmode=sys.argv[3]\nsys.path.insert(0,str(root/"scripts"))\nactive={"value":False}\nobserved=[]\nforbidden=[]\nDENY={"subprocess.Popen","os.system","os.exec","os.posix_spawn","os.spawn","os.fork","os.forkpty",\n "socket.connect","socket.bind","os.mkdir","os.remove","os.rmdir","os.rename","os.link","os.symlink",\n "os.truncate","os.chmod","os.chown"}\nWRITE_FLAGS=os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND\n\ndef audit(event,args):\n    if not active["value"]:return\n    denied=event in DENY\n    if event=="open":\n        path,mode,flags=args\n        denied=bool(type(flags)is int and flags&WRITE_FLAGS)\n        if type(mode)is str:denied=denied or any(c in mode for c in "wax+")\n    if denied:\n        forbidden.append(event)\n        raise RuntimeError("IMPORT_ONLY_FORBIDDEN:"+event)\n\nsys.addaudithook(audit)\nactive["value"]=True\ntry:\n    names=("cloud_cdr_width_loaded","cloud_cdr_width_loaded_stage",\n      "cdr_width_loaded_execution_admission","cdr_width_loaded_result")\n    modules={n:importlib.import_module(n)for n in names}\n    worker=modules[names[0]];stage=modules[names[1]];admission=modules[names[2]]\n    assert worker.current_inputs is admission and stage.a is admission\n    assert stage.result_gate is modules[names[3]]\n    assert stage.WORKER=="scripts/cloud_cdr_width_loaded.py"\n    assert worker.ROOT==stage.ROOT==admission.ROOT==root\n    for name,module in sorted(sys.modules.items()):\n        filename=getattr(module,"__file__",None)\n        if filename is None:continue\n        path=pathlib.Path(filename).resolve()\n        if not path.is_relative_to(root):continue\n        rel=path.relative_to(root).as_posix()\n        assert rel in expected,("Unexpected repository module",name,rel)\n        raw=path.read_bytes()\n        assert len(raw)==expected[rel]["bytes"] and hashlib.sha256(raw).hexdigest()==expected[rel]["sha256"]\n        observed.append({"module":name,"path":rel,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})\n    assert {row["path"]for row in observed}==set(expected)\n    assert len(observed)==len(expected)==52\n    if mode=="deny_write":\n        open(root/"forbidden-import-write.tmp","wb")\n    elif mode=="deny_process":\n        subprocess.Popen([sys.executable,"-c","raise SystemExit(99)"])\n    elif mode=="deny_network":\n        with socket.socket()as connection:connection.connect(("127.0.0.1",9))\n    else:assert mode=="ordinary"\nfinally:active["value"]=False\nassert not forbidden\nprint(json.dumps({"status":"PASS_EXACT_WIDTH_LOADED_ISOLATED_IMPORT",\n "entries":list(names),"repository_modules":observed,"modules":52,"numpy":numpy.__version__,\n "actual_worker_adapter_identity":True,"actual_stage_adapter_identity":True,\n "actual_stage_result_identity":True,"guard_forbidden_events":forbidden,\n "native_functions_called":False,"source_controls_only":True},sort_keys=True))\n'
INSTALLED={"numpy":"2.3.3"}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def initial_nodes(node):
    yield node
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    for child in ast.iter_child_nodes(node):yield from initial_nodes(child)

def closure(root,pins):
    a.require(EXPECTED[a.WORKER]["sha256"]==WORKER_SHA,"Wrong execution worker definition")
    modules={};edges=[];external=[];todo=list(ENTRIES)
    while todo:
        path=todo.pop()
        if path in modules:continue
        a.require(path in EXPECTED,"Undeclared initial repository dependency: "+path)
        raw=a.regular(root,path).read_bytes();spec=EXPECTED[path]
        a.require(len(raw)==spec["bytes"]and digest(raw)==spec["sha256"]
          and pins.get(path)==spec["sha256"],"Changed/unprotected initial module: "+path)
        modules[path]=dict(spec)
        for node in initial_nodes(ast.parse(raw)):
            if isinstance(node,ast.Import):names=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom):
                a.require(node.level==0 and node.module,"Relative initial import unsupported")
                names=[node.module]
            else:continue
            for name in names:
                first=name.split(".")[0];candidate="scripts/"+first+".py"
                if candidate in EXPECTED or(root/"scripts"/(first+".py")).exists()or(root/"scripts"/first).exists():
                    a.require("."not in name and candidate in EXPECTED,"Unexpected repository import: "+name)
                    a.require(first not in sys.stdlib_module_names and first not in INSTALLED,
                      "Repository dependency shadows standard/installed module")
                    edges.append({"from":path,"to":candidate,"line":node.lineno});todo.append(candidate)
                else:
                    a.require(first in sys.stdlib_module_names or name in INSTALLED,
                      "Unexpected initial external import: "+name)
                    if first not in sys.stdlib_module_names:external.append({"from":path,"name":name,"line":node.lineno})
    a.require(set(modules)==set(EXPECTED)and len(modules)==52 and len(edges)==115,
      "Exact four-entry import graph changed")
    data={}
    for path,spec in DATA.items():
        a.require(PurePosixPath(path).as_posix()==path and path.startswith("docs/evidence/")
          and ".."not in PurePosixPath(path).parts,"Initial data path changed")
        raw=a.regular(root,path).read_bytes()
        a.require(len(raw)==spec["bytes"]and digest(raw)==spec["sha256"]
          and pins.get(path)==spec["sha256"],"Changed/unprotected initial recipe: "+path)
        reader_raw=a.regular(root,spec["module"]).read_bytes()
        a.require(digest(reader_raw)==EXPECTED[spec["module"]]["sha256"],"Changed recipe reader")
        tree=ast.parse(reader_raw)
        reads=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="raw"for t in n.targets)]
        a.require(len(reads)==1 and reads[0].lineno==spec["read_line"],"Original recipe read line changed")
        expected=ast.parse("raw=(ROOT/"+repr(path)+").read_bytes()").body[0]
        a.require(ast.dump(reads[0],include_attributes=False)==ast.dump(expected,include_attributes=False),
          "Original recipe read expression changed")
        guards=[n for n in tree.body if isinstance(n,ast.Assert)and n.lineno==spec["hash_line"]]
        expected=ast.parse("assert hashlib.sha256(raw).hexdigest()==RECIPE_SHA").body[0]
        a.require(len(guards)==1 and ast.dump(guards[0],include_attributes=False)==ast.dump(expected,include_attributes=False),
          "Original recipe hash guard changed")
        recipes=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="RECIPE_SHA"for t in n.targets)]
        a.require(len(recipes)==1 and ast.literal_eval(recipes[0].value)==spec["sha256"],"Original recipe digest changed")
        data[path]=dict(spec)
    return {"modules":modules,"edges":edges,"data":data,"installed":INSTALLED,"external_imports":external}

def isolated_copy(root):
    paths=list(EXPECTED)+list(DATA)
    for name in paths:
        body=a.regular(ROOT,name).read_bytes()
        spec=EXPECTED.get(name,DATA.get(name))
        a.require(len(body)==spec["bytes"]and digest(body)==spec["sha256"],"Isolated source copy changed")
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        a.require(target.read_bytes()==body,"Isolated source copy differs")
    a.require({p.relative_to(root).as_posix()for p in root.rglob("*")if p.is_file()}==set(paths),
      "Isolated tree has undeclared files")
    return {name:{"bytes":len((root/name).read_bytes()),"sha256":digest((root/name).read_bytes())}for name in paths}

def run_import(root,mode="ordinary"):
    before={str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob("*")if p.is_file()}
    proc=subprocess.run([sys.executable,"-I","-B","-c",CHILD,str(root),json.dumps(EXPECTED,sort_keys=True),mode],
      cwd=root,capture_output=True,text=True,timeout=60)
    after={str(p.relative_to(root)):digest(p.read_bytes())for p in root.rglob("*")if p.is_file()}
    a.require(before==after,"Import created or modified isolated files")
    a.require(not list(root.glob("cloud-cdr-width-loaded-*"))and not(root/"hw").exists(),
      "Import created a native output directory")
    return {"returncode":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr,
      "exact_tree_unchanged":True,"mode":mode}

def controls():
    m=a.methods();a.require(m["source_controls_authorized"]is True,"Actual import source controls disabled")
    a.require(m["protected_sha256"].get(SELF)==a.sha(a.regular(ROOT,SELF))
      and m["protected_sha256"].get(REVIEW)==a.sha(a.regular(ROOT,REVIEW)),
      "Import checker/review not protected")
    audit=closure(ROOT,m["protected_sha256"])
    positive=[{"name":"actual_current_four_entry_closure","modules":len(audit["modules"]),
      "repository_edges":len(audit["edges"]),"data":len(audit["data"])}];refusal=[]
    # Each child sees exactly52 pinned modules+3 initial recipes, with no caller
    # PYTHONPATH/cwd fallback or bytecode writes. No numerical main is called.
    with tempfile.TemporaryDirectory(prefix="cdr-width-loaded-import-")as folder:
        root=Path(folder);copied=isolated_copy(root)
        a.require(closure(root,m["protected_sha256"])==audit,"Isolated closure differs")
        proof=run_import(root)
        a.require(proof["returncode"]==0 and proof["stderr"]=="","Actual isolated import failed: "+repr(proof))
        parsed=json.loads(proof["stdout"])
        a.require(parsed["status"]=="PASS_EXACT_WIDTH_LOADED_ISOLATED_IMPORT"
          and parsed["modules"]==52 and parsed["numpy"]=="2.3.3"
          and parsed["actual_worker_adapter_identity"]is True
          and parsed["actual_stage_adapter_identity"]is True
          and parsed["actual_stage_result_identity"]is True
          and parsed["native_functions_called"]is False
          and not parsed["guard_forbidden_events"],"Isolated import proof changed")
        a.require({r["path"]:{"bytes":r["bytes"],"sha256":r["sha256"]}for r in parsed["repository_modules"]}==EXPECTED,
          "Actual loaded module map differs")
        positive.append({"name":"actual_four_entry_isolated_import","proof":proof,"parsed":parsed})
        path=root/"scripts/cdr_width_loaded_execution_admission.py";raw=path.read_bytes();path.unlink()
        try:proof=run_import(root)
        finally:path.write_bytes(raw)
        a.require(proof["returncode"]==1 and proof["stdout"]==""
          and proof["stderr"].splitlines()[-1]=="ModuleNotFoundError: No module named 'cdr_width_loaded_execution_admission'",
          "Missing actual execution adapter was not refused: "+repr(proof))
        refusal.append({"name":"missing_actual_execution_adapter","proof":proof})
        selected="docs/evidence/cloud-refined-load-hold-targets-20261016.json"
        for kind in ("missing","tampered"):
            path=root/selected;raw=path.read_bytes()
            if kind=="missing":path.unlink()
            else:path.write_bytes(raw+b" ")
            try:proof=run_import(root)
            finally:path.write_bytes(raw)
            a.require(proof["returncode"]==1 and proof["stdout"]==""and proof["stderr"].startswith("Traceback (most recent call last):\n"),
              "Original data failure was not actual import failure: "+repr(proof))
            spec=DATA[selected]
            frames=re.findall(r'^  File "([^"]+)", line ([0-9]+), in ([^\n]+)$',proof["stderr"],re.MULTILINE)
            frame=(str(root/spec["module"]),str(spec["read_line"]if kind=="missing"else spec["hash_line"]),"<module>")
            a.require(frame in frames,"Original recipe reader frame missing: "+repr(proof))
            if kind=="missing":
                a.require(proof["stderr"].splitlines()[-1]=="FileNotFoundError: [Errno 2] No such file or directory: "+repr(str(root/selected)),
                  "Missing original recipe error changed")
            else:
                a.require(frames[-1]==frame and proof["stderr"].splitlines()[-1]=="AssertionError",
                  "Original recipe hash assertion did not reject changed bytes")
            refusal.append({"name":kind+"_original_recipe","proof":proof})
        for mode,event in (("deny_write","open"),("deny_process","subprocess.Popen"),("deny_network","socket.connect")):
            proof=run_import(root,mode)
            a.require(proof["returncode"]==1 and proof["stdout"]==""
              and proof["stderr"].splitlines()[-1]=="RuntimeError: IMPORT_ONLY_FORBIDDEN:"+event,
              "Import-only audit guard failed: "+repr(proof))
            refusal.append({"name":mode,"proof":proof,"operation_rejected_before_effect":True})
        a.require({str(p.relative_to(root)):{"bytes":p.stat().st_size,"sha256":digest(p.read_bytes())}
          for p in root.rglob("*")if p.is_file()}==copied,"Fault restoration changed isolated fixture")
    return {"status":STATUS,"positive":len(positive),"refusal":len(refusal),"positives":positive,
      "refusals":refusal,"closure":audit,"copied_files":55,"initial_modules":52,"initial_data":3,
      "worker_sha256":WORKER_SHA,"worker_execution_adapter_required":True,"native_executed":False,
      "numpy_version":"2.3.3","all_child_streams_complete":True,"source_controls_only":True,
      "native_functions_called":False,"native_acquisition_performed":False,"simulator_executed":False,
      "electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False,
      "audit_scope":"Behavioral no-process/no-network/no-write guard during imports; not a general Python security sandbox. Generic compile/exec events are allowed for normal authenticated module imports; os.exec is forbidden."}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    report={"status":"FAIL_WIDTH_LOADED_ACTUAL_IMPORT_SOURCE_CONTROLS","source_controls_only":True,"native_executed":False,
      "native_functions_called":False,"native_acquisition_performed":False,"simulator_executed":False,
      "electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False}
    primary=None
    try:
        ctx=a.context();report=controls()
        report["current_context"]={**ctx,"source_controls_only":True,"native_executed":False}
    except BaseException as error:primary=error;report.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        try:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
        except BaseException as error:
            if primary is None:primary=error
        try:print(raw.decode(),end="",flush=True)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary

if __name__=="__main__":main()
