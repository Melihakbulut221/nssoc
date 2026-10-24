#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only crossing order and voltage competition; no current or cause inference."""
import copy, hashlib, json, math
import numpy as np
import cloud_pll_first_latch_cache_replay as frozen

THRESHOLDS = (0.0, 0.01)
MAP_SHA = "d405e7125ae9b838dc258d65ccfc91c03d0f3e9e03ccaed59a741dfb75058df5"
DIAG_SHA = "c7e6892a2e8a615a2970273c1d145457fa1e216a77185a1be84577fd33473f8c"
SIGNALS = ("clock_hold_v", "clock_hold_effective_v", "data_v", "data_effective_v",
           "hold_v", "hold_effective_v", "output_v")
ROLES = {392:"master_hold_clock",393:"master_sample_clock",394:"master_hold_MP_branch",
         395:"master_data_MP_branch",396:"master_data_MN_branch",400:"master_hold_MN_branch"}

def digest(value):
    return hashlib.sha256((json.dumps(value,indent=2)+"\n").encode()).hexdigest()

def vectors(data,mapping):
    assert digest(mapping)==MAP_SHA
    byid={r["native_id"]:r for r in mapping["devices"]}
    for i,role in ROLES.items():
        assert byid[i]["role"]==role and byid[i]["model"]=="npn13G2"
    names={}
    for i in ROLES:
        for terminal in ("B","E","C"):
            item=next(x for x in byid[i]["terminals"]if x["terminal"]==terminal)
            assert item["unit"]=="voltage" and item["vector"]==f"v(xloop.w_t{i}_{terminal.lower()})"
            assert item["vector"] in data
            names[f"T{i}_{terminal}"]=item["vector"]
    V=lambda i,t:data[names[f"T{i}_{t}"]]
    be=lambda i:V(i,"B")-V(i,"E")
    # Collector terminals with the same schematic net are not interchangeable after RC.
    # MP producer=T394_C, MN producer=T396_C; regenerative sinks=T400_B/T394_B.
    s=dict(clock_hold_v=V(392,"B")-V(393,"B"),
      clock_hold_effective_v=be(392)-be(393),data_v=V(396,"B")-V(395,"B"),
      data_effective_v=be(396)-be(395),hold_v=V(400,"B")-V(394,"B"),
      hold_effective_v=be(400)-be(394),output_v=V(394,"C")-V(396,"C"))
    return s,{k:data[v]for k,v in names.items()},names

def validate_series(t,signals):
    assert t.ndim==1 and len(t)>=2 and np.isfinite(t).all() and np.all(np.diff(t)>0)
    assert set(signals)==set(SIGNALS)
    assert all(v.shape==t.shape and np.isfinite(v).all()for v in signals.values())

def edges(t,y,threshold):
    assert threshold in THRESHOLDS
    f=frozen.old.crossing if threshold==0 else lambda tt,yy:frozen.old.hysteresis(tt,yy,threshold)
    return {"rising":np.asarray(f(t,y)),"falling":np.asarray(f(t,-y))}

def event(t,x,kind,signals,native):
    q=frozen.sampling.native_snapshot(t,x,signals,kind)
    rows=q["bracketing_rows"]
    # Values below are original native samples, not a resampled waveform.
    q["native_endpoints"]=[dict(row=i,time_s=float(t[i]),
       signals={k:float(v[i])for k,v in signals.items()},
       terminals_v={k:float(v[i])for k,v in native.items()})for i in rows]
    return q

def ordering(first,second):
    a=first["native_times_s"];b=second["native_times_s"]
    if a[-1]<b[0]:return "before_separate_native_brackets"
    if b[-1]<a[0]:return "after_separate_native_brackets"
    if len(a)==len(b)==1 and a[0]==b[0]:return "same_native_sample"
    return "overlapping_native_brackets_order_unresolved"

def match_controls(rows):
    good=[i for i,r in enumerate(rows)if r["output_transitions"]==1]
    assert good
    matches=[]
    for i,r in enumerate(rows):
        if r["output_transitions"]==1:continue
        k=int(np.searchsorted(good,i))
        before=good[k-1]if k else None
        after=good[k]if k<len(good)else None
        matches.append(dict(anomalous_index=i,preceding_clean_index=before,
                            following_clean_index=after,
                            matching_rule="nearest ordinal on each side; no voltage or outcome fitting"))
    return matches

