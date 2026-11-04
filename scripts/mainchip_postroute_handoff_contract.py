"""Exact restored-route and exported netlist admission; never a timing/LVS verdict."""
import re
WIRE_SYNTAX = re.compile(rb'\+\s+(ROUTED|FIXED|COVER)\b')

def need(ok, message):
    if not ok:
        raise ValueError(message)

def restoration(before, after, baseline, expected_def_pin):
    need(set(before) == set(after), "complete snapshot schema")
    for key in before:
        if key not in ("nets", "def_pin", "clock_record_pins"):
            need(before[key] == after[key], "unchanged native section " + key)
    # Protected clock records carry the temporary FIXED class in the candidate,
    # so restoring classes must change them, and only back to the baseline.
    need(set(after["clock_record_pins"]) == set(baseline["clock_record_pins"]) == set(before["clock_record_pins"]), "protected clock record census")
    need(after["clock_record_pins"] == baseline["clock_record_pins"], "original complete protected clock records")
    restored_clocks = sorted(n for n, pin in before["clock_record_pins"].items() if pin != after["clock_record_pins"][n])
    need(after["def_pin"] == expected_def_pin, "complete expected restored DEF")
    need(set(before["nets"]) == set(after["nets"]) == set(baseline["nets"]), "complete net census")
    changed = []
    for name, old in before["nets"].items():
        new = after["nets"][name]
        need(old["identity"] == new["identity"], "all terminals and net attributes " + name)
        need(new["encoded"] == baseline["nets"][name]["encoded"], "original route metadata/classes " + name)
        if old["encoded"] == new["encoded"]:
            need(old["wire"] == new["wire"], "unmodified wire opcode stream " + name)
        else:
            changed.append(name)
    return dict(restored_class_nets=changed, restored_clock_records=restored_clocks, unchanged_instances=True,
                exact_full_DEF=True, all_original_route_classes=True,
                physical_acceptance=False, timing_accepted=False, full_phy_accepted=False)

def pg(instances, template, baseline_names):
    added = sorted(set(instances) - set(baseline_names))
    need(bool(added), "nonempty actual added diode census")
    for name in added:
        row = instances[name]
        need(row["master"] == template["master"] and row["master"][1] == "sg13g2_antennanp", "only actual diode additions")
        need(set(row["pins"]) == set(template["pins"]), "all diode terminals")
        for pin, value in row["pins"].items():
            if pin == "A":
                need(value["net"] is not None and value["sigtype"] == "SIGNAL" and value["io"] == "INPUT", "connected diode signal")
            else:
                need(value == template["pins"][pin] and value["net"] is not None and value["sigtype"] in ("POWER", "GROUND"), "exact diode supply binding")
    return dict(added_diodes=added, logical_supply_bindings_verified=True,
                physical_supply_connectivity_verified=False)

def topology(before, after):
    need(set(before) == set(after) == {"top", "instances", "ports", "nets"}, "netlist topology schema")
    need(before["top"] == after["top"], "exact top")
    need(before["instances"] == after["instances"], "all masters and all instance pin nets including diode PG")
    need(before["ports"] == after["ports"], "all boundary terminals")
    # Netlists need not serialize unused declarations, but every connected net
    # and its complete incidence must survive. No connected net may be dropped.
    def connected(value):
        return {name: row for name, row in value["nets"].items() if row["iterms"] or row["bterms"]}
    need(connected(before) == connected(after), "complete connected-net incidence")
    return dict(instances=len(before["instances"]), ports=len(before["ports"]),
                connected_nets=len(connected(before)),
                unused_nets_before=sorted(set(before["nets"]) - set(connected(before))),
                unused_nets_after=sorted(set(after["nets"]) - set(connected(after))),
                all_instance_and_boundary_connections_equal=True,
                full_LVS_accepted=False, timing_accepted=False, full_phy_accepted=False)

def wire_class(c, record):
    """Original class of one NETS record; None only for a record with no wire syntax at all.

    Same rule as the frozen fixed_overlay: a record without a line-start route
    clause is wireless only if no other ROUTED/FIXED/COVER syntax is present.
    More than one clause still fails inside the frozen classes().
    """
    if not c.ROUTE.search(record):
        need(not WIRE_SYNTAX.search(record), "unsupported wire syntax")
        return None
    return c.classes(record)

def wire_census(c, records):
    wireless, single, multiple, unsupported = [], 0, {}, []
    for name, record in records.items():
        count = len(c.ROUTE.findall(record))
        if count == 1:
            single += 1
        elif count > 1:
            multiple[name] = count
        elif WIRE_SYNTAX.search(record):
            unsupported.append(name)
        else:
            wireless.append(name)
    return dict(records=len(records), single_clause=single, wireless=len(wireless),
                wireless_names=sorted(wireless), multiple_clause=multiple,
                unsupported_syntax=sorted(unsupported))
