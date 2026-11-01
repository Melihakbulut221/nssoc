"""Separate routing ownership from immutable antenna/diode ownership.

No native work or authorization occurs on import. The future native adapter must
supply the original physical validators and complete native snapshots.
"""
import copy
import hashlib
import json

FLAGS = dict(physical_acceptance=False, timing_accepted=False, full_phy_accepted=False)

def require(value, message):
    if not value:
        raise AssertionError(message)

def exact(got, expected, message):
    require(got == expected, message)

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()

def unique(values, label):
    require(isinstance(values, list) and all(isinstance(v, str) and v for v in values), label)
    require(len(values) == len(set(values)), label + " duplicate")
    return set(values)

def build_scope(antenna_plan, counterparts, summary):
    """Accept exact authenticated derived inputs; never edit the antenna plan."""
    antenna = unique(antenna_plan["mutable_nets"], "antenna owners")
    protected = unique(antenna_plan["protected_nets"], "protected owners")
    attachments = antenna_plan["attachments"]
    require(isinstance(attachments, dict), "diode attachment map")
    exact(antenna, set(attachments.values()), "original diode ownership")
    require(len(antenna) == 608 and len(protected) == 1691 and len(attachments) == 1351,
            "original antenna/protected/diode census")
    exact(summary["status"], "COMPLETE_ORIGINAL_CLASS_COUNTERPART_JOIN", "actual join status")
    exact(summary["temporary_fixed_counterpart_nets"], 220, "actual counterpart census")
    exact(summary["temporary_fixed_counterpart_witnesses"], 448, "actual witness census")
    exact(summary["temporary_fixed_counterpart_markers"], 423, "actual marker census")
    require(summary["all_marker_and_witness_ordinals_retained"] is True, "full ordinal evidence")
    for key in ("route_mutation_authorized", "routing_executed", "physical_cause_proven", *FLAGS):
        require(summary[key] is False, "classification is not native authorization: " + key)
    require(isinstance(counterparts, list) and len(counterparts) == 220, "complete counterpart rows")
    extra = unique([row["net"] for row in counterparts], "counterpart owners")
    require(not (antenna & protected or extra & protected or extra & antenna), "disjoint signal scope")
    markers = set()
    witness_count = 0
    for row in counterparts:
        require(row["observed_class"] == "FIXED" and row["original_class"] == "ROUTED",
                "only temporary FIXED original ROUTED")
        require(row["route_mutation_authorized"] is False, "classifier authority unchanged")
        require(type(row["witness_count"]) is int and row["witness_count"] > 0
                and row["witness_count"] == len(row["witnesses"]), "complete counterpart witnesses")
        exact(sorted(set(w["source_marker_ordinal"] for w in row["witnesses"])),
              row["source_marker_ordinals"], "complete counterpart ordinals")
        exact(sorted(set(w["source_marker_index"] for w in row["witnesses"])),
              row["source_marker_indices"], "complete counterpart indices")
        markers.update(row["source_marker_ordinals"])
        witness_count += row["witness_count"]
    require(witness_count == 448 and len(markers) == 423, "full joined evidence census")
    return dict(schema="mainchip-separate-counterpart-routing-scope-v1",
                antenna_nets=sorted(antenna), counterpart_nets=sorted(extra),
                routing_nets=sorted(antenna | extra), protected_nets=sorted(protected),
                antenna_plan_sha256=digest(antenna_plan), counterparts_sha256=digest(counterparts),
                summary_sha256=digest(summary), attachment_count=len(attachments),
                native_execution_authorized=False, **FLAGS)

def validate_scope(scope, antenna_plan):
    antenna = unique(scope["antenna_nets"], "scope antenna")
    extra = unique(scope["counterpart_nets"], "scope counterpart")
    protected = unique(scope["protected_nets"], "scope protected")
    routing = unique(scope["routing_nets"], "scope routing")
    exact(scope["schema"], "mainchip-separate-counterpart-routing-scope-v1", "scope schema")
    exact(scope["antenna_plan_sha256"], digest(antenna_plan), "entire original antenna plan")
    exact(antenna, unique(antenna_plan["mutable_nets"], "original antenna"), "antenna scope equality")
    exact(protected, unique(antenna_plan["protected_nets"], "original protected"), "protected equality")
    exact(antenna, set(antenna_plan["attachments"].values()), "unmodified diode ownership")
    require(len(antenna) == 608 and len(extra) == 220 and len(protected) == 1691
            and scope["attachment_count"] == len(antenna_plan["attachments"]) == 1351,
            "scope complete census")
    require(not (antenna & extra or antenna & protected or extra & protected), "disjoint scope")
    exact(routing, antenna | extra, "routing union")
    for key in ("native_execution_authorized", *FLAGS):
        require(scope[key] is False, "scope is not authority or acceptance")
    return antenna, extra, protected, routing

