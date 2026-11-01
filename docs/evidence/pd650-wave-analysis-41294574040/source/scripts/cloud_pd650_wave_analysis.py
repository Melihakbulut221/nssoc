#!/usr/bin/env python3
"""Authenticate existing PD650 raw rows and diagnose rejected sampling on GitHub.
No simulator, device/model mutation, new PEX or PHY acceptance.
"""
import ast,hashlib,json,os,subprocess,tarfile,traceback,sys,tempfile,copy
from pathlib import Path,PurePosixPath
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"pd650-wave-analysis"
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12
SOURCE="d638e0e3cd15a0ee930212c27ab1f238b5085237"
PRODUCER_RUN=41288195752;RELEASE=430445706
CASE="native/case-nominal_late/"
SELECTED={CASE+"native/wave.raw",CASE+"measurement-result.json","native/candidate/composition.json","native/candidate/planes.json"}
def sha(path):
    with Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x")as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
def api(path):
    return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def source_gate():
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
    assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"
    assert os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
    assert os.environ["GITHUB_REF"]=="refs/heads/codex/cdr-pd650-loaded-wave-analysis"
    assert np.__version__=="2.3.3"
    pins=json.loads((ROOT/"scripts/pd650-wave-analysis-pins.json").read_bytes())
    assert set(pins)=={"scripts/cloud_pd650_wave_analysis.py","scripts/pd650-wave-analysis-inputs.json",
      ".github/workflows/cloud-evidence-summary.yml","scripts/cloud_tx_stream.py",
      "scripts/cloud_cdr_current_eight_drain_loaded.py"}
    for name,pin in pins.items():
        p=ROOT/name;assert p.is_file()and not p.is_symlink()
        assert dict(bytes=p.stat().st_size,sha256=sha(p))==pin,name
    return pins
def parser():
    p=ROOT/"scripts/cloud_tx_stream.py"
    assert sha(p)=="2894eede2e5e087c23cadee9cec9dbdca359315a786cec0cabfe7f8da37449cb"
    definitions=[n for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name in ("digest","read_streamed_wave")]
    assert [n.name for n in definitions]==["digest","read_streamed_wave"]
    ns=dict(np=np,hashlib=hashlib,Path=Path)
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(p),"exec"),ns)
    return ns["read_streamed_wave"]
def measure(t,delta,expected,edges,phases,limit):
    signed=[];delays=[];events=[]
    for index,(bit,edge)in enumerate(zip(expected,edges,strict=True)):
        sign=2*bit-1
        margins=[float(np.interp(edge+p*UI,t,delta))*sign for p in phases]
        ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI))
        assert len(ids)
        bad=ids[delta[ids]*sign<.1]
        delay=0. if not len(bad)else float(t[bad[-1]]-edge+STEP)
        signed+=margins;delays.append(delay)
        events.append(dict(bit_index=index+1,expected=bit,edge_s=edge,phases=list(phases),
          signed_margins_v=margins,clock_to_valid_s=delay,
          predecessor_expected=expected[index-1]if index else None))
    result=dict(samples=len(signed),minimum_signed_margin_v=min(signed),
      wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),
      maximum_clock_to_valid_s=max(delays),clock_to_valid_by_bit_s=delays,
      passed=min(signed)>=.1 and max(delays)<=limit*UI)
    return result,events
def compare(actual,prior):
    assert set(actual)==set(prior)
    for key in actual:
        a,b=actual[key],prior[key]
        if isinstance(a,list):assert np.allclose(a,b,rtol=0,atol=1e-21),key
        elif isinstance(a,float):assert abs(a-b)<=1e-13,key
        else:assert a==b,key
def stats(values):
    return dict(min=float(np.min(values)),p05=float(np.quantile(values,.05)),median=float(np.median(values)),
                mean=float(np.mean(values)),p95=float(np.quantile(values,.95)),max=float(np.max(values)))
