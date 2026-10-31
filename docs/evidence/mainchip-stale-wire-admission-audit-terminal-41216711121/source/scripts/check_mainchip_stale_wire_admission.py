"""Hosted source/refusal tests only; all native records here are synthetic."""
import ast,contextlib,copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
import mainchip_stale_wire_admission as a
import check_mainchip_stale_wire_admission_inherited as context
from mainchip_stale_wire_admission import p

def fixture():
    labels=["bulk-postdrt-version","bulk-postdrt-ldd"]+[
      "bulk-postdrt-route-continuation-"+x if x in a.original.PREPARATION else "bulk-postdrt-"+x
      for x in a.original.PHASES]
    labels.insert(labels.index(a.ROUTE),a.CLEAR)
    commands=[dict(label=label,returncode=0,argv=a.ARGV if label==a.CLEAR else (["/work/engine/openroad","-no_init","-exit",str(a.WORK/"route.tcl")]if label==a.ROUTE else ["synthetic"]),
      requested_timeout_seconds=14400 if label==a.ROUTE else 1200)for label in labels]
    result=dict(status="COMPLETE_SAVED_DIODE_ROUTING_QUALIFICATION",bounded_cycle_qualified=True,
      current_repair_antennas_calls=0,current_reconstruction_calls=0,current_route_calls=1,
      direct_diode_pg_contact_passed=True,candidate=dict(bytes=7,sha256="a"*64),**p.FLAGS)
    return dict(status="COMPLETE_SAVED_DIODE_ROUTING_ENGINE",terminal_errors=[],native_complete=True,
      route_cycle=dict(complete=True,terminal_errors=[],phases={x:"complete"for x in a.original.PHASES}),
      commands=commands,saved_diode_routing_result=result,
      stale_wire_clear=dict(phase="stale-wire-clear",complete=True,error=None,terminal_errors=[],**p.FLAGS),**p.FLAGS)