def clear_delta(before, after, antenna_plan, scope, empty_wire_pin):
    antenna, extra, protected, routing = validate_scope(scope, antenna_plan)
    exact(sorted(before), sorted(after), "complete snapshot schema")
    for key in before:
        if key not in ("nets", "def_pin"):
            exact(after[key], before[key], "unchanged snapshot " + key)
    exact(sorted(after["nets"]), sorted(before["nets"]), "all net names")
    require(routing | protected <= set(before["nets"]), "known scoped nets")
    for name, old in before["nets"].items():
        new = after["nets"][name]
        if name not in routing:
            exact(new, old, "unowned net changed: " + name)
            continue
        require(old["identity"]["sigtype"] == "SIGNAL", "ordinary signal only: " + name)
        original_class = "ROUTED" if name in antenna else "FIXED"
        require(old["encoded"]["wire_present"] is True and old["wire"]["opcode_count"] > 0
                and old["encoded"]["metadata"] == original_class
                and set(old["encoded"]["paths"]) == {original_class}, "exact initial wire class: " + name)
        expected = copy.deepcopy(old)
        expected["encoded"].update(metadata="ROUTED", wire_present=False, paths=[])
        expected["wire"] = dict(pin=empty_wire_pin, opcode_count=0)
        exact(new, expected, "only scoped class transition and wire removal: " + name)
    return dict(complete=True, cleared_nets=sorted(routing),
                original_antenna_nets=len(antenna), additional_counterpart_nets=len(extra),
                all_nonmutable_exact=True, original_antenna_plan_preserved=True, **FLAGS)

def route_delta(inserted, restored, antenna_plan, scope, same_base):
    antenna, extra, protected, routing = validate_scope(scope, antenna_plan)
    same_base(inserted, restored)  # exact original complete physical validator
    exact(sorted(inserted), sorted(restored), "complete routed snapshot schema")
    for key in inserted:
        if key not in ("nets", "def_pin"):
            exact(restored[key], inserted[key], "unchanged routed snapshot " + key)
    exact(sorted(inserted["nets"]), sorted(restored["nets"]), "complete routed net census")
    require(routing | protected <= set(inserted["nets"]), "known routed scope")
    changed = []
    for name, old in inserted["nets"].items():
        new = restored["nets"][name]
        if name not in routing:
            exact(new, old, "unowned route changed: " + name)
            continue
        exact(new["identity"], old["identity"], "route identity: " + name)
        require(old["identity"]["sigtype"] == "SIGNAL", "ordinary routed signal")
        require(old["encoded"]["metadata"] == "ROUTED"
                and new["encoded"]["metadata"] == old["encoded"]["metadata"], "original restored metadata")
        require(new["encoded"]["wire_present"] is True and new["encoded"]["paths"]
                and set(new["encoded"]["paths"]) == {"ROUTED"}
                and new["wire"]["opcode_count"] > 0, "complete restored routing")
        if old["wire"] != new["wire"]:
            changed.append(name)
    # Every diode-bearing net still requires its original physical route change.
    require(antenna <= set(changed), "each diode owner must change")
    require(set(changed) <= routing, "only scoped route changes")
    return dict(changed_nets=sorted(changed), routing_scope=sorted(routing),
                changed_counterparts=sorted(set(changed) & extra),
                original_logic_placement_preserved=True, all_nonmutable_wires_exact=True,
                original_antenna_plan_preserved=True, **FLAGS)

def scoped_def_delta(before, after, owners, antenna_plan, scope, original):
    antenna, extra, protected, routing = validate_scope(scope, antenna_plan)
    exact(owners, dict(mutable=antenna_plan["mutable_nets"], selected=antenna_plan["protected_nets"]),
          "original full DEF caller ownership")
    return original(before, after, dict(mutable=sorted(routing), selected=sorted(protected)))

def observation_scope(antenna_plan, scope):
    """Transient selection for full route/connectivity observation, not a diode plan."""
    _, _, _, routing = validate_scope(scope, antenna_plan)
    result = copy.deepcopy(antenna_plan)
    result["mutable_nets"] = sorted(routing)
    # Attachments are intentionally unchanged; the original connectivity checker
    # still requires all 1351 diode pins plus all terminals of the 220 extra nets.
    return result