def controls():
    source_gate();read=parser();passed=[]
    with tempfile.TemporaryDirectory()as temp:
        path=Path(temp)/"synthetic.raw"
        header=b"Title: synthetic only\nDate: control\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 2\nNo. Points: 3\nVariables:\n0 time time\n1 v(x) voltage\nBinary:\n"
        matrix=np.array([[0.,.2],[.1,-.2],[.2,.2]],dtype="<f8")
        good=header+matrix.tobytes();path.write_bytes(good)
        t,d,c=read(path,["v(x)"],.2,.1);assert c["header_rows"]==3 and np.array_equal(d["v(x)"],matrix[:,1]);passed.append("actual pinned parser full rows")
        bads={"truncated":good[:-1],"extra":good+b"x","wrong-vector":good.replace(b"v(x)",b"v(y)"),
              "wrong-count":good.replace(b"Points: 3",b"Points: 4"),
              "complex":good.replace(b"Flags: real",b"Flags: complex")}
        for label,change in (("nonfinite",lambda m:m.__setitem__((1,1),np.nan)),
                              ("time-reversal",lambda m:m.__setitem__((1,0),-.1))):
            m=matrix.copy();change(m);bads[label]=header+m.tobytes()
        for label,data in bads.items():
            path.write_bytes(data)
            try:read(path,["v(x)"],.2,.1)
            except AssertionError:passed.append("reject "+label)
            else:raise AssertionError("Accepted "+label)
    original=ROOT/"scripts/cloud_cdr_current_eight_drain_loaded.py"
    assert sha(original)=="add45d0ef874ec93fc9078d99bbb5cb0e684b667ec2f5699121eadb821ec5392"
    nodes=[n for n in ast.walk(ast.parse(original.read_bytes()))if isinstance(n,ast.FunctionDef)and n.name=="measure"]
    assert len(nodes)==1
    t=np.arange(0,8*UI,STEP);delta=.2*np.sin(2*np.pi*t/UI)
    ns=dict(np=np,t=t,UI=UI,STEP=STEP,v=lambda n:delta if n=="p"else np.zeros(len(t)))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(original),"exec"),ns)
    for bits in ([0,1,0,1],[1,0,1,0],[0,0,0,0]):
        edges=[(i+1)*UI for i in range(4)]
        for phases,limit in (((.3,.6,.9),.3),((.6,.75,.9),.6)):
            actual,events=measure(t,delta,bits,edges,phases,limit)
            compare(actual,ns["measure"]("p","n",bits,edges,phases,limit))
            assert len(events)==4
            passed.append("exact original measure "+str(bits)+str(phases))
    assert relative_member("cloud-sampler-load/native/case/wave.raw","cloud-sampler-load")=="native/case/wave.raw"
    passed.append("exact producer archive prefix")
    for bad in ("native/wave.raw","/cloud-sampler-load/native/x","cloud-sampler-load/../x",
                "cloud-sampler-load//native/x","cloud-sampler-load"):
        try:relative_member(bad,"cloud-sampler-load")
        except AssertionError:passed.append("reject archive path "+bad)
        else:raise AssertionError("Accepted archive path "+bad)
    good=dict(source_head=SOURCE,current_context=dict(attempt=1,run_id=PRODUCER_RUN,source=SOURCE),
      case="nominal_late",accepted=False,devices_passed=True,data_offset_s=.15*UI,diagnostics=[],returncode=0)
    producer_measurement_gate(good);passed.append("actual list-valued empty diagnostics")
    for key,value in (("diagnostics",0),("diagnostics",["warning"]),("diagnostics","[]"),
                      ("data_offset_s",0.),("returncode",1),("devices_passed",False),
                      ("source_head","0"*40),("current_context",{})):
        bad=copy.deepcopy(good);bad[key]=value
        try:producer_measurement_gate(bad)
        except AssertionError:passed.append("reject producer "+key+repr(value))
        else:raise AssertionError("Accepted invalid producer "+key)
    assert len(passed)==29
    return dict(status="PASS_SOURCE_READER_AND_ORIGINAL_MEASUREMENT_CONTROLS",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),count=len(passed),passed=passed,native_simulation=False)
def relative_member(name,source_directory):
    assert source_directory=="cloud-sampler-load"
    path=PurePosixPath(name)
    assert str(path)==name and not path.is_absolute()and ".."not in path.parts
    assert len(path.parts)>=2 and path.parts[0]==source_directory
    return "/".join(path.parts[1:])
