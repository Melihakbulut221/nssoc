"""Explicit16-MOS proposed geometry binding; original topology/numerical gates remain frozen."""
import copy,json,re
import cdr_sampler_bias_trial as trial
need=trial.require
def target_map(root):
    values=json.loads((root/trial.TARGETS).read_bytes())
    need(len(values)==16 and {v["schematic"]["name"]:v["layout"]["id"]for v in values}==trial.IDS,"exact complete16 circuit plan")
    return {v["layout"]["id"]:v for v in values}
def revert_mos_record(line,record,target):
    model,old,new,order=trial.plan(target)
    need(model=="sg13_lv_nmos"and record["native_id"]==target["layout"]["id"]and record["instance"]==target["loaded_instance"]and record["model"]==model,"exact proposed MOS identity")
    need(record["parameters"]==new,"only explicitly proposed MOS parameters")
    need([t["terminal"]for t in record["terminals"]]==order,"exact proposed MOS terminal order")
    need({t["terminal"]:dict(cluster=t["native_cluster"],name=t["native_net"])for t in record["terminals"]}==
         {k:dict(cluster=v["cluster"],name=v["name"])for k,v in target["layout"]["terminals"].items()},"original mapped MOS terminal identities")
    nodes=[t["node"]for t in record["terminals"]]
    reversed_line=trial.rewrite_card(line,record["instance"],model,nodes,new,old)
    need(trial.rewrite_card(reversed_line,record["instance"],model,nodes,old,new)==line,"exact byte reversal of proposed MOS card")
    reversed_record=copy.deepcopy(record);reversed_record["parameters"]=old
    return reversed_line,reversed_record
def bind_with_proposed_geometry(original_bind,text,contract,planes,root):
    targets=target_map(root);records=contract["device_records"]
    need(len(records)==500 and len({r["native_id"]for r in records})==500,"entire500 native model retained")
    need({r["native_id"]for r in records}>=set(targets),"all16 native target identities")
    lines=text.splitlines(keepends=True);index={}
    for i,line in enumerate(lines):
        f=line.split()
        if f and f[0].lower().startswith("xd"):
            need(f[0].lower()not in index,"unique primitive card")
            index[f[0].lower()]=i
    restored=copy.deepcopy(contract);modified=[]
    for pos,record in enumerate(records):
        ident=record["native_id"]
        if ident not in targets:continue
        t=targets[ident];model,old,new,order=trial.plan(t)
        need(record["model"]==model and record["instance"]==t["loaded_instance"]and record["parameters"]==new,"exact16 proposed dimensions")
        if model!="sg13_lv_nmos":continue
        key=record["instance"].lower();need(key in index,"one actual proposed MOS card")
        i=index[key];lines[i],restored["device_records"][pos]=revert_mos_record(lines[i],record,t)
        modified.append(record)
    need(len(modified)==16,"only16 proposed slave MOS records")
    # This reversed copy is a read-only topology/dimension proof. The simulator
    # still reads the unmodified candidate file with actual48um intrinsic models.
    bound=original_bind("".join(lines),restored,planes)
    for record in modified:
        name="xpd."+record["instance"].lower();dev=bound["groups"]["sg13_lv_nmos"][name]
        need(dev["native_id"]==record["native_id"],"original binding returned same primitive")
        dev["parameters"]=copy.deepcopy(record["parameters"])
    bound["proposed_geometry_binding"]=dict(status="EXACT16_SLAVE_GEOMETRY_AFTER_ORIGINAL_TOPOLOGY_CHECK",
      instances=sorted(r["instance"]for r in modified),original_binding_source_unchanged=True,
      simulation_uses_actual_candidate_dimensions=True,read_only_reversal_for_validation_only=True,**trial.FLAGS)
    return bound
def numerical_namespace(original,root,numpy=None):
    ns=original.numerical_namespace(root,numpy);original_bind=ns["bind_native"]
    ns["_original_bind_native"]=original_bind
    ns["bind_native"]=lambda text,contract,planes:bind_with_proposed_geometry(original_bind,text,contract,planes,root)
    return ns
