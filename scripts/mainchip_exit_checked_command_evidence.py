#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only command evidence checks. Caller authenticates source, events and stream bytes."""
import math,re

SECONDS=(1200,14400)
MIN_AVAILABLE_KIB=2097152
MAX_GROUP_RSS_KIB=10485760
WINDOW=.10
STATES=frozenset("RSDZTtWXxKPI")
NONRUNNING=frozenset(("Z","X","x"))
TYPED_ERROR="ExhaustedMissingRSS('Persistent unavailable live VmRSS')"
ORIGINAL_ERROR="CounterError('Persistent unavailable live VmRSS')"

def require(condition,reason):
    if not condition:raise ValueError(reason)

def integer(value,minimum,reason):
    require(type(value)is int and value>=minimum,reason)
    return value

def finite(value,reason):
    require(type(value)in (int,float)and math.isfinite(value),reason)
    return value

def identity(value,pgid,reason):
    require(type(value)is dict,reason)
    integer(value["pid"],1,reason);integer(value["pgrp"],1,reason);integer(value["starttime"],0,reason)
    require(value["pgrp"]==pgid and type(value["state"])is str and value["state"]in STATES,reason)
    return (value["pid"],value["pgrp"],value["starttime"])

def disappearance(value,reason):
    require(type(value)is dict and value.get("type")in ("FileNotFoundError","ProcessLookupError")
      and value.get("errno")in (2,3)and type(value.get("errno"))is int,reason)

def status_evidence(observation,missing_file,reason):
    if missing_file:
        require("status_sha256"not in observation,reason)
        disappearance(observation["status_read_error"],reason)
    else:
        require("status_read_error"not in observation and type(observation.get("status_sha256"))is str
          and re.fullmatch("[0-9a-f]{64}",observation["status_sha256"])is not None,reason)

def histories(attempts,pgid):
    require(type(attempts)is list and len(attempts)==3,"exact three MissingRSS histories")
    known={};bounds=[]
    for number,attempt in enumerate(attempts,1):
        require(type(attempt)is dict and type(attempt["attempt"])is int and attempt["attempt"]==number
          and attempt["disposition"]=="retry_missing_live_counter","ordered MissingRSS history")
        require(attempt["enumeration_disappearances"]==[],"unknown resampling identity")
        available=integer(attempt["available_kib"],MIN_AVAILABLE_KIB,"observed available-memory limit")
        rows=attempt["enumerated"];observed=attempt["observations"]
        require(type(rows)is list and rows and type(observed)is list and 1<=len(observed)<=len(rows),
          "complete enumerated observation prefix")
        pids=[]
        for row in rows:
            key=identity(row,pgid,"enumerated process identity")
            require(row["state"]not in NONRUNNING,"nonlive enumerated process")
            require(key[0]not in known or known[key[0]]==key,"historical PID reuse")
            known[key[0]]=key;pids.append(key[0])
        require(pids==sorted(set(pids)),"duplicate or unordered enumerated PID")
        partial=0
        for index,obs in enumerate(observed):
            require(type(obs)is dict and obs["expected"]==rows[index],"observation/enumeration identity join")
            expected=identity(obs["expected"],pgid,"expected process identity")
            disposition=obs["disposition"]
            before=obs.get("before");after=obs.get("after")
            if before is not None:require(identity(before,pgid,"held before identity")==expected,"held before PID reuse")
            if after is not None:require(identity(after,pgid,"held after identity")==expected,"held after PID reuse")
            missing=disposition in ("missing_live_status_file","missing_live_VmRSS")
            require(missing==(index==len(observed)-1),"exact final MissingRSS observation")
            if missing or disposition=="measured_fresh":
                require(before is not None and after is not None
                  and before["state"]not in NONRUNNING and after["state"]not in NONRUNNING,
                  "counter requires same live identity")
                status_evidence(obs,disposition=="missing_live_status_file","counter status evidence")
                if missing:require("rss_kib"not in obs,"missing counter must not manufacture RSS")
                else:partial+=integer(obs["rss_kib"],0,"partial measured RSS")
            elif disposition in ("gone_before_held_directory","exited_before_first_held_stat"):
                require(before is None and after is None and "rss_kib"not in obs,"gone observation shape")
                disappearance(obs["disappearance_error"],"gone observation error")
            elif disposition=="exited_after_counter_read":
                require(before is not None and before["state"]not in NONRUNNING and after is None
                  and "rss_kib"not in obs,"exit-after-counter shape")
                status_evidence(obs,"status_read_error"in obs,"exit-after-counter status")
                disappearance(obs["disappearance_error"],"exit-after-counter error")
            elif disposition=="nonrunning_before_counter":
                require(before is not None and before["state"]in NONRUNNING and after is None
                  and "rss_kib"not in obs,"nonrunning-before shape")
            elif disposition=="nonrunning_after_counter":
                require(before is not None and before["state"]not in NONRUNNING
                  and after is not None and after["state"]in NONRUNNING and "rss_kib"not in obs,
                  "nonrunning-after shape")
                status_evidence(obs,"status_read_error"in obs,"nonrunning-after status")
            else:raise ValueError("unrecognized successful historical observation")
        require(partial<=MAX_GROUP_RSS_KIB,"observed partial RSS lower-bound limit")
        bounds.append(dict(attempt=number,available_kib=available,
          partial_group_rss_lower_bound_kib=partial,full_group_rss_measured=False))
    require(pgid in known,"owned group leader absent")
    return known,bounds

