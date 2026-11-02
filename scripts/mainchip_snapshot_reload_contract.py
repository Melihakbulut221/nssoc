"""Pure strict comparison for a partial route; never a completed-route acceptance."""
def need(ok, message):
    if not ok: raise ValueError(message)

def compare_scope(before, after, scope):
    owned = scope["routing_nets"]
    need(owned and len(owned) == len(set(owned)), "unique declared routing owners")
    owned = set(owned)
    need(set(before) == set(after), "complete snapshot fields")
    need(set(before["nets"]) == set(after["nets"]), "complete native net census")
    need(owned <= set(before["nets"]), "known routing owners")
    need(not owned & set(before["protected"]), "protected clock excluded from routing")
    for key in before:
        if key not in ("nets", "def_pin"):
            need(before[key] == after[key], "unchanged complete native section " + key)
    changed = []
    absent = []
    for name, old in before["nets"].items():
        new = after["nets"][name]
        need(set(old) == set(new) == {"identity", "encoded", "wire"}, "complete native net fields")
        need(old["identity"] == new["identity"], "unchanged net identity and all terminals " + name)
        if name not in owned:
            need(new == old, "unchanged nonowned wire " + name)
            continue
        need(old["identity"]["sigtype"] == "SIGNAL", "ordinary owned signal")
        need(old["encoded"] == {"wire_present": False, "metadata": "ROUTED", "paths": []}, "actual cleared route input")
        need(new["encoded"]["metadata"] == "ROUTED", "unchanged owned route class")
        need(set(new["encoded"]["paths"]) <= {"ROUTED"}, "ordinary routed path encoding")
        if new["encoded"]["wire_present"]:
            need(new["wire"]["opcode_count"] > 0, "nonempty present wire")
        else:
            need(new["encoded"]["paths"] == [] and new["wire"] == old["wire"], "exact missing wire")
            absent.append(name)
        if new != old: changed.append(name)
    return dict(scoped_delta_verified=True, changed_owners=sorted(changed),
                still_absent_owners=sorted(absent), protected_nets=len(before["protected"]),
                routing_complete=False, physical_acceptance=False, timing_accepted=False,
                full_phy_accepted=False)

def validate_archive_member(name, regular, size, expected, seen):
    from pathlib import PurePosixPath
    path = PurePosixPath(name)
    need(name not in seen, "unique archive member")
    need(name and not path.is_absolute() and ".." not in path.parts and str(path) == name, "canonical relative archive member")
    need(regular and name in expected, "declared regular archive member")
    need(size == expected[name]["bytes"], "exact declared member length")
    seen.add(name)
    return True