def acquire(work):
    inputs=json.loads((ROOT/"scripts/pd650-wave-analysis-inputs.json").read_bytes())
    run=api("actions/runs/"+str(PRODUCER_RUN))
    assert run["head_sha"]==SOURCE and run["status"]=="completed"and run["conclusion"]=="failure"
    release=api("releases/"+str(RELEASE));assert release["target_commitish"]==SOURCE
    assert api("git/ref/tags/"+release["tag_name"])["object"]["sha"]==SOURCE
    assets={a["name"]:a for a in release["assets"]};assert set(assets)==set(inputs["assets"])
    for name,pin in inputs["assets"].items():
        a=assets[name];assert a["size"]==pin["bytes"] and a["digest"]=="sha256:"+pin["sha256"]
        path=work/name
        with path.open("xb")as f:
            subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
        assert path.stat().st_size==pin["bytes"]and sha(path)==pin["sha256"]
    parts=json.loads((work/"parts.json").read_bytes());index=json.loads((work/"complete-output-index.json").read_bytes())
    assert parts["context"]==index["context"]==dict(attempt=1,run_id=PRODUCER_RUN,source=SOURCE)
    archive=work/"assembled.tar.gz"
    with archive.open("xb")as target:
        for i,part in enumerate(parts["parts"]):
            assert part["index"]==i and {k:part[k]for k in("bytes","sha256")}==inputs["assets"][part["name"]]
            with(work/part["name"]).open("rb")as f:
                for b in iter(lambda:f.read(1024*1024),b""):target.write(b)
    assert archive.stat().st_size==parts["archive"]["bytes"]and sha(archive)==parts["archive"]["sha256"]
    seen={};members=set()
    with tarfile.open(archive,mode="r|gz")as tar:
        for member in tar:
            p=PurePosixPath(member.name)
            assert not p.is_absolute()and ".."not in p.parts and member.name not in members
            members.add(member.name)
            if member.isdir():continue
            name=relative_member(member.name,parts["source_directory"])
            assert member.isfile()and name in index["files"]and name not in seen
            selected=name in SELECTED
            target=work/"selected"/name
            if selected:target.parent.mkdir(parents=True,exist_ok=True)
            out=target.open("xb")if selected else None;h=hashlib.sha256();n=0
            try:
                f=tar.extractfile(member)
                for b in iter(lambda:f.read(1024*1024),b""):
                    n+=len(b);h.update(b)
                    if out:out.write(b)
            finally:
                if out:out.close()
            pin=dict(bytes=n,sha256=h.hexdigest());assert pin==index["files"][name],member.name
            seen[name]=pin
    assert set(seen)==set(index["files"])and SELECTED<=set(seen)
    save("acquisition.json",dict(run=run,release=release,archive=parts["archive"],authenticated_members=seen,
      selected=sorted(SELECTED),native_simulation=False,native_payloads_remain_cloud=True))
    return work/"selected",index
def producer_measurement_gate(m):
    assert m["source_head"]==SOURCE
    assert m["current_context"]==dict(attempt=1,run_id=PRODUCER_RUN,source=SOURCE)
    assert m["case"]=="nominal_late"and m["accepted"]is False and m["devices_passed"]is True
    assert m["data_offset_s"]==.15*UI
    assert type(m["diagnostics"])is list and m["diagnostics"]==[]
    assert type(m["returncode"])is int and m["returncode"]==0