def census(value,known,pgid,final,gone_before):
    require(type(value)is dict and type(value["complete"])is bool
      and value["complete"]is final and type(value["scans"])is list
      and (len(value["scans"])==2 if final else 1<=len(value["scans"])<=2),
      "terminal identity scan completion")
    for index,scan in enumerate(value["scans"]):
        integer(scan["enumerated_count"],0,"terminal enumeration count")
        require(type(scan["live"])is list and scan["unknown"]==[],"terminal unknown identity")
        require(type(scan["group"])is list and type(scan["known_gone"])is list,"terminal census lists")
        group=[];live=[]
        for item in scan["group"]:
            pid=integer(item["pid"],1,"terminal group PID")
            require(pid in known and identity(item["before"],pgid,"terminal before identity")==known[pid]
              and identity(item["after"],pgid,"terminal after identity")==known[pid],"terminal PID reuse or unanchored member")
            if item["before"]["state"]not in NONRUNNING or item["after"]["state"]not in NONRUNNING:live.append(pid)
            group.append(pid)
        gone=[integer(pid,1,"terminal gone PID")for pid in scan["known_gone"]]
        require(group==sorted(set(group))and gone==sorted(set(gone))and not(set(group)&set(gone)),
          "terminal census duplicates")
        require(set(group)|set(gone)==set(known)and scan["enumerated_count"]>=len(group),
          "complete terminal known-identity coverage")
        require(all(type(pid)is int for pid in scan["live"])and scan["live"]==live,"terminal live identity replay")
        require(gone_before<=set(gone),"gone terminal PID reappeared")
        gone_before=set(gone)
        # The producer stops an incomplete census at the first known live group
        # member. It may poll again within the same original snapshot deadline.
        if final or index<len(value["scans"])-1:
            require(not live,"terminal completed scan remains live")
        else:require(bool(live),"incomplete census requires observed known live member")
    return gone_before

def sample_limits(sample):
    if sample is None:return
    require(type(sample)is dict,"last measured sample shape")
    integer(sample["available_kib"],MIN_AVAILABLE_KIB,"last measured available-memory limit")
    rss=integer(sample["group_rss_kib"],0,"last measured group RSS")
    require(rss<=MAX_GROUP_RSS_KIB,"last measured RSS limit")