def source_controls(root):
    targets=target_map(root);passed=[];rejected=[]
    for ident,t in targets.items():
        model,old,new,order=trial.plan(t)
        if model!="sg13_lv_nmos":continue
        terms=[dict(terminal=k,node="n"+str(i),native_cluster=t["layout"]["terminals"][k]["cluster"],native_net=t["layout"]["terminals"][k]["name"])for i,k in enumerate(order)]
        record=dict(native_id=ident,instance=t["loaded_instance"],model=model,parameters=new,terminals=terms)
        line=" ".join([record["instance"],*[q["node"]for q in terms],model,*[k+"="+v for k,v in new.items()]])+"\n"
        out,rec=revert_mos_record(line,record,t)
        need(rec["parameters"]==old and "w=36u"in out and "w=48u"not in out,"native proposed MOS dimensions reversed")
        passed.append(record["instance"])
        if len(passed)>1:continue
        for label in ["paired-wrong-width","paired-wrong-diffusion","terminal-cluster","identity","duplicate-card-parameter"]:
            bad=copy.deepcopy(record);card=line
            if label.startswith("paired-"):
                key,value=("w","47u")if label=="paired-wrong-width"else("ad","16.33p")
                card=card.replace(key+"="+bad["parameters"][key],key+"="+value);bad["parameters"][key]=value
            elif label=="terminal-cluster":bad["terminals"][0]["native_cluster"]+=1
            elif label=="identity":bad["native_id"]+=1000
            else:card=card.rstrip()+" w=48u\n"
            try:revert_mos_record(card,bad,t)
            except (AssertionError,ValueError,KeyError):rejected.append(label)
            else:raise AssertionError("accepted adapter control "+label)
    need(len(passed)==16 and len(rejected)==5,"all adapter source controls")
    return dict(status="PASS_EXACT16_GEOMETRY_ADAPTER_SOURCE_CONTROLS",positive=passed,rejected=rejected,actual_native_model_bound=False,**trial.FLAGS)
def native_controls(ns,text,contract,planes,root):
    targets=target_map(root);bound=ns["bind_native"](text,contract,planes)
    for ident,t in targets.items():
        model,old,new,order=trial.plan(t)
        if model=="sg13_lv_nmos":need(bound["groups"][model]["xpd."+t["loaded_instance"].lower()]["parameters"]==new,"actual proposed parameters visible to measurement")
    try:ns["_original_bind_native"](text,contract,planes)
    except AssertionError:legacy_refusal=True
    else:raise AssertionError("original fixed geometry unexpectedly accepted proposed48um")
    selected=next(r for r in contract["device_records"]if r["native_id"]in targets and r["model"]=="sg13_lv_nmos")
    rejected=[]
    for key,value in [("w","47u"),("l","0.31u"),("ad","16.33p"),("ps","97u"),("ng","2"),("m","2"),("rfmode","1")]:
        c=copy.deepcopy(contract);d=next(r for r in c["device_records"]if r["native_id"]==selected["native_id"])
        old=d["parameters"][key];d["parameters"][key]=value
        ls=text.splitlines(keepends=True);i=next(i for i,l in enumerate(ls)if l.split()and l.split()[0]==d["instance"])
        ls[i],n=re.subn(r"(?<!\S)"+re.escape(key+"="+old)+r"(?!\S)",key+"="+value,ls[i]);need(n==1,"one paired native fault")
        try:ns["bind_native"]("".join(ls),c,planes)
        except (AssertionError,ValueError,KeyError):rejected.append("paired-"+key)
        else:raise AssertionError("accepted paired native fault "+key)
    # A same-size change at an unselected master cannot borrow the slave allowance.
    c=copy.deepcopy(contract);d=next(r for r in c["device_records"]if r["model"]=="sg13_lv_nmos"and r["native_id"]not in targets and r["parameters"]["w"]=="36u")
    ls=text.splitlines(keepends=True);i=next(i for i,l in enumerate(ls)if l.split()and l.split()[0]==d["instance"])
    old=copy.deepcopy(d["parameters"]);new=dict(old,w="48u",ad="16.32p",**{"as":"16.32p"},pd="96.68u",ps="96.68u")
    ls[i]=trial.rewrite_card(ls[i],d["instance"],d["model"],[t["node"]for t in d["terminals"]],old,new);d["parameters"]=new
    try:ns["bind_native"]("".join(ls),c,planes)
    except (AssertionError,ValueError,KeyError):rejected.append("unselected-master-borrowed-width")
    else:raise AssertionError("accepted unselected master width")
    need(len(rejected)==8,"all8 actual native adapter faults rejected")
    return dict(status="PASS_ACTUAL500_PROPOSED16_GEOMETRY_BINDING",original_fixed_geometry_refused=legacy_refusal,
      actual_proposed16_parameters_returned=True,original500_topology_and_other_geometry_checks_retained=True,
      rejected=rejected,transient_executed=False,**trial.FLAGS)
