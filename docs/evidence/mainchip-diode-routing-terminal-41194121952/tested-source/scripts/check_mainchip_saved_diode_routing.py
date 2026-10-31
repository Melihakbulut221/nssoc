#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls; synthetic native boundaries are explicitly identified."""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,types
from pathlib import Path
import mainchip_saved_diode_routing as plan
import mainchip_bulk_postdrt_antenna as p
ROOT=Path(__file__).resolve().parent.parent

def main():
    target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
    inherited_path=target.with_name("routing-inherited-controls.json")
    call=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/check_mainchip_saved_diode_reconstruction.py"),str(inherited_path)],capture_output=True)
    target.with_name("routing-inherited-controls.stdout").write_bytes(call.stdout)
    target.with_name("routing-inherited-controls.stderr").write_bytes(call.stderr)
    assert call.returncode==0,"inherited actual source controls"
    inherited=json.loads(inherited_path.read_bytes());assert inherited["count"]==62
    rows=list(inherited["passed_cases"])
    def ok(name,fn):
        assert name not in rows
        fn();rows.append(name)
    def refuse(name,fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,RuntimeError):rows.append(name)
        else:raise AssertionError("not refused: "+name)
    def eq(a,b):assert a==b,(a,b)
    a=dict(box=[0,0,10,10],layer="Metal1",via_layer="Metal2",congested=False,jumper=False,connected_to_term=True,properties=[])
    b=dict(a,box=[10,0,20,10],jumper=True)
    before={"owned":[a],"other":[b,b],"clock":[a]}
    donor={"owned":[b,a,b]}
    def overlay(before=before,donor=donor,owners=["owned"],protected=["clock"]):
        return plan.guide_overlay(before,donor,owners,protected)
    def positive():
        actual,delta=overlay()
        eq(actual,{"owned":[b,a,b],"other":[b,b],"clock":[a]})
        eq(delta["changed_owners"],["owned"]);assert delta["all_flags_preserved"]is True
        eq(before["owned"],[a])
    ok("routing guide exact flags order multiplicity and unowned preservation",positive)
    ok("routing unchanged owner guide accepted",lambda:eq(overlay(donor={"owned":[a]})[1]["changed_owners"],[]))
    refuse("routing protected guide mutation refused",lambda:overlay(owners=["clock"],donor={"clock":[b]}))
    refuse("routing unknown guide owner refused",lambda:overlay(owners=["missing"],donor={"missing":[b]}))
    refuse("routing duplicate owner refused",lambda:overlay(owners=["owned","owned"]))
    refuse("routing missing donor owner refused",lambda:overlay(donor={}))
    refuse("routing extra donor owner refused",lambda:overlay(donor=dict(donor,other=[a])))
    refuse("routing empty owned guides refused",lambda:overlay(donor={"owned":[]}))
    for field,value in(("box",[10,0,0,10]),("box",[0.0,0,10,10]),("layer",""),("via_layer",None),
      ("congested",1),("jumper",0),("connected_to_term",None),("properties",[{"name":"hidden"}])):
        refuse("routing invalid guide field "+field+repr(value),lambda field=field,value=value:plan.validate_guide(dict(a,**{field:value})))
    refuse("routing missing native guide field refused",lambda:plan.validate_guide({k:v for k,v in a.items()if k!="jumper"}))
    refuse("routing unknown native guide field refused",lambda:plan.validate_guide(dict(a,unknown=True)))
    ok("routing zero area guide retained without invented geometry",lambda:plan.validate_guide(dict(a,box=[0,0,0,10])))
    # Exercise actual native record extraction, with only dbObject boundaries synthetic.
    path=ROOT/"scripts/mainchip_saved_diode_routing_native.py"
    tree=ast.parse(path.read_bytes());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=="guides")
    scope=dict(p=p,plan=plan,own=types.SimpleNamespace(box=lambda x:list(x)),
      same_native=lambda x,y:x is y,odb=types.SimpleNamespace(dbProperty=types.SimpleNamespace(getProperties=lambda x:x.props)))
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),"exec"),scope)
    class Net:
        def __init__(self,name):self.name=name;self.gs=[]
        def getName(self):return self.name
        def getGuides(self):return self.gs
    class Guide:
        def __init__(self,net,row):self.net=net;self.row=row;self.props=[]
        def getNet(self):return self.net
        def getBox(self):return self.row["box"]
        def getLayer(self):return types.SimpleNamespace(getName=lambda:self.row["layer"])
        def getViaLayer(self):return types.SimpleNamespace(getName=lambda:self.row["via_layer"])
        def isCongested(self):return self.row["congested"]
        def isJumper(self):return self.row["jumper"]
        def isConnectedToTerm(self):return self.row["connected_to_term"]
    net=Net("owned");guide=Guide(net,b);net.gs=[guide,guide]
    block=types.SimpleNamespace(getNets=lambda:[net],findNet=lambda name:net if name=="owned"else None)
    ok("routing actual native extractor retains duplicate flagged guides",lambda:eq(scope["guides"](block),{"owned":[b,b]}))
    guide.props=[object()]
    refuse("routing actual extractor refuses unknown guide property",lambda:scope["guides"](block))
    guide.props=[];guide.net=Net("owned")
    refuse("routing actual extractor refuses different live owner",lambda:scope["guides"](block))
    guide.net=net
    refuse("routing actual extractor refuses missing native owner",lambda:scope["guides"](block,["absent"]))
    # Full cycle lifecycle uses actual implementation, synthetic native callbacks.
    def cycle(fail=None,restore_failure=False,preserve_failure=False,writer_failure=False):
        seen=[];saved={};sentinel=RuntimeError("primary:"+str(fail))
        def action(name):
            seen.append(name)
            if name==fail:raise sentinel
            return dict(complete=True)
        def restore(states):
            seen.append("restore")
            if restore_failure:raise RuntimeError("restore-failure")
            return dict(complete=True,observed=dict(states))
        def preserve():
            seen.append("preserve")
            if preserve_failure:raise RuntimeError("preserve-failure")
            return dict(complete=True)
        def writer(name,value):
            saved[name]=copy.deepcopy(value)
            if writer_failure and name=="route-cycle-terminal.json":raise RuntimeError("writer-failure")
        error=None;result=None
        try:result=plan.run_phases({name:lambda name=name:action(name)for name in plan.PHASES},restore,preserve,writer)
        except BaseException as exc:error=exc
        eq(seen[-2:],["restore","preserve"])
        if fail is not None:
            assert error is sentinel
            eq(seen[:-2],list(plan.PHASES[:plan.PHASES.index(fail)+1]))
            eq(saved["route-cycle-terminal.json"]["phases"][fail],"failed")
        elif restore_failure or preserve_failure or writer_failure:assert error is not None
        else:
            assert error is None and result["complete"]is True
            eq(seen[:-2],list(plan.PHASES))
        return result,saved
    ok("routing cycle complete exact phase order",lambda:cycle())
    for phase in plan.PHASES:ok("routing cycle failure at "+phase,lambda phase=phase:cycle(fail=phase))
    ok("routing primary retained across restoration failure",lambda:cycle(fail="route",restore_failure=True))
    ok("routing primary retained across preservation failure",lambda:cycle(fail="route",preserve_failure=True))
    ok("routing primary retained across terminal writer failure",lambda:cycle(fail="route",writer_failure=True))
    ok("routing cleanup failure cannot become success",lambda:cycle(restore_failure=True))
    ok("routing preservation failure cannot become success",lambda:cycle(preserve_failure=True))
    ok("routing terminal write failure cannot become success",lambda:cycle(writer_failure=True))
    refuse("routing phase omission refused",lambda:plan.run_phases({},lambda x:{"complete":True},lambda:{"complete":True},lambda x,y:None))
    # This is real preserved native evidence; no model output is invented.
    prefix=ROOT/plan.PROOF
    actual=json.loads((prefix/"readable-records/native/bulk-postdrt-inner-result.json").read_bytes())
    native=json.loads((prefix/"readable-records/native/bulk-postdrt-antenna/reconstruction-result.json").read_bytes())
    failed=json.loads((prefix/"readable-records/result.json").read_bytes())
    ok("routing accepts actual saved native engine while retaining failed host",lambda:plan.validate_saved_native(actual,native,failed))
    bad=copy.deepcopy(native);bad["candidate"]["sha256"]="0"*64
    refuse("routing rejects changed candidate in saved admission",lambda:plan.validate_saved_native(actual,bad,failed))
    badhost=copy.deepcopy(failed);badhost["error"]["error"]="unrelated failure"
    refuse("routing rejects unrelated failed host",lambda:plan.validate_saved_native(actual,native,badhost))
    # Exercise exact new inner phase dispatch and prohibit inherited antenna repair.
    source=(ROOT/"scripts/mainchip_saved_diode_routing_inner.py").read_bytes()
    parsed=ast.parse(source)
    fn=next(x for x in parsed.body if isinstance(x,ast.FunctionDef)and x.name=="run_route_cycle")
    assert all(x not in plan.PHASES for x in("repair","insertion-audit","construct"))
    ok("routing source excludes repair and repeated construction phases",lambda:eq(len(plan.PHASES),14))
    assert len(rows)==111 and len(set(rows))==111
    result=dict(status="PASS_SAVED_DIODE_ROUTING_SOURCE_CONTROLS",count=len(rows),passed_cases=rows,
      inherited=inherited,source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      native_executed=False,source_pin=hashlib.sha256(path.read_bytes()).hexdigest(),
      synthetic_boundaries=["dbGuide/dbNet wrappers for source extractor controls","native phase lifecycle callbacks"],
      authentic_producer_run=41190910993,**p.FLAGS)
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n");print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