def sign_competition(t,signals,a,b,sign):
    """Voltage-only observations; never treats a VBE sign as a current measurement."""
    assert sign in (-1,1)and t[0]<=a<=b<=t[-1]
    lo=int(np.searchsorted(t,a,"left"));hi=int(np.searchsorted(t,b,"right"))
    tt=t[lo:hi]
    # Data requests the eventual output sign; hold still regenerates its old sign;
    # effective clock steering voltage favors hold. No fitted voltage threshold.
    mask=((sign*signals["data_effective_v"][lo:hi]>0)&
          (sign*signals["hold_effective_v"][lo:hi]<0)&
          (signals["clock_hold_effective_v"][lo:hi]>0))
    paired=mask[:-1]&mask[1:]
    indices=np.flatnonzero(mask)+lo
    return dict(window_s=[float(a),float(b)],native_rows_considered=int(hi-lo),
      matching_native_rows=int(mask.sum()),
      first_matching_row=int(indices[0])if len(indices)else None,
      last_matching_row=int(indices[-1])if len(indices)else None,
      adjacent_matching_endpoint_pairs=int(paired.sum()),
      adjacent_matching_endpoint_span_s=float(np.diff(tt)[paired].sum())if len(tt)>1 else 0.,
      continuous_behavior_between_samples_proved=False,
      sample_path_current_overlap_proved=False)

def analyze_series(t,signals,native,clock,master_rises,master_falls,expected):
    validate_series(t,signals)
    for values in native.values():assert values.shape==t.shape and np.isfinite(values).all()
    output=edges(t,signals["output_v"],.01)
    assert np.array_equal(output["rising"],master_rises)
    assert np.array_equal(output["falling"],master_falls)
    rows=frozen.events.relation(clock,master_rises,master_falls)
    histogram={}
    for row in rows:
        key=str(row["output_transitions"]);histogram[key]=histogram.get(key,0)+1
    assert len(rows)==expected["complete_input_intervals"]
    assert histogram==expected["transition_count_histogram"]
    actual_bad=[r for r in rows if r["output_transitions"]!=1]
    assert actual_bad==[{k:r[k]for k in ("interval_s","output_rises","output_falls","output_transitions")}
                       for r in expected["anomalous_intervals"]]
    matches=match_controls(rows)
    selected=sorted({m[k]for m in matches for k in
      ("anomalous_index","preceding_clean_index","following_clean_index")if m[k]is not None})
    # Compute fixed event lists once. No per-cycle threshold fit or waveform slicing.
    related={(name,h):edges(t,signals[name],h)for name in ("data_v","hold_v")for h in THRESHOLDS}
    observations=[];event_count=0
    for i in selected:
        row=rows[i];a,b=row["interval_s"]
        # Include one complete adjacent input interval on each side to expose causal order.
        wa=float(clock[max(0,i-1)]);wb=float(clock[min(len(clock)-1,i+2)])
        output_events=sorted([(float(x),kind)for kind,es in output.items()
          for x in es[np.searchsorted(es,a,"left"):np.searchsorted(es,b,"left")]])
        rec=dict(index=i,class_name="one_transition_control"if row["output_transitions"]==1 else
                 "anomalous_interval_not_individually_labelled_extra",**row,
                 observation_window_s=[wa,wb],events=[])
        for x,kind in output_events:
            sign=1 if kind=="rising"else-1
            q=event(t,x,kind,signals,native);q["related_crossings"]=[]
            for (name,h),table in related.items():
                # Preserve both directions, not only a cherry-picked same-sign predecessor.
                for direction,es in table.items():
                    for y in es[np.searchsorted(es,wa,"left"):np.searchsorted(es,wb,"left")]:
                        z=event(t,float(y),direction,{name:signals[name]},{})
                        q["related_crossings"].append(dict(signal=name,threshold_v=h,
                          same_direction=(direction==kind),event=z,
                          interpolated_delay_to_output_s=x-float(y),
                          native_bracket_order=ordering(z,q)))
            q["related_crossings"].sort(key=lambda z:(z["event"]["time_s"],z["signal"],z["threshold_v"],z["event"]["kind"]))
            q["pretransition_voltage_competition"]=sign_competition(t,signals,wa,x,sign)
            candidates=[z for z in q["related_crossings"]if z["signal"]=="data_v" and
                        z["threshold_v"]==0 and z["same_direction"]]
            nearest=min(candidates,key=lambda z:(abs(z["interpolated_delay_to_output_s"]),
                        z["event"]["time_s"]))if candidates else None
            q["nearest_same_direction_data_zero_crossing"]=(dict(
              time_s=nearest["event"]["time_s"],
              interpolated_delay_to_output_s=nearest["interpolated_delay_to_output_s"],
              native_bracket_order=nearest["native_bracket_order"],
              matching_rule="minimum absolute time distance within fixed observation window; earlier tie",
              causally_corresponding_edge_proved=False)if nearest else None)
            q["individual_extra_transition_identified"]=False
            rec["events"].append(q);event_count+=1
        assert len(rec["events"])==row["output_transitions"]
        observations.append(rec)
    comparison={}
    for category in ("anomalous_interval_not_individually_labelled_extra","one_transition_control"):
        chosen=[e for row in observations if row["class_name"]==category for e in row["events"]]
        orders={}
        for e in chosen:
            nearest=e["nearest_same_direction_data_zero_crossing"]
            key=nearest["native_bracket_order"]if nearest else "no_matching_edge_in_fixed_window"
            orders[key]=orders.get(key,0)+1
        comparison[category]=dict(events=len(chosen),nearest_data_zero_crossing_order=orders,
          positive_effective_hold_clock_events=sum(e["signals"]["clock_hold_effective_v"]>0 for e in chosen),
          voltage_competition_observed_before_event=sum(
            e["pretransition_voltage_competition"]["matching_native_rows"]>0 for e in chosen))
    return dict(comparison=comparison,
      scope="Existing native voltage observations only; no current, cause, acceptance or repaired circuit.",
      fixed_input_threshold_v=.01,related_crossing_thresholds_v=list(THRESHOLDS),
      original_complete_intervals=len(rows),original_transition_histogram=histogram,
      matched_controls=matches,observed_intervals=observations,output_events_observed=event_count,
      all_anomalous_intervals_retained=len(actual_bad)==len(matches),
      control_reuse_allowed_and_visible=True,
      ordering_with_overlapping_native_brackets="unresolved, never forced",
      fifty_mV_interval_caveat="No50mV input binning: it can merge many nominal clock cycles.",
      individual_HBT_current_inferred=False,causal_hypothesis_proved=False,
      acquisition_accepted=False,full_device_safety_accepted=False,full_phy_accepted=False)

