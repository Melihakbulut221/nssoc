"""Cloud-only source controls. Native DB proof is a separate required stage."""
import ast,copy,hashlib,inspect,itertools,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest import mock
import mainchip_stale_wire_routing as a
import cloud_mainchip_saved_diode_routing as old
from mainchip_stale_wire_routing import p

def fixture():
    row=dict(identity=dict(sigtype="SIGNAL",terminals=[["driver","Y"],["diode","A"]]),
             encoded=dict(wire_present=True,metadata="ROUTED",paths=["ROUTED"]),
             wire=dict(opcode_count=2,pin=dict(bytes=6,sha256="old")))
    before=dict(nets={"mutable":copy.deepcopy(row),"clock":copy.deepcopy(row),"other":copy.deepcopy(row)},
      instances={"driver":{"master":"buf"},"diode":{"master":"antenna"}},
      block={"dbu":1000},immutable={"PG":[1,2]},masters={"buf":{"width":3}},
      protected=["clock"],clock_record_pins={"clock":"pin"},diode_template={"master":"antenna"},def_pin="before")
    after=copy.deepcopy(before);after["def_pin"]="after"
    after["nets"]["mutable"]["encoded"].update(wire_present=False,paths=[])
    after["nets"]["mutable"]["wire"]=dict(opcode_count=0,pin=p.pin(p.encode(None)))
    admission=dict(mutable_nets=["mutable"],attachments={"diode":"mutable"},protected_nets=["clock"])
    return before,after,admission