def validate(record,seconds):
    """Validate one record, not a run. Declared timeout/argv and byte authentication remain caller gates."""
    require(type(seconds)is int and seconds in SECONDS,"supported original command budget")
    require(type(record)is dict,"command record object")
    require(type(record["returncode"])is int and record["returncode"]==0
      and record["supervision_failure"]is None,"successful original command")
    pid=integer(record["pid"],1,"owned command PID")
    require(type(record["minimum_available_kib"])is int and record["minimum_available_kib"]==MIN_AVAILABLE_KIB
      and type(record["maximum_group_rss_kib"])is int and record["maximum_group_rss_kib"]==MAX_GROUP_RSS_KIB,
      "unchanged original command resource limits")
    elapsed=finite(record["elapsed_seconds"],"finite command elapsed")
    require(elapsed>=0,"nonnegative command elapsed")
    declared="requested_timeout_seconds"in record
    if declared:
        require(type(record["requested_timeout_seconds"])is int and record["requested_timeout_seconds"]==seconds,
          "declared command budget differs")
    cleanup=record["process_group_cleanup"]
    require(type(cleanup)is dict and cleanup["signals"]==[]and cleanup["remaining_live"]==[],
      "command signalled or live cleanup")
    require(type(cleanup["remaining_nonrunning"])is list,"cleanup nonrunning list")
    for row in cleanup["remaining_nonrunning"]:
        integer(row["pid"],1,"cleanup nonrunning PID")
        require(row["state"]in NONRUNNING,"cleanup member still live")
    sample_limits(record["last_memory_sentinel_sample"])
    error=record["memory_read_error"];resolution=record["memory_terminal_resolution"]
    result=dict(status="PASS_EXIT_CHECKED_COMMAND_EVIDENCE",command_only=True,
      seconds=seconds,requested_timeout_recorded=declared,requested_timeout_bound=declared,
      retained_memory_read_error=error,terminal_resolution_validated=False,
      source_authenticated=False,event_authenticated=False,stream_bytes_authenticated=False,
      native_execution_performed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    if error is None:
        require(resolution is None,"ordinary command cannot carry terminal resolution")
        result["path"]="ordinary_no_memory_error"
        result["pre_cleanup_command_deadline_proved"]=False
        return result
    require(type(error)is str and error==TYPED_ERROR,"exact exhausted MissingRSS error")
    require(type(resolution)is dict and resolution["outcome"]=="terminal_complete"
      and "resolution_error"not in resolution,"successful terminal memory resolution")
    require(resolution["original_error"]==ORIGINAL_ERROR and resolution["original_memory_error"]==error,
      "retained original counter error")
    require(resolution["fresh_memory_sample"]is False and resolution["PF_EXITING_used_for_acceptance"]is False
      and resolution["cleanup_started"]is False and resolution["completed_before_cleanup"]is True,
      "pre-cleanup terminal proof without RSS substitution")
    require(type(resolution["parent_returncode"])is int and resolution["parent_returncode"]==0,
      "resolved parent returncode")
    require(type(resolution["minimum_available_kib"])is int and resolution["minimum_available_kib"]==MIN_AVAILABLE_KIB
      and type(resolution["maximum_group_rss_kib"])is int and resolution["maximum_group_rss_kib"]==MAX_GROUP_RSS_KIB,
      "terminal resource limits")
    known,bounds=histories(resolution["attempts"],pid)
    require(resolution["observed_resource_bounds_validated"]is True
      and resolution["observed_resource_bounds"]==bounds,"exact observed resource-bound replay")
    # Canonical JSON equality also refuses bool-for-int metadata substitutions.
    import json
    require(json.dumps(resolution["observed_resource_bounds"],sort_keys=True,allow_nan=False)==
      json.dumps(bounds,sort_keys=True,allow_nan=False),"typed observed resource-bound replay")
    began=finite(resolution["snapshot_began"],"finite snapshot start")
    deadline=finite(resolution["snapshot_deadline"],"finite snapshot deadline")
    finished=finite(resolution["finished_at"],"finite terminal finish")
    interval=finite(resolution["elapsed_from_snapshot_start_seconds"],"finite snapshot elapsed")
    require(type(resolution["total_budget_seconds"])in (int,float)and resolution["total_budget_seconds"]==WINDOW
      and deadline==began+WINDOW and began<=finished<=deadline and interval==finished-began,
      "original 100ms snapshot budget")
    polls=resolution["polls"]
    require(type(polls)is list and polls,"terminal poll history")
    last=began;gone=set();parent_completed=False
    for index,poll in enumerate(polls):
        at=finite(poll["at"],"finite terminal poll")
        require(last<=at<=finished,"ordered terminal poll clock");last=at
        if poll["parent_returncode"]is None:
            require(index<len(polls)-1 and not parent_completed and "census"not in poll,
              "uncompleted parent census")
        else:
            require(type(poll["parent_returncode"])is int and poll["parent_returncode"]==0,
              "stable completed parent returncode")
            parent_completed=True
            gone=census(poll["census"],known,pid,index==len(polls)-1,gone)
    require("command_budget_decision"in resolution,"strict command deadline proof missing")
    budget=resolution["command_budget_decision"]
    require(type(budget)is dict and budget["status"]=="checked"and budget["clock"]=="time.monotonic"
      and budget["within_limit"]is True,"checked strict command deadline")
    for key in ("began","observed_at","deadline","limit_seconds","elapsed_seconds"):
        finite(budget[key],"finite command budget decision")
    require(type(budget["limit_seconds"])is int and budget["limit_seconds"]==seconds
      and budget["began"]<=began<=finished<=budget["observed_at"]
      and budget["deadline"]==budget["began"]+seconds
      and budget["elapsed_seconds"]==budget["observed_at"]-budget["began"]
      and 0<=budget["elapsed_seconds"]<seconds and budget["observed_at"]<budget["deadline"]
      and elapsed>=budget["elapsed_seconds"],"original strict command budget arithmetic")
    result.update(path="resolved_exhausted_MissingRSS",terminal_resolution_validated=True,
      pre_cleanup_command_deadline_proved=True,observed_attempts=3,terminal_identity_scans=2,
      snapshot_budget_seconds=WINDOW,last_sample_reclassified_as_fresh=False)
    return result