def analyze(data,mapping,diagnosis,original):
    assert digest(diagnosis)==DIAG_SHA
    assert diagnosis["acquisition_accepted"]is diagnosis["full_phy_accepted"]is False
    assert diagnosis["device_current_observation_available"]is False
    t=np.array(data["time"],dtype="<f8",copy=True)
    assert np.array_equal(t.view("<u8"),data["time"].view("<u8"))
    assert len(t)==3201410 and t[0]==0 and t[-1]==1e-6
    signals,native,names=vectors(data,mapping)
    clock=np.asarray(original["differential"]["div1_first_conditioned"]["rising_edges_s"]["hysteresis_10mV"])
    my=original["differential"]["div1_first_master"]
    assert my["p_vector"]=="v(xloop.w_t394_c)"and my["n_vector"]=="v(xloop.w_t396_c)"
    rises=np.asarray(my["rising_edges_s"]["hysteresis_10mV"])
    falls=frozen.old.hysteresis(t,-signals["output_v"],.01)
    expected=diagnosis["master_events"]["hysteresis_10mV"]
    assert expected["complete_input_intervals"]==8648
    assert expected["transition_count_histogram"]=={"1":8489,"2":159}
    result=analyze_series(t,signals,native,clock,rises,falls,expected)
    result["native_terminal_vectors"]=names
    result["original_diagnosis_sha256"]=DIAG_SHA
    result["status"]="PASS_EXISTING_CAPTURE_CROSSING_ORDER_DIAGNOSIS_NOT_CAUSE_OR_REPAIR"
    return result
