"""Cloud-only passive sensitivity of the exact rejected new-ground RC model."""
import importlib.metadata,json,os,sys
from pathlib import Path
import cloud_cdr_wire_wave_diagnosis as prior
from cdr_selector_resistance import need,parse_model,solve

ROOT=Path(__file__).resolve().parents[1]
prior.BRANCH="codex/cdr-selector-resistance"
prior.OUT=ROOT/"wire-selector-resistance"
prior.NATIVE=ROOT/"wire-selector-resistance-native"

def gate():
    cfg=prior.gate()
    need(importlib.metadata.version("numpy")=="2.3.3"and importlib.metadata.version("scipy")=="1.16.3","declared solver versions")
    need(cfg["parent"]["run"]==41391065497 and cfg["parent"]["source"]=="494a63a4136813f6018c8cab027632ff02f54d0d","actual rejected new-ground producer")
    return cfg

def main():
    cfg=gate();prior.OUT.mkdir(exist_ok=True)
    if sys.argv[1:]==["--controls"]:
        prior.controls()
        return
    need(sys.argv[1:]==["--analyze"],"explicit read-only analysis")
    paths=prior.acquire(cfg)
    before={name:prior.pin(path)for name,path in paths.items()}
    contract=json.loads(paths["composition"].read_bytes())
    measurement=json.loads(paths["measurement"].read_bytes())
    need(measurement["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED"and measurement["sources_unchanged"],"preserved electrical rejection")
    need(measurement["current_context"]==dict(run_id=41391065497,source=cfg["parent"]["source"],attempt=1),"measurement binding")
    need(prior.pin(paths["model"])==dict(bytes=1982585,sha256="0bfdbf74c8dd73b2234b771746785af57fade28f122af94b436096c27b2ff943"),"exact current extracted model")
    need(prior.pin(paths["composition"])==dict(bytes=974729,sha256="c863575e8fd2f6586d0436a8db2fc0c80061b3032c8f9633fc9d9777f18c1527"),"exact current composition")
    edges,counts=parse_model(paths["model"].read_text(),contract)
    need(counts==dict(devices=500,R=24530,C=15676),"complete actual RC census")
    device={int(d["native_id"]):d for d in contract["device_records"]}
    def terminal(i,t):
        rows=[r for r in device[i]["terminals"]if r["terminal"]==t]
        need(len(rows)==1,"unique actual native terminal")
        return rows[0]
    queries=[]
    for first,seconds,origin,dest,group in [
        ((61,62),(54,56),"C","E","D_collector"),
        ((115,116),(106,108),"C","E","C_collector"),
        ((61,62),(3,4,5,6),"E","D","D_emitter"),
        ((115,116),(32,33,34,35),"E","D","C_emitter")]:
        for a in first:
            for b in seconds:
                x=terminal(a,origin);y=terminal(b,dest)
                need((x["native_cluster"],x["native_net"])==(y["native_cluster"],y["native_net"]),"same real extracted net")
                queries.append(dict(label=group+"_"+str(a)+"_"+str(b),source=x["node"].lower(),sink=y["node"].lower(),native_net=x["native_net"],source_terminal=[a,origin],sink_terminal=[b,dest]))
    need("avss"in contract["interface"],"real public avss port")
    for i in(3,4,5,6,32,33,34,35):
        x=terminal(i,"S");need(x["native_net"]=="avss","actual source ground ownership")
        queries.append(dict(label="ground_"+str(i),source=x["node"].lower(),sink="avss",native_net="avss",source_terminal=[i,"S"],sink_terminal="public_avss"))
    need(len(queries)==32,"all four selectors and eight source ground paths")
    summary=[]
    for query in queries:
        result=solve(edges,query["source"],query["sink"])
        reverse=solve(edges,query["sink"],query["source"])
        reff=result["effective_resistance_ohm"]
        need(abs(reverse["effective_resistance_ohm"]-reff)<=max(1e-9,1e-7*reff),"actual network reciprocity")
        result.update(query=query,reverse_resistance_ohm=reverse["effective_resistance_ohm"],physical_acceptance=False,full_phy_accepted=False)
        filename="pairs/"+query["label"]+".json";prior.save(filename,result)
        summary.append(dict(**query,effective_resistance_ohm=reff,component_nodes=result["component_nodes"],
            component_resistors=result["component_resistors"],maximum_kcl_residual_a=result["maximum_kcl_residual_a"],
            full_result=filename,full_result_pin=prior.pin(prior.OUT/filename),top_edges=result["full_edge_contributions"][:12]))
    need(before=={name:prior.pin(path)for name,path in paths.items()},"all actual model and evidence bytes unchanged")
    gate()
    prior.save("result.json",dict(status="COMPLETE_ACTUAL_EXTRACTED_SELECTOR_RESISTANCE_SENSITIVITY",
        source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),parent=cfg["parent"],counts=counts,
        inputs=before,queries=summary,solver_versions={n:importlib.metadata.version(n)for n in("numpy","scipy")},
        original_electrical_rejection_preserved=True,all_native_members_authenticated=True,
        new_transient_executed=False,loaded_simulation_passed=False,qualified_pex=False,
        full_phy_accepted=False,physical_acceptance=False,final_timing_complete=False,
        limits="Resistor-only unit-current network with other terminals floating. Capacitors are counted and preserved but excluded from this diagnostic. Edge power ranks sensitivity, not actual operating power. No nonlinear or transient acceptance follows."))
    print("COMPLETE_ACTUAL_EXTRACTED_SELECTOR_RESISTANCE_SENSITIVITY",flush=True)

if __name__=="__main__":
    try:main()
    except BaseException as exc:
        import traceback
        prior.OUT.mkdir(exist_ok=True)
        prior.save("failure-"+sys.argv[1].lstrip("-")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,full_phy_accepted=False))
        raise
