"""Cloud-only full authenticated waveform diagnosis of rejected physical PD500."""
import ast,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
import numpy as np
import cdr_sampler_stage_timing as stage_timing
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"wire-wave-diagnosis";NATIVE=ROOT/"wire-wave-diagnosis-native"
CFG="scripts/cdr-wire-wave-diagnosis-inputs.json"
PINS="scripts/cdr-wire-wave-diagnosis-pins.json"
BRANCH="codex/cdr-slave-drive-stage-timing";REPO="Melihakbulut221/nssoc"
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def digest(path):
    with Path(path).open("rb")as f:return hashlib.file_digest(f,"sha256").hexdigest()
def pin(path):return dict(bytes=Path(path).stat().st_size,sha256=digest(path))
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write((json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],timeout=180))
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e["GITHUB_REF"]=="refs/heads/"+BRANCH and e["GITHUB_RUN_ATTEMPT"]=="1","hosted first exact branch")
    need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_EVENT_NAME"]=="workflow_dispatch","explicit repository dispatch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"current source")
    m=json.loads((ROOT/PINS).read_bytes())
    for n,p in m["files"].items():need(pin(ROOT/n)==p,"protected source "+n)
    return json.loads((ROOT/CFG).read_bytes())
def reader():
    # Execute only these two exact frozen pure functions, not the module's CLI/imports.
    path=ROOT/"scripts/cloud_tx_stream.py";tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in("digest","read_streamed_wave")]
    need(len(nodes)==2,"both original pure definitions")
    ns=dict(Path=Path,hashlib=hashlib,np=np)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns)
    return ns["read_streamed_wave"]
def trial_delta(derivation):
    rows=derivation["delta"]
    expected={194,191,205,202,214,212,176,175,7,8,9,10,16,17,18,19,25,26,27,28,36,37,38,39}
    need(type(rows)is list and len(rows)==24,"actual24-element device delta list")
    need(all(isinstance(row,dict)and type(row.get("native_id"))is int for row in rows),"typed native delta identity")
    need({row["native_id"]for row in rows}==expected,"unique exact24 changed native devices")
    need(all(isinstance(row.get("old"),dict)and isinstance(row.get("new"),dict)and row["old"]!=row["new"]for row in rows),"actual changed parameter records")
    return True
def trial_delta_controls():
    import copy
    d=json.loads((ROOT/"docs/evidence/slave-drive-stage-derivation-fixture.json").read_bytes())
    need(trial_delta(d),"actual captured derivation list")
    rejected=[]
    for label,bad in (("integer_count",24),("missing_device",d["delta"][:-1]),("duplicate_device",d["delta"][:-1]+d["delta"][:1])):
        candidate=copy.deepcopy(d);candidate["delta"]=bad
        try:trial_delta(candidate)
        except AssertionError:rejected.append(label)
        else:raise AssertionError("accepted malformed derivation "+label)
    return dict(actual_captured_list_passed=True,rejected=rejected,native_executed=False)
def controls():
    gate();read=reader();folder=NATIVE/"controls";folder.mkdir(parents=True,exist_ok=False)
    head=b"Title: control\nDate: control\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 2\nNo. Points: 2\nVariables:\n0 time time\n1 v(x) voltage\nBinary:\n"
    data=np.array([[0.,.2],[1e-12,.3]],dtype="<f8").tobytes()
    p=folder/"valid.raw";p.write_bytes(head+data);t,d,c=read(p,["v(x)"],1e-12,1e-12)
    need(c["header_rows"]==2 and d["v(x)"][1]==.3,"positive frozen reader fixture")
    bad={"truncated":head+data[:-1],"extra":head+data+b"x",
      "wrong_vector":head.replace(b"v(x)",b"v(y)")+data,
      "wrong_kind":head.replace(b"v(x) voltage",b"v(x) current")+data,
      "row_count":head.replace(b"Points: 2",b"Points: 3")+data,
      "nonfinite":head+np.array([[0.,.2],[1e-12,np.nan]],dtype="<f8").tobytes(),
      "time_order":head+np.array([[0.,.2],[0.,.3]],dtype="<f8").tobytes(),
      "flags":head.replace(b"Flags: real",b"Flags: complex")+data}
    rejected=[]
    for label,b in bad.items():
        q=folder/(label+".raw");q.write_bytes(b)
        try:read(q,["v(x)"],1e-12,1e-12)
        except AssertionError:rejected.append(label)
        else:raise AssertionError("accepted malformed native "+label)
    save("controls.json",dict(status="PASS_FROZEN_FULL_WAVE_READER_CONTROLS",rejected=rejected,stage_controls=stage_timing.source_controls(),trial_delta_controls=trial_delta_controls(),new_transient_executed=False))
