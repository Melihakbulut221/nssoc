"""Cloud-only full authenticated current650-device waveform and clock-switch headroom diagnosis."""
import ast,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
import numpy as np
import cdr_sampler_stage_timing as stage_timing
import cdr_current_domain_partition as domain
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"wire-wave-diagnosis";NATIVE=ROOT/"wire-wave-diagnosis-native"
CFG="scripts/cdr-wire-wave-diagnosis-inputs.json"
PINS="scripts/cdr-wire-wave-diagnosis-pins.json"
BRANCH="codex/cdr-current-domain-stage-diagnosis";REPO="Melihakbulut221/nssoc"
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
    need(e.get("RUNNER_ENVIRONMENT")=="github-hosted"and e["APPROVED_SOURCE"]==e["GITHUB_SHA"],"approved hosted exact source")
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
    plan=derivation["plan"];summary=derivation["summary"]
    need(type(plan)is list and len(plan)==50,"actual50 original MOS plans")
    need({p["native_id"]for p in plan}==set(range(1,51)),"all50 actual unique MOS origin identities")
    units=[u for p in plan for u in p["units"]]
    need(len(units)==200 and len({u["instance"]for u in units})==200,"all200 unique explicit units")
    for p in plan:
        need(sum(domain.prior.scalar(u["parameters"]["w"])for u in p["units"])==domain.prior.scalar(p["original_parameters"]["w"]),"exact total original width")
        for u in p["units"]:
            q=u["parameters"]
            need(domain.prior.Decimal(".15e-6")<=domain.prior.scalar(q["w"])<=domain.prior.Decimal("10e-6"),"each actual unit width domain")
            need(q["ng"]==q["m"]=="1"and q["l"]==p["original_parameters"]["l"],"independent single-gate original-length units")
    need(summary["original_devices"]==500 and summary["candidate_devices"]==650 and summary["candidate_mos"]==200,"exact current census")
    need(summary["all450_other_devices_unchanged"]and summary["all98_resistors_unchanged"]and summary["all_parent_wire_RC_unchanged"]and summary["original_model_exact_reversal"],"current-parent MOS-only derivation")
    need(all(summary[k]is False for k in domain.FLAGS),"no inherited physical or timing acceptance")
    proof=derivation["model_domain"]
    need(proof["status"]=="PASS_ACTUAL_RUNTIME_WIDTH_MEMBERSHIP_NOT_MODEL_OR_PHYSICAL_QUALIFICATION"and proof["units"]==200,"actual width membership proof")
    return True
def trial_delta_controls():
    import copy
    d=json.loads((ROOT/"docs/evidence/current-domain-wave-derivation-fixture.json").read_bytes())
    need(trial_delta(d),"actual native derivation structure")
    rejected=[]
    for label in ("missing-origin","duplicate-origin","out-of-domain-unit","metadata-fingers","wrong-total-width","stale500-census","false-physical-pass"):
        bad=copy.deepcopy(d)
        if label=="missing-origin":bad["plan"].pop()
        elif label=="duplicate-origin":bad["plan"][-1]=copy.deepcopy(bad["plan"][0])
        elif label=="out-of-domain-unit":bad["plan"][0]["units"][0]["parameters"]["w"]="11u"
        elif label=="metadata-fingers":bad["plan"][0]["units"][0]["parameters"]["ng"]="4"
        elif label=="wrong-total-width":bad["plan"][0]["original_parameters"]["w"]="99u"
        elif label=="stale500-census":bad["summary"]["candidate_devices"]=500
        else:bad["summary"]["physical_acceptance"]=True
        try:trial_delta(bad)
        except (AssertionError,ValueError):rejected.append(label)
        else:raise AssertionError("accepted corrupt current derivation "+label)
    return dict(actual_captured_derivation_passed=True,rejected=rejected,native_executed=False)
