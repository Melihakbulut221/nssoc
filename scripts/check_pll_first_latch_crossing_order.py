#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud fixtures with independently specified edges, matching and sign predicates."""
import copy
import numpy as np
import pll_first_latch_crossing_order as a

def controls():
    t=np.arange(17,dtype="<f8")
    y=np.array([-.02]*3+[.02]*2+[-.02]*2+[.02]*2+[-.02]*4+[.02]*4)
    assert len(y)==17
    signals=dict(clock_hold_v=t*0+.04,clock_hold_effective_v=t*0+.03,
      data_v=np.r_[y[1:],y[-1]],data_effective_v=np.r_[y[1:],y[-1]],
      hold_v=np.r_[y[0],y[:-1]],hold_effective_v=np.r_[y[0],y[:-1]],output_v=y)
    clock=np.array([0.,4.,8.,12.,16.]);up=np.array([2.75,6.75,12.75]);down=np.array([4.75,8.75])
    badrow=dict(interval_s=[4.,8.],output_rises=1,output_falls=1,output_transitions=2)
    expected=dict(complete_input_intervals=4,transition_count_histogram={"1":3,"2":1},
                  anomalous_intervals=[badrow])
    q=a.analyze_series(t,signals,{},clock,up,down,expected)
    assert [(m["anomalous_index"],m["preceding_clean_index"],m["following_clean_index"])
            for m in q["matched_controls"]]==[(1,0,2)]
    assert [r["index"]for r in q["observed_intervals"]]==[0,1,2]
    assert [[e["time_s"]for e in r["events"]]for r in q["observed_intervals"]]==[[2.75],[4.75,6.75],[8.75]]
    assert q["output_events_observed"]==4
    first=q["observed_intervals"][0]["events"][0]
    actual={(z["signal"],z["threshold_v"]):[]for z in first["related_crossings"]}
    for z in first["related_crossings"]:
        actual[z["signal"],z["threshold_v"]].append((z["event"]["time_s"],z["event"]["kind"]))
    assert actual=={
      ("data_v",0.):[(1.5,"rising"),(3.5,"falling"),(5.5,"rising"),(7.5,"falling")],
      ("data_v",.01):[(1.75,"rising"),(3.75,"falling"),(5.75,"rising"),(7.75,"falling")],
      ("hold_v",0.):[(3.5,"rising"),(5.5,"falling"),(7.5,"rising")],
      ("hold_v",.01):[(3.75,"rising"),(5.75,"falling"),(7.75,"rising")]}
    n=first["nearest_same_direction_data_zero_crossing"]
    assert n["time_s"]==1.5 and n["interpolated_delay_to_output_s"]==1.25
    assert n["native_bracket_order"]=="overlapping_native_brackets_order_unresolved"
    assert n["causally_corresponding_edge_proved"]is False
    assert all(v["nearest_data_zero_crossing_order"]==
      {"overlapping_native_brackets_order_unresolved":2}for v in q["comparison"].values())
    # Exercise the exact independently pinned native-role map with transparent integer
    # values. These arbitrary arithmetic fixtures are not a voltage simulation.
    import json
    mapping=json.loads((a.frozen.ROOT/a.frozen.original.MAP).read_text())
    fake={"time":t}
    for item in mapping["devices"]:
        if item["native_id"]not in a.ROLES:continue
        i=item["native_id"]
        for term in item["terminals"]:
            if term["terminal"]in ("B","C","E"):
                fake[term["vector"]]=t*0+i*{"B":17,"C":23,"E":5}[term["terminal"]]
    vs,raw,names=a.vectors(fake,mapping)
    want=dict(clock_hold_v=-17,clock_hold_effective_v=-12,data_v=17,
              data_effective_v=12,hold_v=102,hold_effective_v=72,output_v=-46)
    assert all(np.array_equal(vs[k],t*0+v)for k,v in want.items())
    assert len(raw)==len(names)==18
    # Independent affine snapshot oracle covers actual samples and intervening events.
    sig={k:2*t+1 for k in a.SIGNALS}
    for x in (0.,.25,1.,2.75,16.):
        e=a.event(t,x,"rising",sig,{"native_B":3*t-2})
        assert all(v==2*x+1 for v in e["signals"].values())
        for row in e["native_endpoints"]:
            i=row["row"];assert row["time_s"]==t[i] and row["terminals_v"]["native_B"]==3*t[i]-2
    def ev(ts):return {"native_times_s":ts}
    assert a.ordering(ev([0.,1.]),ev([2.,3.]))=="before_separate_native_brackets"
    assert a.ordering(ev([2.,3.]),ev([0.,1.]))=="after_separate_native_brackets"
    assert a.ordering(ev([1.]),ev([1.]))=="same_native_sample"
    assert a.ordering(ev([0.,1.]),ev([1.,2.]))=="overlapping_native_brackets_order_unresolved"
    # Both sign polarities have the same known mask [T,T,F,T,T].
    st=np.arange(5,dtype=float);drive=np.array([1.,1.,-1.,1.,1.])
    for sign in (1,-1):
        ss={"data_effective_v":sign*drive,"hold_effective_v":st*0-sign,
            "clock_hold_effective_v":st*0+1}
        z=a.sign_competition(st,ss,0.,4.,sign)
        assert z["matching_native_rows"]==4 and z["adjacent_matching_endpoint_pairs"]==2
        assert z["adjacent_matching_endpoint_span_s"]==2.
        assert z["first_matching_row"]==0 and z["last_matching_row"]==4
        assert not z["sample_path_current_overlap_proved"] and not z["continuous_behavior_between_samples_proved"]
    # Deterministic nearest controls, including repeated controls and edge anomalies.
    rr=[{"output_transitions":n}for n in (2,1,2,2,1,2)]
    mm=a.match_controls(rr)
    assert [(m["anomalous_index"],m["preceding_clean_index"],m["following_clean_index"])
            for m in mm]==[(0,None,1),(2,1,4),(3,1,4),(5,4,None)]
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):rejected.append(label)
        else:raise AssertionError("Accepted crossing-order corruption "+label)
    def run(tt=t,ss=signals,cc=clock,uu=up,dd=down,ee=expected):
        return a.analyze_series(tt,ss,{},cc,uu,dd,ee)
    for label,index,value in (("nan-time",3,np.nan),("duplicate-time",3,2.),("backward-time",3,-1.)):
        tt=t.copy();tt[index]=value;reject(label,lambda tt=tt:run(tt=tt))
    ss=copy.deepcopy(signals);ss["hold_v"][4]=np.inf
    reject("nonfinite-voltage",lambda:run(ss=ss))
    short={k:v[:-1]for k,v in signals.items()}
    reject("short-signal",lambda:run(ss=short))
    missing={k:v for k,v in signals.items()if k!="hold_v"}
    reject("missing-effective-or-native-pair",lambda:run(ss=missing))
    reject("wrong-clock-order",lambda:run(cc=clock[::-1]))
    reject("wrong-rise",lambda:run(uu=up+.1))
    reject("wrong-fall",lambda:run(dd=down+.1))
    reverse=copy.deepcopy(signals);reverse["output_v"]=-y
    reject("reversed-producer-polarity",lambda:run(ss=reverse))
    for label,change in (
        ("wrong-complete-census",lambda e:e.__setitem__("complete_input_intervals",3)),
        ("wrong-histogram",lambda e:e.__setitem__("transition_count_histogram",{"1":4})),
        ("lost-anomaly",lambda e:e["anomalous_intervals"].clear()),
        ("wrong-interval",lambda e:e["anomalous_intervals"][0].__setitem__("interval_s",[5.,8.])),
        ("wrong-direction-census",lambda e:e["anomalous_intervals"][0].__setitem__("output_rises",2))):
        ee=copy.deepcopy(expected);change(ee);reject(label,lambda ee=ee:run(ee=ee))
    reject("fitted-threshold",lambda:a.edges(t,y,.05))
    reject("invalid-competition-sign",lambda:a.sign_competition(t,signals,0.,1.,0))
    reject("competition-outside-capture",lambda:a.sign_competition(t,signals,-1.,1.,1))
    reject("reversed-competition-window",lambda:a.sign_competition(t,signals,2.,1.,1))
    reject("no-clean-match",lambda:a.match_controls([{"output_transitions":2}]))
    assert len(rejected)==20,len(rejected)
    return dict(status="PASS_FIXED_CROSSING_ORDER_AND20_FAULTS_NO_NATIVE_DATA",
      rejected=rejected,independent_expected_edges=True,both_sign_polarities=True,
      exact_and_interpolated_native_brackets=True,nearest_control_edges_and_reuse=True,
      native_cache_read=False,native_simulation_started=False,full_phy_accepted=False)