def acquire(c):
    p=c["parent"];r=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]));tag=api("git/ref/tags/"+p["tag"])
    need(r["status"]=="completed"and r["conclusion"]=="failure"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"actual rejected source")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and tag["object"]["sha"]==p["source"],"native release source")
    live={a["name"]:a for a in rel["assets"]};need(set(live)==set(p["assets"]),"complete release asset names")
    for name,a in p["assets"].items():
        actual=live[name];need(actual["id"]==a["id"]and actual["size"]==a["bytes"]and actual["digest"]=="sha256:"+a["sha256"],"native asset identity "+name)
    save("producer.json",dict(run=r,release=rel,tag=tag))
    NATIVE.mkdir(exist_ok=True)
    def download(name):
        a=p["assets"][name];dest=NATIVE/name
        with dest.open("xb")as f:
            subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
        need(pin(dest)=={k:a[k]for k in("bytes","sha256")},"download "+name)
        return dest
    idx=json.loads(download("complete-output-index.json").read_bytes())
    parts=json.loads(download("parts.json").read_bytes())
    need(idx==c["index"]and parts==c["parts"],"exact complete native index and parts")
    arc=NATIVE/"native.tar.gz"
    with arc.open("xb")as out:
        for i,a in enumerate(parts["parts"]):
            need(a["index"]==i,"ordered part")
            q=download(a["name"])
            with q.open("rb")as f:
                while chunk:=f.read(8*1024*1024):out.write(chunk)
            q.unlink()
    need(pin(arc)==parts["archive"],"full reconstructed native archive")
    wanted=set(c["selected"]);need(wanted<=set(idx["files"]),"selected current native entries")
    seen=set();dest=NATIVE/"selected";dest.mkdir()
    with tarfile.open(arc,"r|gz")as tar:
        for member in tar:
            prefix=parts["archive_root"]+"/";need(member.name.startswith(prefix),"archive root")
            name=member.name[len(prefix):]
            need(member.isfile()and name in idx["files"]and name not in seen,"exact unique regular indexed member")
            need(not Path(name).is_absolute()and ".."not in Path(name).parts,"safe selected member")
            expected=idx["files"][name];need(member.size==expected["bytes"],"member length")
            h=hashlib.sha256();size=0;f=tar.extractfile(member)
            target=dest/name
            if name in wanted:target.parent.mkdir(parents=True,exist_ok=True)
            out=target.open("xb")if name in wanted else None
            try:
                while chunk:=f.read(8*1024*1024):
                    size+=len(chunk);h.update(chunk)
                    if out is not None:out.write(chunk)
            finally:
                if out is not None:out.close()
                f.close()
            need(dict(bytes=size,sha256=h.hexdigest())==expected,"full member digest "+name);seen.add(name)
    need(seen==set(idx["files"]),"all native members authenticated")
    save("acquisition.json",dict(authenticated_members=len(seen),selected=sorted(wanted),archive=parts["archive"],native_payloads_cloud_only=True))
    return {role:dest/name for name,role in c["selected"].items()}