class Controls(unittest.TestCase):
    def test_source(self):
        self.assertEqual(a.source_gate()["schema"],"mainchip-stale-wire-routing-v1")
    def test_exact_owned_clear(self):
        b,c,plan=fixture()
        r=a.clear_delta(b,c,plan)
        self.assertTrue(r["complete"]);self.assertEqual(r["cleared_nets"],["mutable"])
    def test_reject_all_unowned_snapshot_changes(self):
        b,c,plan=fixture()
        for key in ("instances","block","immutable","masters","protected","clock_record_pins","diode_template"):
            bad=copy.deepcopy(c);bad[key]={"changed":True}
            with self.subTest(key=key),self.assertRaises(AssertionError):a.clear_delta(b,bad,plan)
    def test_reject_unowned_wire(self):
        b,c,plan=fixture()
        for name in ("clock","other"):
            bad=copy.deepcopy(c);bad["nets"][name]["wire"]["opcode_count"]=0
            with self.subTest(net=name),self.assertRaises(AssertionError):a.clear_delta(b,bad,plan)
    def test_reject_owned_identity_or_metadata(self):
        b,c,plan=fixture()
        for path,value in ((("identity","sigtype"),"POWER"),(("encoded","metadata"),"FIXED"),
                           (("wire","opcode_count"),1),(("encoded","wire_present"),True)):
            bad=copy.deepcopy(c);bad["nets"]["mutable"][path[0]][path[1]]=value
            with self.subTest(path=path),self.assertRaises(AssertionError):a.clear_delta(b,bad,plan)
    def test_reject_noncandidate_scope(self):
        b,c,plan=fixture()
        for update in (dict(mutable_nets=[]),dict(mutable_nets=["mutable","mutable"]),
                       dict(protected_nets=["mutable"]),dict(attachments={"diode":"other"})):
            with self.subTest(update=update),self.assertRaises(AssertionError):a.clear_delta(b,c,dict(plan,**update))
    def test_initial_wire_required(self):
        b,c,plan=fixture()
        for update in (dict(wire_present=False),dict(paths=["FIXED"]),dict(metadata="FIXED")):
            bad=copy.deepcopy(b);bad["nets"]["mutable"]["encoded"].update(update)
            with self.subTest(update=update),self.assertRaises(AssertionError):a.clear_delta(bad,c,plan)
    def test_route_input_only(self):
        work=Path("/work/out/work/bulk-postdrt-antenna")
        raw="source {env}\nread_db {"+str(work/"fixed.odb")+"}\ndetailed_route {*}$drt_args\nwrite_db {out}\n"
        changed=a.route_text(raw,work)
        self.assertEqual(changed.replace("stale-wire-cleared.odb","fixed.odb"),raw)
        for bad in (raw+raw,raw.replace("fixed.odb","other.odb"),changed):
            with self.subTest(bad=bad),self.assertRaises(AssertionError):a.route_text(bad,work)
    def test_only_three_host_path_constants_change(self):
        derived=a.host_perform(old.perform,source_gate=lambda:None,MANIFEST=a.MANIFEST)
        def walk(code):
            for value in code.co_consts:
                if isinstance(value,types.CodeType):yield from walk(value)
                else:yield value
        previous=list(walk(old.perform.__code__));current=list(walk(derived.__code__))
        self.assertEqual(current,[a.INNER if x==a.OLD_INNER else x for x in previous])
        self.assertIs(derived.__globals__["publish_capsule"],old.publish_capsule)
        self.assertIs(derived.__globals__["plan"],old.plan)
    def test_real_host_environment(self):
        original=lambda *args:["docker","create","--network","none","image"]
        with mock.patch.dict(os.environ,{"GITHUB_ACTIONS":"true"}):
            self.assertEqual(a.hosted_argv(original,None,None,1,1),
              ["docker","create","--env","GITHUB_ACTIONS=true","--network","none","image"])
        with mock.patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}):
            with self.assertRaises(AssertionError):a.hosted_argv(original,None,None,1,1)
    def test_clock_ast_only_census_change(self):
        raw=(a.ROOT/"scripts/check_mainchip_route12_all_clocks.py").read_bytes()
        before=ast.parse(raw);after=a.gate_tree(raw)
        changed=[]
        expected=ast.parse("assert len(list(b.getInsts()))=={'before':153130,'after':154480}[label]").body[0]
        for node in ast.walk(after):
            if isinstance(node,ast.Assert)and ast.dump(node)==ast.dump(expected):
                changed.append(node);node.test.comparators[0]=ast.Constant(value=153130)
        self.assertEqual(len(changed),1);self.assertEqual(ast.dump(before),ast.dump(after))
        with self.assertRaises(AssertionError):a.gate_tree(raw+b"\n")
    def run_clock(self,after_count=154480,route_changed=False,instance_changed=False):
        raw=(a.ROOT/"scripts/check_mainchip_route12_all_clocks.py").read_bytes()
        names=["clknet_3_5_0_pcie_clk_i"]+["clock_"+str(i)for i in range(1690)]
        class Inst:
            def getName(self):return "clock_driver"
            def getMaster(self):return types.SimpleNamespace(getName=lambda:"buf")
            def getLocation(self):return (1+int(instance_changed and current["label"]=="after"),2)
            def getOrient(self):return "R0"
            def getPlacementStatus(self):return "PLACED"
        inst=Inst()
        class Net:
            def __init__(self,name):self.name=name
            def getName(self):return self.name
            def getSigType(self):return "CLOCK"
            def getWireType(self):return "ROUTED"
            def getITerms(self):return [types.SimpleNamespace(getInst=lambda:inst)]
        class Block:
            def getInsts(self):return itertools.repeat(None,153130 if current["label"]=="before"else after_count)
            def getNets(self):return [Net(n)for n in names]
            def findNet(self,name):return Net(name)
        block=Block();current={}
        db=types.SimpleNamespace(getChip=lambda:types.SimpleNamespace(getBlock=lambda:block))
        def read_db(db,path):current["label"]=Path(path).name
        def write_def(block,path):
            records={n:n+" route "+str(int(route_changed and current["label"]=="after"and i==0))for i,n in enumerate(names)}
            Path(path).write_text(json.dumps(records))
        odb=types.SimpleNamespace(dbDatabase=types.SimpleNamespace(create=lambda:db,destroy=lambda db:None),read_db=read_db,write_def=write_def)
        split=types.SimpleNamespace(split_def=lambda text:(None,json.loads(text)))
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp)
            for n in ("before","after"):(root/n).write_bytes(n.encode())
            env=dict(GITHUB_ACTIONS="true",NSSOC_CLOCK_BEFORE=str(root/"before"),NSSOC_CLOCK_AFTER=str(root/"after"),NSSOC_CLOCK_AUDIT=str(root/"audit"))
            with mock.patch.dict(sys.modules,{"odb":odb,"prepare_mainchip_repair_deep_fresh_route":split}),mock.patch.dict(os.environ,env):
                exec(compile(a.gate_tree(raw),"derived-gate","exec"),{"__name__":"__main__"})
            return json.loads((root/"audit/result.json").read_bytes())
    def test_full_clock_gate_current_census(self):
        r=self.run_clock();self.assertEqual(r["clock_or_fixed_nets"],1691)
        self.assertTrue(r["all_source_clock_and_fixed_records_preserved"])
    def test_full_clock_gate_wrong_census(self):
        for count in (153130,154479,154481):
            with self.subTest(count=count),self.assertRaises(AssertionError):self.run_clock(after_count=count)
    def test_full_clock_gate_route_drift(self):
        with self.assertRaises(AssertionError):self.run_clock(route_changed=True)
    def test_full_clock_gate_instance_drift(self):
        with self.assertRaises(AssertionError):self.run_clock(instance_changed=True)

if __name__=="__main__":unittest.main()