class Controls(unittest.TestCase):
    def test_exact_bytes_are_typed_and_nonpermissive(self):
        a.exact_bytes(b"preserved",b"preserved","same exact bytes")
        for first,second in ((b"preserved",b"changed"),("preserved",b"preserved"),(b"preserved","preserved"),(bytearray(b"same"),b"same")):
            with self.subTest(first=type(first),second=type(second)),self.assertRaises(AssertionError):
                a.exact_bytes(first,second,"not exact bytes")
    def test_source_gate(self):
        self.assertFalse(a.source_gate()["current_native_result_accepted"])
    def test_complete_real_environment_unchanged(self):
        before=dict(os.environ)
        actual=context.source_context(os.environ)
        self.assertEqual(actual["source"],os.environ["GITHUB_SHA"])
        self.assertEqual(os.environ["GITHUB_REF"],"refs/heads/"+context.BRANCH)
        with self.assertRaises(AssertionError):context.original_host.context(os.environ)
        historical=dict(os.environ,GITHUB_REF="refs/heads/codex/mainchip-net459-diode-prune")
        with self.assertRaises(AssertionError):context.source_context(historical)
        self.assertEqual(dict(os.environ),before)
    def test_only_inherited_context_global_changes(self):
        self.assertIs(context.source_context.__code__,context.original_host.context.__code__)
        self.assertIs(context.source_main.__code__,context.original_controls.main.__code__)
        self.assertIs(context.source_main.__globals__["controls"],context.original_controls.controls)
        for key,value in vars(context.original_host).items():
            if key!="context":self.assertIs(getattr(context.source_host,key),value,key)
    def test_original_rejects_added_phase_new_gate_preserves_record(self):
        inner=fixture();before=copy.deepcopy(inner)
        with self.assertRaises(AssertionError):a.original.accept_native_result(inner)
        self.assertTrue(a.validate_native_result(inner)["saved_diode_routing_complete"])
        self.assertEqual(inner,before)
    def test_whole_validator_ast_only_one_statement(self):
        raw=(a.ROOT/a.PLAN).read_bytes()
        old=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=="accept_native_result")
        derived=a.validator_tree(raw).body[0]
        inserts=[i for i,n in enumerate(derived.body)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)
          and isinstance(n.value.func,ast.Attribute)and n.value.func.attr=="insert"]
        self.assertEqual(len(inserts),1);derived.body.pop(inserts[0])
        self.assertEqual(ast.dump(old),ast.dump(derived))
        with self.assertRaises(AssertionError):a.validator_tree(raw+b"\n")
    def test_clear_missing_duplicate_order_name_extra_refused(self):
        for mode in ("missing","duplicate","order","name","extra"):
            inner=fixture();rows=inner["commands"];i=next(i for i,r in enumerate(rows)if r["label"]==a.CLEAR)
            if mode=="missing":rows.pop(i)
            elif mode=="duplicate":rows.insert(i,copy.deepcopy(rows[i]))
            elif mode=="order":rows[i],rows[i+1]=rows[i+1],rows[i]
            elif mode=="name":rows[i]["label"]="other-clear"
            else:rows.append(dict(label="extra",returncode=0))
            with self.subTest(mode=mode),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_clear_and_route_invocation_refused(self):
        for label,key,value in ((a.CLEAR,"argv",["other"]), (a.CLEAR,"requested_timeout_seconds",1201),
          (a.CLEAR,"requested_timeout_seconds",True),(a.ROUTE,"requested_timeout_seconds",14401),
          (a.ROUTE,"argv",["unexpected-router"])):
            inner=fixture();row=next(r for r in inner["commands"]if r["label"]==label);row[key]=value
            with self.subTest(label=label,key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_clear_terminal_failure_refused(self):
        for key,value in (("phase","other"),("complete",False),("complete",1),("error","failure"),("terminal_errors",["error"])):
            inner=fixture();inner["stale_wire_clear"][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_any_command_failure_refused(self):
        for i in range(17):
            inner=fixture();inner["commands"][i]["returncode"]=7
            with self.subTest(command=i),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_all_original_phases_required(self):
        for phase in a.original.PHASES:
            inner=fixture();inner["route_cycle"]["phases"][phase]="failed"
            with self.subTest(phase=phase),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_command_missing_or_reordered_refused(self):
        for mode in ("missing","reordered","second_route"):
            inner=fixture()
            if mode=="missing":inner["commands"].pop(0)
            elif mode=="reordered":inner["commands"][0],inner["commands"][1]=inner["commands"][1],inner["commands"][0]
            else:inner["commands"].append(copy.deepcopy(next(r for r in inner["commands"]if r["label"]==a.ROUTE)))
            with self.subTest(mode=mode),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_physical_verdict_refusals(self):
        for key,value in (("status","FAIL"),("bounded_cycle_qualified",False),("current_repair_antennas_calls",1),
           ("current_reconstruction_calls",1),("current_route_calls",2),("direct_diode_pg_contact_passed",False)):
            inner=fixture();inner["saved_diode_routing_result"][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_candidate_pin_refusals(self):
        for key,value in (("bytes",0),("bytes",True),("sha256","A"*64),("sha256","0")):
            inner=fixture();inner["saved_diode_routing_result"]["candidate"][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_engine_or_cleanup_failure_refused(self):
        for key,value in (("status","FAIL"),("terminal_errors",["failed"]),("native_complete",False)):
            inner=fixture();inner[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
        for key,value in (("complete",False),("terminal_errors",["error"])):
            inner=fixture();inner["route_cycle"][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_all_acceptance_flags_refused(self):
        for where in ("inner","saved_diode_routing_result","stale_wire_clear"):
            for key in p.FLAGS:
                for value in (True,0,1):
                    inner=fixture();target=inner if where=="inner"else inner[where];target[key]=value
                    with self.subTest(where=where,key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)


def write_fixture(root,name,value):
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(value if type(value)is bytes else p.encode(value))

def synthetic_capsule(root):
    """Exercise actual audit I/O with full-size synthetic censuses and no CAD."""
    inner=fixture()
    for ordinal,row in enumerate(inner["commands"][2:]):
        label=row["label"];seconds=row["requested_timeout_seconds"]
        stdout=("synthetic stdout "+label+"\n").encode();stderr=b""
        record=dict(label=label,argv=row["argv"],requested_timeout_seconds=seconds,
          returncode=0,supervision_failure=None,pid=1000+ordinal,elapsed_seconds=.125,
          minimum_available_kib=2097152,maximum_group_rss_kib=10485760,
          process_group_cleanup=dict(signals=[],remaining_live=[],remaining_nonrunning=[]),
          last_memory_sentinel_sample=dict(available_kib=3145728,group_rss_kib=1024),
          memory_read_error=None,memory_terminal_resolution=None,
          stdout_bytes=len(stdout),stdout_sha256=p.pin(stdout)["sha256"],
          stderr_bytes=len(stderr),stderr_sha256=p.pin(stderr)["sha256"])
        raw=p.encode(record)
        write_fixture(root,"bulk-postdrt-supervision/"+label+".command.json",raw)
        write_fixture(root,"bulk-postdrt-supervision/"+label+".stdout",stdout)
        write_fixture(root,"bulk-postdrt-supervision/"+label+".stderr",stderr)
        row.update(command_record_pin=p.pin(raw),supervision_record=record,
          command_evidence=a.command.validate(record,seconds))
    work="work/bulk-postdrt-antenna/";data="bulk-postdrt-antenna/"
    for name in ("fixed.odb","stale-wire-cleared.odb","final-measured.odb"):
        write_fixture(root,work+name,("SYNTHETIC SOURCE FIXTURE ONLY; NOT AN ODB: "+name+"\n").encode())
    names=["net_%06d"%i for i in range(143820)]
    mutable=names[:608];protected=names[608:608+1691]
    attachments={"diode_%04d"%i:mutable[i%608]for i in range(1351)}
    admission=dict(mutable_nets=mutable,attachments=attachments,protected_nets=protected)
    oldrow=dict(identity=dict(sigtype="SIGNAL",fixture_only=True),
      encoded=dict(wire_present=True,metadata="ROUTED",paths=["ROUTED"]),
      wire=dict(opcode_count=2,pin=p.pin(p.encode([[1,2],[3,4]]))))
    instrow=dict(master=["synthetic","non_native_cell"],fixture_only=True)
    instances={name:instrow for name in attachments}
    instances.update({"instance_%06d"%i:instrow for i in range(154480-len(instances))})
    before=dict(nets={name:oldrow for name in names},instances=instances,
      masters={"synthetic/non_native_cell":{"fixture_only":True}},
      protected=protected,block=dict(name="synthetic",dbu=1000,rows=[]),
      immutable=dict(fixture_only=True),diode_template=instrow,
      clock_record_pins={name:p.pin(name.encode())for name in protected},
      def_pin=p.pin(b"synthetic before DEF"))
    after=dict(before,nets=dict(before["nets"]),def_pin=p.pin(b"synthetic after DEF"))
    for name in mutable:
        changed=copy.deepcopy(oldrow)
        changed["encoded"].update(wire_present=False,paths=[])
        changed["wire"]=dict(opcode_count=0,pin=p.pin(p.encode(None)))
        after["nets"][name]=changed
    # Independent expected projection; the function under test is not used to construct it.
    delta=dict(complete=True,cleared_nets=sorted(mutable),all_nonmutable_exact=True,
      all_instances_and_guides_checked_separately=True,**p.FLAGS)
    before_tcl=("source {synthetic-source-only-env}\nread_db {"+str(a.WORK/"fixed.odb")+
      "}\ndetailed_route {*}$drt_args\nwrite_db {synthetic-output.odb}\n").encode()
    after_tcl=before_tcl.replace(b"/fixed.odb}",b"/stale-wire-cleared.odb}")
    mutation=dict(complete=True,all_guides_unchanged=True,removed=sorted(mutable),
      input=a.pin(root/(work+"fixed.odb")),candidate=a.pin(root/(work+"stale-wire-cleared.odb")),
      delta=delta,route_before=p.pin(before_tcl),route_after=p.pin(after_tcl),**p.FLAGS)
    inner["saved_diode_routing_result"]["candidate"]=a.pin(root/(work+"final-measured.odb"))
    for name,value in (
      ("insertion-plan.json",admission),("fixed-snapshot.json",before),
      ("stale-wire-cleared-snapshot.json",after),("stale-wire-mutation.json",mutation),
      ("stale-wire-clear-terminal.json",inner["stale_wire_clear"]),
      ("stale-wire-original-guides.json",{name:[]for name in names}),
      ("route-before-stale-wire-clear.tcl",before_tcl),
      ("route-after-stale-wire-clear.tcl",after_tcl),
      ("saved-diode-routing-result.json",inner["saved_diode_routing_result"])):
        write_fixture(root,data+name,value)
    write_fixture(root,"bulk-postdrt-inner-result.json",inner)
    return dict(synthetic_only=True,native_bytes_generated=False,tests_mock_no_audit_functions=True,
      commands=17,supervised_commands=15,mutable_nets=608,attachments=1351,
      protected_nets=1691,instances=154480,nets=143820,
      fixture_files={str(path.relative_to(root)):a.pin(path)for path in sorted(root.rglob("*"))if path.is_file()})

@contextlib.contextmanager
def changed_fixture(root,name,change):
    path=root/name;raw=path.read_bytes()
    try:
        altered=change(json.loads(raw)) if callable(change) else change
        path.write_bytes(altered if type(altered)is bytes else p.encode(altered))
        yield
    finally:path.write_bytes(raw)

class CapsuleControls(unittest.TestCase):
    evidence={}
    @classmethod
    def setUpClass(cls):
        context.source_context(os.environ)
        cls.owned=tempfile.TemporaryDirectory(prefix="nssoc-synthetic-admission-")
        cls.addClassCleanup(cls.owned.cleanup)
        cls.root=Path(cls.owned.name);cls.evidence=synthetic_capsule(cls.root)
    def audit(self):
        return a.audit(self.root)
    def test_capsule_complete_audit_reads_real_files_without_mutation(self):
        before=self.evidence["fixture_files"]
        result=self.audit()
        self.assertEqual(result["status"],"PASS_SOURCE_BOUND_STALE_WIRE_ROUTING_READBACK")
        self.assertEqual(result["command_count"],17);self.assertEqual(result["clear_nets"],608)
        self.assertTrue(result["native_result"]["saved_diode_routing_complete"])
        self.assertTrue(all(result[k]is False for k in p.FLAGS))
        after={str(path.relative_to(self.root)):a.pin(path)for path in sorted(self.root.rglob("*"))if path.is_file()}
        self.assertEqual(after,before)
        type(self).evidence["complete_audit_nonmutation_passed"]=True
    def test_capsule_missing_command_record_is_refused(self):
        path=self.root/("bulk-postdrt-supervision/"+a.CLEAR+".command.json")
        raw=path.read_bytes();path.unlink()
        try:
            with self.assertRaisesRegex(AssertionError,"required regular member"):self.audit()
        finally:path.write_bytes(raw)
    def test_capsule_stream_byte_drift_is_refused(self):
        for stream in ("stdout","stderr"):
            name="bulk-postdrt-supervision/"+a.CLEAR+"."+stream
            raw=(self.root/name).read_bytes()
            changed=(bytes([raw[0]^1])+raw[1:])if raw else b"x"
            with self.subTest(stream=stream),changed_fixture(self.root,name,changed):
                with self.assertRaises(AssertionError):self.audit()
    def test_capsule_archived_command_pin_drift_is_refused(self):
        name="bulk-postdrt-supervision/"+a.CLEAR+".command.json"
        with changed_fixture(self.root,name,lambda r:dict(r,elapsed_seconds=.25)):
            with self.assertRaisesRegex(AssertionError,"actual command record pin"):self.audit()
    def test_capsule_embedded_command_drift_is_refused(self):
        def change(inner):
            row=next(r for r in inner["commands"]if r["label"]==a.CLEAR)
            row["supervision_record"]["elapsed_seconds"]=.25
            return inner
        with changed_fixture(self.root,"bulk-postdrt-inner-result.json",change):
            with self.assertRaisesRegex(AssertionError,"embedded and archived command equality"):self.audit()
    def test_capsule_coherent_failed_supervision_is_refused(self):
        member="bulk-postdrt-supervision/"+a.CLEAR+".command.json"
        record=json.loads((self.root/member).read_bytes());record["supervision_failure"]="synthetic failure"
        raw=p.encode(record)
        def change(inner):
            row=next(r for r in inner["commands"]if r["label"]==a.CLEAR)
            row.update(supervision_record=record,command_record_pin=p.pin(raw))
            return inner
        with changed_fixture(self.root,member,raw),changed_fixture(self.root,"bulk-postdrt-inner-result.json",change):
            with self.assertRaisesRegex(ValueError,"successful original command"):self.audit()
    def test_capsule_clear_terminal_drift_is_refused(self):
        with changed_fixture(self.root,"bulk-postdrt-antenna/stale-wire-clear-terminal.json",
          lambda r:dict(r,error="synthetic drift")):
            with self.assertRaisesRegex(AssertionError,"actual terminal bytes"):self.audit()
    def test_capsule_owned_removal_census_drift_is_refused(self):
        def change(r):r["removed"]=r["removed"][:-1];return r
        with changed_fixture(self.root,"bulk-postdrt-antenna/stale-wire-mutation.json",change):
            with self.assertRaisesRegex(AssertionError,"exact ordered608wire removal"):self.audit()
    def test_capsule_unowned_snapshot_wire_drift_is_refused(self):
        def change(r):
            r["nets"]["net_143819"]["wire"]["opcode_count"]=3
            return r
        with changed_fixture(self.root,"bulk-postdrt-antenna/stale-wire-cleared-snapshot.json",change):
            with self.assertRaisesRegex(AssertionError,"unowned wire or net changed: net_143819"):self.audit()
    def test_capsule_coherent_tcl_pin_still_requires_only_input_substitution(self):
        name="bulk-postdrt-antenna/route-after-stale-wire-clear.tcl"
        changed=(self.root/name).read_bytes()+b"puts unexpected-extra-command\n"
        with changed_fixture(self.root,name,changed),changed_fixture(self.root,
          "bulk-postdrt-antenna/stale-wire-mutation.json",lambda r:dict(r,route_after=p.pin(changed))):
            with self.assertRaisesRegex(AssertionError,"only approved route input substitution"):self.audit()
    def test_capsule_odb_byte_pins_are_refused(self):
        for name,reason in (("fixed.odb","unchanged fixed input"),
          ("stale-wire-cleared.odb","cleared ODB"),("final-measured.odb","actual final candidate")):
            with self.subTest(name=name),changed_fixture(self.root,"work/bulk-postdrt-antenna/"+name,b"changed synthetic bytes"):
                with self.assertRaisesRegex(AssertionError,reason):self.audit()
    def test_capsule_separate_native_verdict_drift_is_refused(self):
        with changed_fixture(self.root,"bulk-postdrt-antenna/saved-diode-routing-result.json",
          lambda r:dict(r,bounded_cycle_qualified=False)):
            with self.assertRaisesRegex(AssertionError,"actual native physical verdict"):self.audit()


if __name__=="__main__":
    assert os.environ["GITHUB_ACTIONS"]=="true"
    assert os.environ["GITHUB_REF"]=="refs/heads/"+context.BRANCH
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(kind)for kind in (Controls,CapsuleControls)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status="PASS" if result.wasSuccessful()else "FAIL",
      source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      tests=result.testsRun,synthetic_capsule=CapsuleControls.evidence,failures=[dict(test=str(x),traceback=y)for x,y in result.failures],
      errors=[dict(test=str(x),traceback=y)for x,y in result.errors],skipped=result.skipped,
      native_acquisition=False,native_executed=False,physical_acceptance=False,
      timing_accepted=False,full_phy_accepted=False)
    Path("bulk-postdrt-integration-controls/stale-wire-admission-controls.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    sys.exit(0 if result.wasSuccessful()and result.testsRun==28 and not result.skipped else 1)