def analyze(base,index):
    m=json.loads((base/(CASE+"measurement-result.json")).read_bytes())
    producer_measurement_gate(m)
    bound=m["binding"];vectors=m["raw_capture"]["logical_vector_order"][1:]
    assert len(vectors)==1301 and len(set(vectors))==1301
    t,d,capture=parser()(base/(CASE+"native/wave.raw"),vectors,STOP,STEP)
    assert capture==m["raw_capture"]
    # Preserve every row; cache read-only contiguous arrays for repeated point diagnostics.
    t=np.array(t,copy=True);t.setflags(write=False);voltage_cache={}
    def v(n):
        n=bound["aliases"].get(n,n)
        if n not in voltage_cache:
            value=np.zeros(len(t))if n=="0"else np.array(d["v("+n+")"],copy=True)
            value.setflags(write=False);voltage_cache[n]=value
        return voltage_cache[n]
    expected=m["expected_samples"]
    bits=[expected["c"][0],*expected["a"]]
    assert len(bits)==256 and hashlib.sha256(bytes(bits)).hexdigest()==m["source_bits_sha256"]
    assert expected==dict(a=bits[1:],b=bits[:-1],c=bits[:-1],d=bits[:-1])
    xbits=[a^b for a,b in zip(bits[1:],bits[:-1],strict=True)];ybits=[0]*255
    assert m["expected_comparisons"]==dict(x=xbits,y=ybits)
    active=t>=START;window=(t>=START+8*UI)&(t<=START+255*UI)
    outputs={tag:("xpd."+tag+"qp","xpd."+tag+"qn")for tag in"abcd"}
    outputs.update(x=("xp","xn"),y=("yp","yn"))
    voltage_nodes={k:n for k,n in bound["aliases"].items()}
    voltage_nodes.update({n:n for n in("cp","cn","dp","dn","xp","xn","yp","yn","vip","vin")})
    probe_devices={}
    for tag in"abcd":
        probe_devices[tag]=[]
        for leg in"pn":
            name="xpd."+bound["probe_witnesses"][tag+"q"+leg]["device"]
            dev=bound["groups"]["npn13g2"][name];probe_devices[tag].append(name)
            for terminal,node in zip("CBES",dev["nodes"],strict=True):voltage_nodes[name+"."+terminal]=node
    group_values={key:sum((d["@n."+n+".nsg13_lv_nmos[ids]"]for n in names),np.zeros(len(t)))for key,names in bound["mos_tail_groups"].items()}
    groups={key:dict(units=bound["mos_tail_groups"][key],active_current_a=stats(values[active]))for key,values in group_values.items()}
    stages={}
    for tag,(p,n)in outputs.items():
        phases=(.3,.6,.9)if tag in"abcd"else(.6,.75,.9);limit=.3 if tag in"abcd"else.6
        target=expected[tag]if tag in"abcd"else m["expected_comparisons"][tag]
        edges=[START+(i+(0 if tag=="b"else.5))*UI for i in range(1,256)]
        delta=v(p)-v(n)
        reproduced,events=measure(t,delta,target,edges,phases,limit)
        prior=m["sampler_checks"][tag]if tag in"abcd"else m["comparisons"][tag]
        compare(reproduced,prior)
        transition={}
        for before in(0,1):
            for after in(0,1):
                rows=[e for e in events if e["predecessor_expected"]==before and e["expected"]==after]
                if rows:
                    transition[str(before)+"->"+str(after)]=dict(bits=len(rows),
                       phase_margins_v={str(phase):stats([r["signed_margins_v"][i]for r in rows])for i,phase in enumerate(phases)},
                       clock_to_valid_s=stats([r["clock_to_valid_s"]for r in rows]))
        ids=set(e["bit_index"]for e in sorted(events,key=lambda e:min(e["signed_margins_v"]))[:8])
        ids.update(e["bit_index"]for e in sorted(events,key=lambda e:e["clock_to_valid_s"],reverse=True)[:8])
        worst=[]
        for event in events:
            if event["bit_index"]not in ids:continue
            sample=[]
            for phase in(0,.3,.6,.9):
                when=event["edge_s"]+phase*UI
                sample.append(dict(phase=phase,time_s=when,
                  voltages_v={label:float(np.interp(when,t,v(node)))for label,node in voltage_nodes.items()},
                  stage_currents_a={label:float(np.interp(when,t,value))for label,value in group_values.items()},
                  collector_currents_a={name:float(np.interp(when,t,d["@q."+name+".qnpn13g2[ic]"]))for name in probe_devices.get(tag,[])}))
            worst.append(dict(event=event,samples=sample))
        stages[tag]=dict(reproduced_original_gate=reproduced,active_output_diff_v=stats(delta[active]),
           active_commonmode_v=stats(((v(p)+v(n))/2)[active]),by_transition=transition,
           worst_cases=worst,events=events,probe_devices=probe_devices.get(tag,[]))
    phase=float(np.trapezoid(((v("xp")-v("xn"))-(v("yp")-v("yn")))[window],t[window])/(t[window][-1]-t[window][0]))
    assert abs(phase-m["phase_average_v"])<1e-13 and phase<.03
    contract=json.loads((base/"native/candidate/composition.json").read_bytes())
    planes=json.loads((base/"native/candidate/planes.json").read_bytes())
    logical={}
    for a in planes["anchors"]:
        key=(a["native_cluster"],a["native_name"])
        logical.setdefault(key,[]).append(a["logical_net"])
    topology=[]
    for dev in contract["device_records"]:
        if dev["model"]not in("npn13g2","sg13_lv_nmos","rppd"):continue
        topology.append(dict(instance=dev["instance"],model=dev["model"],native_id=dev["native_id"],
          source_native_id=dev.get("source_native_id"),parameters=dev["parameters"],
          terminals=[dict(x,logical_nets=sorted(set(logical.get((x["native_cluster"],x["native_net"]),[]))))for x in dev["terminals"]]))
    # Diagnose buffer paths only after reproducing all original acceptance metrics.
    # This never creates a new acceptance criterion or replaces the six original gates.
    record_by_name={"xpd."+r["instance"].lower():r for r in contract["device_records"]}
    def base_node(ident,logical_name):
        name="xpd.xd"+format(ident,"04d")
        row=record_by_name[name];assert row["model"]=="npn13g2"
        terminal=next(r for r in row["terminals"]if r["terminal"]=="B")
        assert logical_name in logical[(terminal["native_cluster"],terminal["native_net"])]
        dev=bound["groups"]["npn13g2"][name]
        return dev["nodes"][1]
    paths={
      "A_divider":("a",base_node(123,"uap"),base_node(125,"uan")),
      "A_buffer":("a","xpd.adp","xpd.adn"),
      "C_divider":("c",base_node(128,"ucp"),base_node(130,"ucn")),
      "C_buffer":("c","xpd.cdp","xpd.cdn"),
      "D_divider_X":("d",base_node(131,"usp"),base_node(132,"usn")),
      "D_divider_Y":("d",base_node(149,"usp"),base_node(150,"usn")),
      "D_buffer_X":("d","xpd.s0p","xpd.s0n"),
      "D_buffer_Y":("d","xpd.s1p","xpd.s1n")}
    path_results={}
    for name,(reference,p,n)in paths.items():
        phases=(.3,.6,.9);edges=[START+(i+.5)*UI for i in range(1,256)]
        metric,events=measure(t,v(p)-v(n),expected[reference],edges,phases,.3)
        metric.pop("passed") # diagnostic only, never a substituted gate
        original_events=stages[reference]["events"]
        conditional={}
        for phase_index,phase in enumerate(phases):
            samples=[]
            for output,probe in zip(original_events,events,strict=True):
                assert output["bit_index"]==probe["bit_index"]and output["expected"]==probe["expected"]
                samples.append(dict(bit=probe["bit_index"],expected=probe["expected"],
                  source_signed_v=output["signed_margins_v"][phase_index],
                  probe_signed_v=probe["signed_margins_v"][phase_index]))
            settled=[r for r in samples if r["source_signed_v"]>=.1]
            wrong=[r for r in settled if r["probe_signed_v"]<=0]
            conditional[str(phase)]=dict(total=len(samples),source_at_least_100mv=len(settled),
              source_valid_but_probe_wrong_sign=len(wrong),wrong_bit_indices=[r["bit"]for r in wrong],
              actual_wrong_examples=wrong[:8])
        path_results[name]=dict(reference_sampler=reference,positive_physical_node=bound["aliases"].get(p,p),
          negative_physical_node=bound["aliases"].get(n,n),metrics=metric,source_conditioned=conditional,
          events=events,diagnostic_only=True)
    save("buffer-paths.json",path_results)
    hbt={}
    for name,dev in bound["groups"]["npn13g2"].items():
        vc,vb,ve,_=map(v,dev["nodes"]);current=d["@q."+name+".qnpn13g2[ic]"]
        hbt[name]=dict(nodes=dev["nodes"],nx=dev["nx"],active_ic_a=stats(current[active]),
          active_vce_v=stats((vc-ve)[active]),active_vbe_v=stats((vb-ve)[active]),
          original_device_gate=m["device_checks"][name])
    for name,value in [("stages.json",stages),("tail-groups.json",groups),("hbt-state.json",hbt),
                       ("logical-device-topology.json",topology),("producer-measurement.json",m)]:
        save(name,value)
    result=dict(status="PASS_AUTHENTICATED_FAILURE_ANALYSIS_ONLY",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),
      producer_source=SOURCE,producer_run=PRODUCER_RUN,producer_release=RELEASE,raw_capture=capture,
      all_six_original_measurements_reproduced=True,phase_average_v=phase,phase_gate_v=.03,
      summary={k:{key:value for key,value in stage["reproduced_original_gate"].items()if key!="clock_to_valid_by_bit_s"}for k,stage in stages.items()},
      original_devices_passed=True,native_simulation=False,source_models_changed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
      scope="Existing full raw rows only. Diagnostic samples use interpolation exactly as original measurement; complete raw remains immutable and cloud-only.")
    save("result.json",result)
    print(json.dumps({k:v for k,v in result.items()if k!="raw_capture"},sort_keys=True))
def main():
    pins=source_gate();OUT.mkdir(exist_ok=False)
    if sys.argv[1:]==["controls"]:
        save("controls.json",controls());return
    assert sys.argv[1:]==["analyze"]
    work=Path(os.environ["RUNNER_TEMP"])/("pd650-wave-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
    base,index=acquire(work);analyze(base,index)
    assert source_gate()==pins
if __name__=="__main__":
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        if not(OUT/"failure.json").exists():save("failure.json",dict(error=repr(error),traceback=traceback.format_exc(),native_simulation=False))
        raise