def prove_current_candidate(paths,m,contract,planes):
    derivation=json.loads(paths["derivation"].read_bytes());need(trial_delta(derivation),"actual current derivation")
    original=json.loads(paths["original_composition"].read_bytes())
    mapping=json.loads((ROOT/domain.MAP).read_bytes())
    state=domain.derive(paths["original_model"].read_text(),original,mapping)
    need(state["contract"]==contract and state["text"].encode()==paths["model"].read_bytes(),"rederive every actual650 model card and composition record")
    need(state["summary"]==derivation["summary"]and state["plan"]==derivation["plan"]and state["deltas"]==derivation["deltas"],"complete actual native derivation reproduced")
    need(paths["planes"].read_bytes()==paths["original_planes"].read_bytes(),"all actual160 native planes unchanged")
    need(len(m["mos_devices"])==len(m["mos_checks"])==200 and m["vector_census"]["total"]==1301,"all200 measured MOS currents and full1301 vectors")
    controls=m["binding_controls"]
    need(len(controls["rejected"])==13 and controls["equivalent_unit_spellings"]==2 and controls["candidate_expansion"]["checks"]==12 and controls["candidate_expansion"]["failures"]==0,"all actual baseline and expansion binding controls")
    audit=json.loads((ROOT/"docs/evidence/cdr-current-domain-model-proof.json").read_bytes())
    expected=[dict(path=str(Path(p["path"]).relative_to("source/model-sources")),**p["audited_pin"])for p in audit["all_current_model_pins_equal_historical_audit"]]
    need(derivation["model_domain"]["files"]==expected,"exact current three audited runtime model files")
    index=gate()["index"]["files"]
    for p in expected:need(index["native/runtime/source/model-sources/"+p["path"]]=={k:p[k]for k in ("bytes","sha256")},"actual fully authenticated model member")
    save("candidate-analysis-scope.json",dict(derivation=derivation,actual_model_and_contract_rederived=True,
        unchanged48_HBT_role_mapping_required=True,new_transient_executed=False,physical_acceptance=False,full_phy_accepted=False))
def headroom_terms(upper_base,upper_emitter,clock_base,clock_collector,clock_emitter):
    common_mode=upper_base-clock_base
    upper_vbe=upper_base-upper_emitter
    clock_vbe=clock_base-clock_emitter
    access_drop=upper_emitter-clock_collector
    reconstructed=common_mode-upper_vbe+clock_vbe-access_drop
    actual=clock_collector-clock_emitter
    need(np.isfinite([common_mode,upper_vbe,clock_vbe,access_drop,actual]).all(),"finite actual headroom decomposition")
    need(abs(reconstructed-actual)<1e-12,"exact Kirchhoff headroom identity")
    return dict(input_base_minus_clock_base_v=common_mode,upper_input_vbe_v=upper_vbe,
        clock_switch_vbe_v=clock_vbe,upper_emitter_to_clock_collector_drop_v=access_drop,
        reconstructed_clock_vce_v=reconstructed,actual_clock_vce_v=actual,deficit_below_400mv_v=max(0.,.4-actual))
def headroom_controls():
    r=headroom_terms(1.6,.7,1.2,.65,.3)
    need(abs(r["actual_clock_vce_v"]-.35)<1e-12 and abs(r["upper_emitter_to_clock_collector_drop_v"]-.05)<1e-12,"known signed wire/headroom example")
    reverse=headroom_terms(1.6,.7,1.2,.75,.3)
    need(reverse["upper_emitter_to_clock_collector_drop_v"]<0 and abs(reverse["actual_clock_vce_v"]-.45)<1e-12,"reverse wire drop sign retained")
    try:headroom_terms(float("nan"),.7,1.2,.65,.3)
    except AssertionError:pass
    else:raise AssertionError("accepted nonfinite diagnostic")
    return dict(exact_voltage_identity=True,signed_wire_drop_preserved=True,nonfinite_rejected=True,acceptance_limits_changed=False)
