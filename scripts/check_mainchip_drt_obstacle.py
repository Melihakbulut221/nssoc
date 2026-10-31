#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic contracts, never a native ODB result."""
import ast,copy,os,types,unittest
from pathlib import Path
from unittest.mock import patch
import mainchip_drt_obstacle_contract as k
import check_mainchip_drt_report_analysis as fixture_m
class Controls(unittest.TestCase):
    def fixture(self):
        f=fixture_m.Controls();p,x=f.owners()
        raw=f.report()+f.report()+f.report(("a","clock"),"Metal Spacing","Metal4")+f.report(("a","clock"),"Short","Metal3")
        rows=k.text.parse_report(raw);a=dict(status="COMPLETE_TEXTUAL_DRT_MANIFEST_CLASSIFICATION",iteration10=k.text.classify(rows,k.text.ownership(p,x)),**k.text.FLAGS)
        return f,p,x,raw,a
    def test_exact_decimal_grid_and_negative_values(self):
        f=fixture_m.Controls();row=k.text.parse_report(f.report(coords=("-0.0000","-2.0050","3.0100","4.0000")))[0]
        self.assertEqual(k.dbu_box(row,1000),[0,-2005,3010,4000])
        self.assertEqual(k.dbu_box(row,2000),[0,-4010,6020,8000])
    def test_off_grid_invalid_dbu_and_changed_layer_refused(self):
        f=fixture_m.Controls();row=k.text.parse_report(f.report(coords=("1.0001","2.0000","3.0000","4.0000")))[0]
        for dbu in(1000,True,0,-1,1000.0):
            with self.subTest(dbu=dbu),self.assertRaises(ValueError):k.dbu_box(row,dbu)
        row=k.text.parse_report(f.report())[0];row["layer"]="Metal3"
        with self.assertRaises(ValueError):k.dbu_box(row,1000)
    def test_closed_edge_point_and_positive_area_are_distinct(self):
        a=[0,0,10,10]
        expected=[([2,3,8,9],(True,True,6,6)),([10,2,12,8],(True,False,0,6)),([10,10,12,12],(True,False,0,0)),([11,2,12,8],(False,False,-1,6))]
        for b,want in expected:
            got=k.relation(a,b);self.assertEqual(tuple(got[n]for n in("closed_intersection","positive_area_intersection","x_overlap_dbu","y_overlap_dbu")),want)
        for b in([0,0,True,1],[2,0,1,1],[0,0,1],[0.0,0,1,1]):
            with self.assertRaises(ValueError):k.rectangle(b)
    def test_complete_scope_keeps_multiplicity_and_all_other_kinds(self):
        f,p,x,raw,a=self.fixture();s,o=k.scope(raw,p,x,a,1000,4,2)
        self.assertEqual([r["ordinal"]for r in s["markers"]],[0,1])
        self.assertEqual([r["ordinal"]for r in s["other_markers"]],[2,3])
        self.assertEqual(s["endpoint_names"],["a","b"])
        self.assertEqual([r["box"]for r in s["markers"]],[[1000,2000,3000,4000]]*2)
        self.assertEqual("".join(r["raw"]for r in sorted(s["markers"]+s["other_markers"],key=lambda r:r["ordinal"])).encode(),raw)
    def test_incomplete_or_reinterpreted_analysis_and_censuses_refused(self):
        f,p,x,raw,a=self.fixture()
        for total,selected in((3,2),(4,1),(4,3)):
            with self.assertRaises(ValueError):k.scope(raw,p,x,a,1000,total,selected)
        for field,value in(("physical_cause_proven",True),("status","PASS_PHYSICAL")):
            bad={**a,field:value}
            with self.assertRaises(ValueError):k.scope(raw,p,x,bad,1000,4,2)
        bad=copy.deepcopy(a);bad["iteration10"]["records"].pop()
        with self.assertRaises(ValueError):k.scope(raw,p,x,bad,1000,4,2)
    def test_two_distinct_selected_endpoints_required(self):
        f,p,x,raw,a=self.fixture()
        for nets in(("a",),("a","a"),("a","b","clock")):
            b=f.report(nets);a["iteration10"]=k.text.classify(k.text.parse_report(b),k.text.ownership(p,x))
            with self.assertRaises(ValueError):k.scope(b,p,x,a,1000,1,1)
    def test_witness_requires_exact_owner_and_layer_or_explicit_pin_projection(self):
        escaped=r"a\[0\]";m=dict(nets=[escaped,"b"],box=[0,0,10,10],layer="Metal2")
        shape=dict(owner=escaped,box=[1,2,4,6],kind="wire",layer="Metal2")
        r=k.witness(m,shape);self.assertEqual(r["layer_relation"],"same_layer");self.assertIn("not_root_cause",r["observation"])
        with self.assertRaises(ValueError):k.witness(m,{**shape,"owner":"a[0]"})
        off={**shape,"layer":"Metal1"}
        self.assertIsNone(k.witness(m,off));self.assertEqual(k.witness(m,off,True)["layer_relation"],"xy_projection_only_different_layer")
        self.assertIsNone(k.witness(m,{**shape,"box":[11,11,12,12]},True))
    def test_actual_candidate_census_and_added_endpoint_inventory(self):
        nets=["net"+str(i)for i in range(143820)]
        added=["NSSOC_BULK_NEW_"+str(i)for i in range(1351)]
        inst=["base"+str(i)for i in range(153129)]+added
        attachments={n:nets[0]for n in added}
        self.assertEqual(k.census(nets,inst,added,attachments),dict(net_count=143820,instance_count=154480,added_count=1351))
        for nn,ii,aa,at in((nets[:-1],inst,added,attachments),(nets,inst[:-1],added,attachments),
          (nets,inst[:-1]+[inst[0]],added,attachments),(nets,inst,added[:-1],attachments),
          (nets,inst,added,{**attachments,added[0]:"unknown"})):
            with self.assertRaises(ValueError):k.census(nn,ii,aa,at)
    def test_actual_context_and_native_authority_refusal(self):
        e=dict(GITHUB_ACTIONS="true",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",
          GITHUB_REF="refs/heads/codex/mainchip-drt-obstacle-progress-v2",GITHUB_SHA="a"*40,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123")
        self.assertEqual(k.context(e,"a"*40),dict(source="a"*40,run=123,attempt=1))
        for key,val in(("GITHUB_ACTIONS","false"),("GITHUB_REPOSITORY","other/repo"),("GITHUB_EVENT_NAME","push"),
          ("GITHUB_REF","refs/heads/main"),("GITHUB_SHA","b"*40),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_RUN_ID","0")):
            with self.assertRaises(ValueError):k.context({**e,key:val},"a"*40)
        with patch.object(k,"source_gate",return_value=dict(native_readonly_authorized=False,native_routing_authorized=False)):
            with self.assertRaisesRegex(ValueError,"disabled"):k.native_authorization()
    def pin_function(self):
        path=Path(__file__).with_name("mainchip_drt_obstacle_native.py");tree=ast.parse(path.read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="all_pin_geometry"];self.assertEqual(len(nodes),1)
        geom=types.SimpleNamespace(box=lambda r:list(r),placed_box=lambda transform,b:transform[b.key])
        scope=dict(q=k.q,geom=geom);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
        return scope["all_pin_geometry"]
    def pin_fixture(self):
        ns=types.SimpleNamespace
        layer=lambda name:ns(getName=lambda:name)
        boxes=[ns(key="left",isVia=lambda:False,getTechLayer=lambda:layer("Metal1")),ns(key="right",isVia=lambda:False,getTechLayer=lambda:layer("Metal2"))]
        transformed={"left":[-30,40,-10,60],"right":[-70,80,-50,100]}
        mpins=[ns(getGeometry=lambda:[boxes[0]]),ns(getGeometry=lambda:[boxes[1],boxes[1]])]
        actual=[(layer("Metal1"),transformed["left"]),(layer("Metal2"),transformed["right"]),(layer("Metal2"),transformed["right"])]
        term=ns(getGeometries=lambda:actual,getInst=lambda:ns(getTransform=lambda:transformed),getMTerm=lambda:ns(getMPins=lambda:mpins))
        return term,actual,boxes
    def test_all_mpin_shapes_transform_layers_and_multiplicity_checked(self):
        fn=self.pin_function();term,actual,boxes=self.pin_fixture()
        self.assertEqual(fn(term),[("Metal1",[-30,40,-10,60]),("Metal2",[-70,80,-50,100]),("Metal2",[-70,80,-50,100])])
        actual.reverse();self.assertEqual(len(fn(term)),3)
        actual.pop()
        with self.assertRaises(ValueError):fn(term)
    def test_changed_pin_layer_transform_and_unqualified_via_refused(self):
        fn=self.pin_function()
        for mode in("layer","transform","via"):
            term,actual,boxes=self.pin_fixture()
            if mode=="layer":actual[0]=(types.SimpleNamespace(getName=lambda:"Metal3"),actual[0][1])
            elif mode=="transform":actual[0]=(actual[0][0],[-29,40,-10,60])
            else:boxes[0].isVia=lambda:True
            with self.subTest(mode=mode),self.assertRaises(ValueError):fn(term)

    def test_progress_batch_census_and_exact_endpoint_stages(self):
        import mainchip_drt_obstacle_progress as p
        rows=[];clock=[10.0];trace=p.Progress(rows.append,lambda:clock[0])
        trace.begin("endpoint-iterm-pins","VGND")
        for i in range(2049):trace.tick()
        clock[0]=11.0;trace.end();trace.begin("endpoint-special-wires","VGND");trace.end()
        self.assertEqual([r["completed_items"]for r in rows],[0,1024,2048,2049,0,0])
        self.assertEqual([r["sequence"]for r in rows],list(range(6)))
        self.assertEqual([r["event"]for r in rows],["begin","checkpoint","checkpoint","complete","begin","complete"])
        self.assertTrue(all(r["endpoint"]=="VGND"and all(r[n]is False for n in k.FLAGS)for r in rows))
        self.assertEqual(rows[3]["elapsed_seconds"],1.0)
    def test_progress_refuses_overlap_bad_clock_and_preserves_sink_failure(self):
        import mainchip_drt_obstacle_progress as p
        rows=[];clock=[10.0];trace=p.Progress(rows.append,lambda:clock[0])
        with self.assertRaises(ValueError):trace.tick()
        with self.assertRaises(ValueError):trace.end()
        with self.assertRaises(ValueError):trace.begin("unqualified-stage")
        trace.begin("endpoint-identity","VGND")
        with self.assertRaises(ValueError):trace.begin("endpoint-encoding","VGND")
        clock[0]=9.0
        with self.assertRaises(ValueError):trace.end()
        primary=OSError("explicit synthetic telemetry sink failure")
        with self.assertRaises(OSError)as caught:p.Progress(lambda row:(_ for _ in()).throw(primary),lambda:0).begin("database-load")
        self.assertIs(caught.exception,primary)
    def test_progress_append_journal_and_atomic_latest_failure_are_visible(self):
        import json,tempfile
        import mainchip_drt_obstacle_progress as p
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);trace=p.Progress(p.emitter(root),lambda:0)
            trace.begin("endpoint-identity","VGND");trace.end()
            rows=[json.loads(line)for line in(root/"substage-events.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows),2);self.assertEqual(json.loads((root/"substage-progress.json").read_bytes()),rows[-1])
            primary=OSError("synthetic latest rename failure")
            with patch.object(Path,"replace",side_effect=primary):
                with self.assertRaises(OSError)as caught:trace.begin("endpoint-encoding","VGND")
            self.assertIs(caught.exception,primary)
            self.assertEqual(len((root/"substage-events.jsonl").read_text().splitlines()),3)
            self.assertEqual(json.loads((root/"substage-progress.json.partial").read_bytes())["stage"],"endpoint-encoding")
            self.assertEqual(json.loads((root/"substage-progress.json").read_bytes()),rows[-1])
    def test_complete_native_geometry_ast_unchanged_except_telemetry(self):
        import hashlib
        baseline=Path(__file__).resolve().parents[1]/"docs/evidence/mainchip-drt-obstacle-65e620-native-source.py"
        raw=baseline.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),"c7204c678d84045cf03040b5d7a857411a81ac5720abd2e5f481e46f4208b23f")
        old=ast.parse(raw);new=ast.parse(Path(__file__).with_name("mainchip_drt_obstacle_native.py").read_text())
        def function(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
        class RemoveTelemetry(ast.NodeTransformer):
            def visit_Expr(self,node):
                call=node.value
                if isinstance(call,ast.Call)and isinstance(call.func,ast.Attribute)and isinstance(call.func.value,ast.Name)and call.func.value.id=="trace":
                    if call.func.attr not in("begin","tick","end"):raise AssertionError("unqualified trace operation")
                    return None
                return self.generic_visit(node)
        prior=function(old,"native_scope");observed=copy.deepcopy(function(new,"native_scope"))
        self.assertEqual(observed.args.args[-1].arg,"trace");observed.args.args.pop()
        observed=RemoveTelemetry().visit(observed)
        self.assertEqual(ast.dump(observed,include_attributes=False),ast.dump(prior,include_attributes=False))
        for name in("record","all_pin_geometry"):
            self.assertEqual(ast.dump(function(new,name),include_attributes=False),ast.dump(function(old,name),include_attributes=False))
    def test_periodic_stack_diagnostics_are_nonterminating_and_cancelled(self):
        import mainchip_drt_obstacle_progress as p
        with patch.object(p.faulthandler,"dump_traceback_later")as start,patch.object(p.faulthandler,"cancel_dump_traceback_later")as stop:
            p.start_stacks();p.stop_stacks()
            start.assert_called_once_with(60,repeat=True,file=p.sys.stderr,exit=False);stop.assert_called_once_with()
        tree=ast.parse(Path(__file__).with_name("mainchip_drt_obstacle_native.py").read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="main")
        outer=next(n for n in main.body if isinstance(n,ast.Try))
        self.assertTrue(any(isinstance(n,ast.Attribute)and isinstance(n.value,ast.Name)and n.value.id=="telemetry"and n.attr=="stop_stacks"for stmt in outer.finalbody for n in ast.walk(stmt)))


    def test_exact_readonly_3600_budget_and_unchanged_resource_refusals(self):
        import mainchip_drt_obstacle_budget as b
        import mainchip_exit_checked_command_evidence as original
        check=b.validator(original)
        self.assertIs(check.__code__,original.validate.__code__)
        self.assertEqual(original.SECONDS,(1200,14400));self.assertEqual(check.__globals__["SECONDS"],(3600,))
        self.assertEqual((b.OBSERVATION_SECONDS,b.CONTAINER_SECONDS),(3600,3900))
        row=dict(returncode=0,supervision_failure=None,pid=5,minimum_available_kib=2097152,
          maximum_group_rss_kib=10485760,elapsed_seconds=2.0,requested_timeout_seconds=3600,
          process_group_cleanup=dict(signals=[],remaining_live=[],remaining_nonrunning=[]),
          last_memory_sentinel_sample=dict(available_kib=2097152,group_rss_kib=10485760),
          memory_read_error=None,memory_terminal_resolution=None)
        self.assertEqual(check(row,3600)["status"],"PASS_EXIT_CHECKED_COMMAND_EVIDENCE")
        for seconds in(1200,14400,3599,3601,3600.0,True):
            with self.subTest(seconds=seconds),self.assertRaises(ValueError):check(row,seconds)
        for key,val in(("minimum_available_kib",2097151),("maximum_group_rss_kib",10485761),("requested_timeout_seconds",1200)):
            with self.assertRaises(ValueError):check({**row,key:val},3600)
        for key,val in(("available_kib",2097151),("group_rss_kib",10485761)):
            bad=copy.deepcopy(row);bad["last_memory_sentinel_sample"][key]=val
            with self.assertRaises(ValueError):check(bad,3600)
    def test_budget_runner_exact_source_and_synthetic_command_pipeline(self):
        import hashlib,json,tempfile
        import mainchip_drt_obstacle_budget as b
        import mainchip_exit_checked_command_evidence as evidence
        path=Path(__file__).with_name("mainchip_bulk_postdrt_antenna_inner.py")
        tree=ast.parse(path.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="supervised_run")
        original=types.ModuleType("explicit_synthetic_original_namespace");original.__file__=str(path)
        original.WORK=Path("/explicit-synthetic-unused-default")
        original.command_evidence=evidence;original.p=types.SimpleNamespace(require=k.q.require,pin=lambda raw:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        progress=[];original.write=lambda name,report:progress.append((name,copy.deepcopy(report)))
        original.c=types.SimpleNamespace(require=k.q.require,decode=k.q.decode,secure_file=lambda root,name:root/name,
          error_record=lambda action,exc:dict(action=action,error=repr(exc)),
          attempt=lambda report,label,fn:fn())
        streamed=[];original.stream_contract=types.SimpleNamespace(terminal_stream=lambda row,root,label:streamed.append((row["argv"],label)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),"exec"),original.__dict__)
        adapted=b.runner(original)
        self.assertEqual(b.source(original.supervised_run).count(b.OLD_GUARD),1)
        with patch.object(b,"source",return_value=b.source(original.supervised_run)+"# altered source\n"):
            with self.assertRaises(ValueError):b.runner(original)
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);calls=[];label="obstacle-endpoint-observation";argv=["explicit-synthetic-no-process"]
            def supervised(args,name,seconds,cwd):
                calls.append((args,name,seconds,cwd))
                row=dict(argv=args,returncode=0,supervision_failure=None,pid=5,minimum_available_kib=2097152,
                  maximum_group_rss_kib=10485760,elapsed_seconds=2.0,
                  process_group_cleanup=dict(signals=[],remaining_live=[],remaining_nonrunning=[]),
                  last_memory_sentinel_sample=dict(available_kib=2097152,group_rss_kib=10485760),
                  memory_read_error=None,memory_terminal_resolution=None)
                (root/(name+".command.json")).write_bytes(k.q.encode(row))
            sup=types.SimpleNamespace(TRACE=root,supervised=supervised)
            report=dict(commands=[],terminal_errors=[])
            adapted(report,label,argv,3600,sup,cwd=root)
            self.assertEqual(calls,[(argv,label,3600,root)])
            self.assertEqual(streamed,[(argv,label)]);self.assertEqual(len(progress),1)
            self.assertEqual(report["commands"][0]["requested_timeout_seconds"],3600)
            self.assertEqual(report["commands"][0]["command_evidence"]["status"],"PASS_EXIT_CHECKED_COMMAND_EVIDENCE")
            for value in(1200,14400,3600.0,True):
                with self.assertRaises(ValueError):adapted(dict(commands=[],terminal_errors=[]),label,argv,value,sup,cwd=root)
            self.assertEqual(len(calls),1)

if __name__=="__main__":
    if os.environ.get("GITHUB_ACTIONS")!="true":raise RuntimeError("Hosted controls only")
    unittest.main(verbosity=2)