def diagnose():
    c=gate();paths=acquire(c);m=json.loads(paths["measurement"].read_bytes());contract=json.loads(paths["composition"].read_bytes());planes=json.loads(paths["planes"].read_bytes())
    need(m["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED"and m["sources_unchanged"]and m["transient_executed"],"actual rejection")
    need(m["current_context"]==dict(source=c["parent"]["source"],run_id=c["parent"]["run"],attempt=1),"measurement source")
    t,d,capture=reader()(paths["wave"],m["vectors"],34.25e-9,.3125e-12)
    need(capture==m["raw_capture"],"same complete original native raw measurement")
    derivation=json.loads(paths["derivation"].read_bytes())
    geometry=json.loads(paths["geometry_controls"].read_bytes())
    need(derivation["status"]=="DERIVED_PROVISIONAL_SLAVE_DRIVE_LOAD_TRIAL"and trial_delta(derivation),"actual24 parameter trial provenance")
    need(derivation["all_other476_devices_unchanged"]and derivation["all_parent_wire_RC_cards_unchanged"]and derivation["entire_model_exact_reversal"],"recorded complete original trial derivation")
    need(pin(paths["composition"])==derivation["trial_inputs"]["composition"]and pin(paths["planes"])==derivation["trial_inputs"]["planes"],"actual candidate composition and fixed parent planes")
    need(geometry["status"]=="PASS_ACTUAL500_PROPOSED16_GEOMETRY_BINDING"and len(geometry["rejected"])==8,"actual proposed geometry fault controls")
    binding=m["binding"]["proposed_geometry_binding"]
    need(binding["status"]=="EXACT16_SLAVE_GEOMETRY_AFTER_ORIGINAL_TOPOLOGY_CHECK"and len(binding["instances"])==16 and binding["simulation_uses_actual_candidate_dimensions"],"actual simulated candidate geometry")
    need(len(m["binding_controls"]["rejected"])==13 and m["binding_controls"]["equivalent_unit_spellings"]==2,"original complete binding fault controls")
    for report in (derivation,geometry,binding):
        need(all(report[k]is False for k in ("fresh_RC_for_modified_devices","full_phy_accepted","matching_layout_verified","physical_acceptance","qualified_pex","final_timing_complete")),"provisional scope preserved")
    save("candidate-analysis-scope.json",dict(derivation=derivation,geometry_controls=geometry,binding=binding,unchanged48_HBT_role_mapping_required=True,new_transient_executed=False,full_phy_accepted=False,physical_acceptance=False))
    stage_timing.diagnose_stages(ROOT,m,contract,t,d,save)
    active=t>=2e-9;UI=125e-12;START=2e-9
    def v(n):
        n=m["binding"]["aliases"].get(n,n)
        return np.zeros(len(t))if n=="0"else d["v("+n+")"]
    records={int(x["native_id"]):x for x in contract["device_records"]}
    logical={}
    for x in planes["anchors"]:logical.setdefault((x["native_cluster"],x["native_name"]),set()).add(x["logical_net"])
    def describe(n):
        rec=records[n];terms=[]
        for term in rec["terminals"]:
            key=(term["native_cluster"],term["native_net"])
            related=[]
            for other in contract["device_records"]:
                hits=[q["terminal"]for q in other["terminals"]if(q["native_cluster"],q["native_net"])==key]
                if hits:related.append(dict(native_id=other["native_id"],model=other["model"],terminals=hits))
            terms.append(dict(**term,logical_labels=sorted(logical.get(key,set())),connected_devices=related))
        return dict(native_id=n,instance=rec["instance"],model=rec["model"],parameters=rec["parameters"],terminals=terms)
    def signals(i):
        return {name:float(v(name)[i])for name in["cp","cn","dp","dn","xp","xn","yp","yn","vip","vin",*m["binding"]["aliases"]]}
    failures={}
    for name,dev in m["devices"].items():
        vc,vb,ve,_=map(v,dev["nodes"]);a=vc-ve;check=m["device_checks"][name]
        need(abs(float(a[active].min())-check["minimum_active_vce_v"])<1e-12,"native device minimum reproduction")
        if check["minimum_active_vce_v"]>=.4:continue
        mask=active&(a<.4);ids=np.flatnonzero(mask);worst=int(np.flatnonzero(active)[np.argmin(a[active])])
        starts=np.flatnonzero(mask&~np.r_[False,mask[:-1]]);ends=np.flatnonzero(mask&~np.r_[mask[1:],False])
        episodes=[dict(start_s=float(t[i]),end_s=float(t[j]),minimum_vce_v=float(a[i:j+1].min()))for i,j in zip(starts,ends,strict=True)]
        failures[name]=dict(device=describe(dev["native_id"]),minimum_vce_v=float(a[worst]),at_s=float(t[worst]),vc_v=float(vc[worst]),vb_v=float(vb[worst]),ve_v=float(ve[worst]),ic_a=float(d["@q."+name+".qnpn13g2[ic]"][worst]),samples_below=len(ids),episodes=episodes,signals_at_minimum=signals(worst))
    # Quantify voltage loss between terminals that share the SAME extracted net.
    # The distributed wire model remains unchanged; no ideal electrical alias is added.
    for name,row in failures.items():
        i=int(np.argmin(abs(t-row["at_s"])));rec=records[row["device"]["native_id"]]
        neighbors={}
        for term in rec["terminals"]:
            if term["terminal"]not in("C","E"):continue
            key=(term["native_cluster"],term["native_net"])
            origin_node=m["binding"]["interface"].get(term["node"],"xpd."+term["node"].lower())
            origin=float(v(origin_node)[i]);members=[]
            for other in contract["device_records"]:
                if other["model"]=="ptap1":continue
                hits=[q for q in other["terminals"]if(q["native_cluster"],q["native_net"])==key]
                if not hits:continue
                measurements=[]
                for q in other["terminals"]:
                    node=m["binding"]["interface"].get(q["node"],"xpd."+q["node"].lower())
                    value=float(v(node)[i])
                    measurements.append(dict(terminal=q["terminal"],native_net=q["native_net"],logical_labels=sorted(logical.get((q["native_cluster"],q["native_net"]),set())),node=node,voltage_v=value,same_extracted_net=(q["native_cluster"],q["native_net"])==key,delta_from_failed_terminal_v=value-origin))
                members.append(dict(native_id=other["native_id"],model=other["model"],parameters=other["parameters"],terminals=measurements))
            neighbors[term["terminal"]]=dict(native_net=term["native_net"],origin_node=origin_node,origin_voltage_v=origin,connected_devices=members)
        row["same_net_native_voltage_drops_at_minimum"]=neighbors
    need(set(failures)=={"xpd.xd0061","xpd.xd0062","xpd.xd0115","xpd.xd0116"},"same current four HBT failures")
    timing={}
    for kind,checks,expected,phases,limit in[("sampler",m["sampler_checks"],m["expected_samples"],(.3,.6,.9),.3),("comparison",m["comparisons"],m["expected_comparisons"],(.6,.75,.9),.6)]:
        for tag,check in checks.items():
            p,n=("xpd."+tag+"qp","xpd."+tag+"qn")if kind=="sampler"else(tag+"p",tag+"n")
            delta=v(p)-v(n);bits=expected[tag];rows=[];signed=[];delays=[]
            for i,bit in enumerate(bits,start=1):
                edge=START+(i+(0 if kind=="sampler"and tag=="b"else .5))*UI;sign=2*bit-1
                samples=[float(np.interp(edge+phase*UI,t,delta))*sign for phase in phases];signed+=samples
                ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
                delay=0. if not len(bad)else float(t[bad[-1]]-edge+.3125e-12);delays.append(delay)
                row=dict(bit_index=i,expected=bit,source_previous=m["source_bits"][i-1],source_current=m["source_bits"][i],edge_s=edge,signed_samples_v=samples,clock_to_valid_s=delay)
                if min(samples)<=0:
                    at=edge+phases[int(np.argmin(samples))]*UI
                    row["wrong_sign_at_s"]=at
                    row["hbt_vce_at_wrong_sample"]={name:float(np.interp(at,t,v(dev["nodes"][0])-v(dev["nodes"][2])))for name,dev in m["devices"].items()if name in failures}
                rows.append(row)
            need(abs(min(signed)-check["minimum_signed_margin_v"])<1e-12 and abs(max(delays)-check["maximum_clock_to_valid_s"])<1e-18,"same native margin and delay")
            need(sum(x<=0 for x in signed)==check["wrong_sign_samples"],"same wrong-sign count")
            summary={}
            for prev,cur in[(0,0),(0,1),(1,0),(1,1)]:
                group=[r for r in rows if(r["source_previous"],r["source_current"])==(prev,cur)]
                summary[str(prev)+str(cur)]=dict(bits=len(group),wrong_sign_samples=sum(x<=0 for r in group for x in r["signed_samples_v"]),below_100mv_samples=sum(x<.1 for r in group for x in r["signed_samples_v"]),minimum_margin_v=min((min(r["signed_samples_v"])for r in group),default=None),maximum_delay_s=max((r["clock_to_valid_s"]for r in group),default=None))
            timing[kind+"_"+tag]=dict(by_source_transition=summary,rows=rows)
    save("native-device-diagnosis.json",dict(parent=c["parent"],capture={k:v for k,v in capture.items()if k!="logical_vector_order"},failing_devices=failures,timing=timing,original_electrical_rejection_preserved=True,physical_acceptance=False,new_transient_executed=False,full_phy_accepted=False,final_timing_complete=False))
    gate()
    save("result.json",dict(status="COMPLETE_ACTUAL_FULL_WAVE_DIAGNOSIS_OF_ELECTRICAL_REJECTION",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),failed_devices=list(failures),all_native_members_authenticated=True,full_original_wave_parsed=True,original_scalar_measurements_reproduced=True,new_transient_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
    print(json.dumps(dict(status="COMPLETE_ACTUAL_FULL_WAVE_DIAGNOSIS_OF_ELECTRICAL_REJECTION",failed_devices=list(failures))),flush=True)
if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    try:
        if sys.argv[1:]==["--controls"]:controls()
        elif sys.argv[1:]==["--diagnose"]:diagnose()
        else:raise AssertionError("known entry")
    except BaseException as exc:
        import traceback
        save("failure-"+sys.argv[1].lstrip("-")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