def diagnose_master_headroom(m,t,d,failures):
    def v(node):return np.zeros(len(t))if node=="0"else d["v("+node+")"]
    roles=json.loads((ROOT/stage_timing.TARGETS).read_bytes())["pairs"]
    named={r["schematic"]["name"]:"xpd."+r["loaded_instance"].lower()for r in roles}
    observed={}
    for sampler in ("C","D"):
        for leg in (0,1):
            role="S"+sampler+"_M_CS"+str(leg);key=named[role];clock=m["devices"][key]
            vc,vb,ve,_=map(v,clock["nodes"]);vce=vc-ve;active=np.flatnonzero(t>=2e-9)
            worst=int(active[np.argmin(vce[active])])
            need(abs(float(t[worst])-failures[key]["at_s"])<1e-18,"same actual failed sample")
            candidates=[]
            for polarity in ("DP","DN"):
                up_role="S"+sampler+"_M_"+polarity;up_key=named[up_role];up=m["devices"][up_key]
                _,ub,ue,_=map(v,up["nodes"]);current=d["@q."+up_key+".qnpn13g2[ic]"]
                terms=headroom_terms(float(ub[worst]),float(ue[worst]),float(vb[worst]),float(vc[worst]),float(ve[worst]))
                candidates.append(dict(role=up_role,device=up_key,native_id=up["native_id"],collector_current_a=float(current[worst]),
                    upper_base_v=float(ub[worst]),upper_emitter_v=float(ue[worst]),terms=terms))
            conducting=max(candidates,key=lambda x:abs(x["collector_current_a"]))
            observed[role]=dict(device=key,native_id=clock["native_id"],index=worst,at_s=float(t[worst]),
                clock_base_v=float(vb[worst]),clock_collector_v=float(vc[worst]),clock_emitter_v=float(ve[worst]),
                external_cn_v=float(v("cn")[worst]),external_cn_minus_local_base_v=float(v("cn")[worst]-vb[worst]),
                clock_current_a=float(d["@q."+key+".qnpn13g2[ic]"][worst]),both_upper_input_candidates=candidates,
                largest_absolute_upper_current_candidate=conducting,
                selection_rule="Largest absolute measured collector current at the same original Vce minimum; both branches retained")
    save("master-clock-headroom.json",dict(parent=m["current_context"],observations=observed,
        controls=headroom_controls(),all_samples_original=True,new_transient_executed=False,causal_fix_proven=False,
        electrical_rejection_preserved=True,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))

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
    save("controls.json",dict(status="PASS_FROZEN_FULL_WAVE_READER_CONTROLS",rejected=rejected,stage_controls=stage_timing.source_controls(),trial_delta_controls=trial_delta_controls(),headroom_controls=headroom_controls(),new_transient_executed=False))
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
    need(m["status"]=="REJECTED_WHOLE_MIM_PD650_LOADED"and m["sources_unchanged"]and m["transient_executed"],"actual rejection")
    need(m["current_context"]==dict(source=c["parent"]["source"],run_id=c["parent"]["run"],attempt=1),"measurement source")
    t,d,capture=reader()(paths["wave"],m["vectors"],34.25e-9,.3125e-12)
    need(capture==m["raw_capture"],"same complete original native raw measurement")
    prove_current_candidate(paths,m,contract,planes)
    stage_timing.diagnose_stages(ROOT,m,contract,t,d,save)
    active=t>=2e-9;UI=125e-12;START=2e-9
    def v(n):
        n=m["binding"]["aliases"].get(n,n)
        return np.zeros(len(t))if n=="0"else d["v("+n+")"]
    records={x["native_id"]:x for x in contract["device_records"]}
    need(len(records)==650,"complete unique integer-or-unit native identities")
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
    diagnose_master_headroom(m,t,d,failures)
    save("native-device-diagnosis.json",dict(parent=c["parent"],capture={k:v for k,v in capture.items()if k!="logical_vector_order"},failing_devices=failures,timing=timing,original_electrical_rejection_preserved=True,physical_acceptance=False,new_transient_executed=False,full_phy_accepted=False,final_timing_complete=False))
    gate()
    save("result.json",dict(status="COMPLETE_ACTUAL650_FULL_WAVE_AND_MASTER_HEADROOM_DIAGNOSIS_NOT_ACCEPTANCE",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),failed_devices=list(failures),all_native_members_authenticated=True,full_original_wave_parsed=True,original_scalar_measurements_reproduced=True,new_transient_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
    print(json.dumps(dict(status="COMPLETE_ACTUAL650_FULL_WAVE_AND_MASTER_HEADROOM_DIAGNOSIS_NOT_ACCEPTANCE",failed_devices=list(failures))),flush=True)
if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    try:
        if sys.argv[1:]==["--controls"]:controls()
        elif sys.argv[1:]==["--diagnose"]:diagnose()
        else:raise AssertionError("known entry")
    except BaseException as exc:
        import traceback
        save("failure-"+sys.argv[1].lstrip("-")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
