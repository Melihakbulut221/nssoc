#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline metadata joins; execute only in cloud source-controls."""
import copy,json,unittest
import mainchip_drt_counterpart_scope as c

def fixture():
    originals=dict(T="ROUTED",P="ROUTED",F="FIXED",C="COVER",U=None,G=None)
    plan=dict(mutable_nets=["A"],protected_nets=["P"],added_instances=["D"],attachments={"D":"A"},
              physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    endpoints=[]
    for n in("A","T","P","F","C","U","G"):
        wire=n in("T","P","F","C")
        endpoints.append(dict(name=n,signal_type="POWER"if n=="G"else"SIGNAL",
          manifest_membership="mutable_cleared_manifest"if n=="A"else"protected_manifest"if n=="P"else"not_in_either_manifest",
          encoded_class_counts={"FIXED":1}if wire else{},encoded_wire_present=wire,
          route_metadata="FIXED"if wire else"ROUTED"))
    eps={e["name"]:e for e in endpoints}
    markers=[];witnesses=[];total={}
    for i,n in enumerate(("T","P","F","C","U","G")):
        rows=[]
        for j,owner in enumerate((n,"A")):
            ep=eps[owner];wire=owner in("T","P","F","C");special=owner=="G"
            kind="wire"if wire else"special-wire"if special else"iterm-pin"
            layer="Metal2"if wire or special else"Metal1"
            group="ordinary-wire-FIXED"if wire else"special-PG"if special else"iterm-pin"
            row=dict(source_marker_index=i,source_marker_ordinal=i,source_witness_index=j,owner=owner,
              other_endpoint="A"if owner!="A"else n,manifest_membership=ep["manifest_membership"],
              signal_type=ep["signal_type"],record_id=["fixture",owner,i],kind=kind,layer=layer,
              relation=dict(closed_intersection=True,positive_area_intersection=True),
              layer_relation="same_layer"if layer=="Metal2"else"xy_projection_only_different_layer",
              evidence_group=group,source_pointer="/markers/"+str(i)+"/endpoint_witnesses/"+str(j),
              details=dict(route_metadata="FIXED",encoded_class_counts={"FIXED":1})if wire else{})
            rows.append(row)
        groups={}
        for row in rows:
            g="|".join((row["manifest_membership"],row["evidence_group"],row["layer_relation"],"positive-area"))
            groups[g]=groups.get(g,0)+1;total[g]=total.get(g,0)+1
        markers.append(dict(source_marker_index=i,ordinal=i,nets=[n,"A"],layer="Metal2",
          endpoint_membership={k:eps[k]["manifest_membership"]for k in(n,"A")},
          all_witnesses=2,evidence_groups=groups,witnesses_by_owner={n:1,"A":1},no_observed_endpoint_intersection=False))
        witnesses+=rows
    summary=dict(status="COMPLETE_AUTHENTICATED_PREROUTE_OBSTACLE_REDUCTION",
      all_source_marker_and_witness_records_retained=True,complete_input_sha256_verified=True,
      endpoints=7,selected_markers=6,other_marker_records=1,complete_witness_records=12,
      endpoint_membership_counts=dict(mutable_cleared_manifest=1,protected_manifest=1,not_in_either_manifest=5),
      evidence_groups=total,**{k:False for k in("physical_acceptance","timing_accepted","full_phy_accepted","routing_executed","physical_cause_proven","iteration10_mutable_routes_present")})
    expected=dict(mutable=1,protected=1,diodes=1,original_classes=6,all_nets=7,endpoints=7,markers=6,other_markers=1,witnesses=12)
    return [summary,endpoints,markers,witnesses,[dict(ordinal=6,kind="Spacing")],originals,plan,expected]
class Controls(unittest.TestCase):
    def test_all_classifications_and_full_records(self):
        f=fixture();before=copy.deepcopy(f);r=c.classify(*f)
        self.assertEqual(f,before)
        self.assertEqual(r["result"]["temporary_fixed_counterpart_nets"],1)
        self.assertEqual(r["counterparts"][0]["net"],"T")
        self.assertEqual(r["counterparts"][0]["source_marker_ordinals"],[0])
        self.assertEqual([x["source"]for x in r["endpoints"]],f[1])
        self.assertEqual([x["source"]for x in r["markers"]],f[2])
        self.assertEqual([x["source"]for x in r["witnesses"]],f[3])
        self.assertEqual(r["other_markers"],f[4])
        self.assertEqual(set(x["classification"]for x in r["endpoints"]),{"mutable_cleared","temporary_fixed_original_routed","protected_keep","original_fixed_keep","original_cover_keep","original_unwired_keep","power_ground_keep_special"})
        for k in c.FLAGS:self.assertIs(r["result"][k],False)
        self.assertTrue(all(x["route_mutation_authorized"]is False for x in r["endpoints"]+r["witnesses"]+r["counterparts"]))
    def reject(self,change):
        f=fixture();change(f)
        with self.assertRaises((ValueError,KeyError)):c.classify(*f)
    def test_scope_acceptance_refused(self):
        for k in("physical_acceptance","timing_accepted","full_phy_accepted","routing_executed","physical_cause_proven","iteration10_mutable_routes_present"):
            with self.subTest(k=k):self.reject(lambda f:f[0].update({k:True}))
    def test_original_classes_refused(self):
        changes=[
          lambda f:f[5].pop("T"),
          lambda f:f[5].update(T="UNKNOWN"),
          lambda f:f[5].update(T=True),
          lambda f:f[5].update(T=None),
          lambda f:f[5].update(A="ROUTED"),
          lambda f:f[5].update({"":None}),
          lambda f:f[1][1].update(route_metadata="ROUTED"),
          lambda f:f[1][1].update(encoded_class_counts={"ROUTED":1}),
          lambda f:f[1][1].update(encoded_wire_present=False),
          lambda f:f[1][1].update(encoded_class_counts={"FIXED":True}),
          lambda f:f[1][5].update(encoded_class_counts={"FIXED":1},encoded_wire_present=True),
        ]
        for i,change in enumerate(changes):
            with self.subTest(i=i):self.reject(change)
    def test_membership_and_plan_refusals(self):
        changes=[
          lambda f:f[6]["protected_nets"].append("A"),
          lambda f:f[6]["mutable_nets"].append("A"),
          lambda f:f[6]["attachments"].update(D="T"),
          lambda f:f[6].update(added_instances=[]),
          lambda f:f[1][0].update(manifest_membership="not_in_either_manifest"),
          lambda f:f[1][2].update(manifest_membership="not_in_either_manifest"),
          lambda f:f[1].append(copy.deepcopy(f[1][0])),
          lambda f:f[1][0].update(encoded_wire_present=True,encoded_class_counts={"ROUTED":1}),
          lambda f:f[6].update(physical_acceptance=True),
        ]
        for i,change in enumerate(changes):
            with self.subTest(i=i):self.reject(change)
    def test_marker_and_witness_refusals(self):
        changes=[
          lambda f:f[2][0].update(ordinal=1),
          lambda f:f[4][0].update(ordinal=0),
          lambda f:f[3].pop(),
          lambda f:f[3][0].update(source_witness_index=1),
          lambda f:f[3][0].update(source_marker_ordinal=1),
          lambda f:f[3][0].update(source_pointer="/markers/0/endpoint_witnesses/9"),
          lambda f:f[3][0].update(owner="P"),
          lambda f:f[3][0].update(other_endpoint="T"),
          lambda f:f[3][0].update(layer_relation="xy_projection_only_different_layer"),
          lambda f:f[3][0].update(evidence_group="iterm-pin"),
          lambda f:f[3][0]["details"].update(route_metadata="ROUTED"),
          lambda f:f[3][0]["relation"].update(closed_intersection=False),
          lambda f:f[2][0].update(all_witnesses=3),
          lambda f:f[2][0].update(witnesses_by_owner={"T":2}),
          lambda f:f[2][0].update(no_observed_endpoint_intersection=True),
          lambda f:f[0].update(evidence_groups={}),
          lambda f:f[0].update(endpoint_membership_counts={}),
          lambda f:f[2][0].update(endpoint_membership={}),
        ]
        for i,change in enumerate(changes):
            with self.subTest(i=i):self.reject(change)
    def test_no_candidate_for_boundary_only(self):
        f=fixture();w=f[3][0];w["relation"]["positive_area_intersection"]=False
        old="|".join((w["manifest_membership"],w["evidence_group"],w["layer_relation"],"positive-area"));new=old.replace("positive-area","boundary-only")
        for groups in(f[0]["evidence_groups"],f[2][0]["evidence_groups"]):
            groups[old]-=1
            if not groups[old]:del groups[old]
            groups[new]=1
        r=c.classify(*f);self.assertEqual(r["result"]["temporary_fixed_counterpart_nets"],0)
        self.assertEqual(len(r["witnesses"]),12)
    def test_duplicate_json_and_nonfinite(self):
        for raw in(b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):c.decode(raw)
    def test_original_fixed_and_cover_are_never_candidates(self):
        f=fixture();f[5]["T"]="FIXED";r=c.classify(*f);self.assertEqual(r["counterparts"],[])
        f[5]["T"]="COVER";r=c.classify(*f);self.assertEqual(r["counterparts"],[])
    def test_multiple_witnesses_preserve_multiplicity(self):
        f=fixture();w=copy.deepcopy(f[3][0]);w.update(source_witness_index=2,source_pointer="/markers/0/endpoint_witnesses/2",record_id=["fixture","T","distinct-second-shape"])
        f[3].insert(2,w);f[0]["complete_witness_records"]+=1;f[7]["witnesses"]+=1
        f[2][0]["all_witnesses"]+=1;f[2][0]["witnesses_by_owner"]["T"]+=1
        group="|".join((w["manifest_membership"],w["evidence_group"],w["layer_relation"],"positive-area"))
        f[0]["evidence_groups"][group]+=1;f[2][0]["evidence_groups"][group]+=1
        r=c.classify(*f);self.assertEqual(r["result"]["temporary_fixed_counterpart_nets"],1)
        self.assertEqual(r["result"]["temporary_fixed_counterpart_witnesses"],2)
        self.assertEqual(r["result"]["temporary_fixed_counterpart_markers"],1)
if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),passed=result.wasSuccessful(),native_tools_executed=False,routing_executed=False)
    print("COUNTERPART_CONTROLS "+json.dumps(report),flush=True)
    require=result.testsRun==9 and not result.failures and not result.errors and not result.skipped
    raise SystemExit(0 if require else 1)
