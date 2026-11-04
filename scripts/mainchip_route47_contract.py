"""Strict scope for the actual47-net repair; no physical/timing acceptance."""
def need(value,message):
    if not value:raise ValueError(message)
def route_program(route,old,new):
    """Original route program with only its input binding changed.

    No per-iteration DRT snapshot insertion: the original keeps DRT_SAVE_SNAPSHOTS=0.
    """
    need(route.count(old)==1 and route.count("detailed_route {*}$drt_args")==1,"single original router input and call")
    need(route.count("puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN")==1,"single native route stage")
    need(route.count('$::env(DRT_SAVE_SNAPSHOTS) ne "0"')==1,"original snapshot-free route setting")
    need(new!=old and new not in route,"fresh input binding")
    changed=route.replace(old,new,1)
    need(changed.replace(new,old,1)==route,"only input binding differs from original route program")
    return changed
def select(plan,scope,before):
    owners=scope["routing_nets"];clocks=scope["protected_nets"]
    need(len(owners)==len(set(owners))and owners,"unique routing owners")
    need(len(clocks)==len(set(clocks))and clocks,"unique protected clocks")
    owners=set(owners);clocks=set(clocks);need(not owners&clocks,"clock excluded")
    need(set(before["protected"])==clocks,"actual protected clock identity")
    found=set();seen=set()
    need(plan["records"]and plan["violations"]==len(plan["records"]),"all report records")
    for row in plan["records"]:
        tokens=row["sources"].split(" ")
        need(all(t.startswith("net:")and len(t)>4 and not any(c.isspace()for c in t)for t in tokens),"literal source names")
        names=[t[4:]for t in tokens]
        need(names==row["names"]and set(names)<=set(before["nets"]),"all literal names exist in native snapshot")
        selected=sorted(set(names)&owners)
        need(selected and selected==row["selected_owners"],"each record has exact scoped owners")
        for name in names:need(before["nets"][name]["identity"]["name"]==name,"native exact name")
        found.update(selected);seen.update(names)
    need(sorted(found)==plan["selected_routing_nets"]and len(found)==plan["selected_count"],"complete exact selection")
    for name in found:
        row=before["nets"][name]
        need(row["identity"]["sigtype"]=="SIGNAL"and row["encoded"]["wire_present"]and row["encoded"]["metadata"]=="ROUTED"and set(row["encoded"]["paths"])=={"ROUTED"},"actual ordinary routed selected signal")
    return sorted(found),sorted(seen)
def same_sections(before,after):
    need(set(before)==set(after),"complete snapshot fields")
    need(set(before["nets"])==set(after["nets"]),"complete net census")
    for name in before:
        if name not in("nets","def_pin"):need(before[name]==after[name],"unchanged native section "+name)
def wire_delta(before,after,selected,mode,missing_pin):
    need(mode in("clear","route"),"explicit wire delta")
    same_sections(before,after)
    need(selected and len(selected)==len(set(selected)),"unique delta owners")
    owners=set(selected)
    need(owners<=set(before["nets"])and not owners&set(before["protected"]),"known unprotected owners")
    changed=[]
    for name,old in before["nets"].items():
        new=after["nets"][name]
        need(set(old)==set(new)=={"identity","encoded","wire"},"complete native net fields")
        need(old["identity"]==new["identity"],"unchanged identity and terminals "+name)
        if name not in owners:need(old==new,"unchanged nonowner wire "+name);continue
        need(old["identity"]["sigtype"]=="SIGNAL"and old["encoded"]["metadata"]=="ROUTED","ordinary input owner")
        if mode=="clear":
            need(old["encoded"]["wire_present"]and set(old["encoded"]["paths"])=={"ROUTED"},"original routed owner")
            need(new["encoded"]==dict(wire_present=False,metadata="ROUTED",paths=[]),"exact cleared encoding")
            need(new["wire"]==dict(pin=missing_pin,opcode_count=0),"exact absent native wire")
        else:
            need(new["encoded"]["wire_present"]and new["encoded"]["metadata"]=="ROUTED"and set(new["encoded"]["paths"])=={"ROUTED"},"actual ordinary routed output")
            need(new["wire"]["opcode_count"]>0,"nonempty actual route")
        if old!=new:changed.append(name)
    return dict(mode=mode,selected=sorted(owners),changed=sorted(changed),all_other_wires_unchanged=True,
        all_clocks_unchanged=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
