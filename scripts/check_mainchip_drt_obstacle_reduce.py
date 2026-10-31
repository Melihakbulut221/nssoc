#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted independent full-census synthetic reduction/refusal controls; no CAD."""
import copy,io,json,unittest
import mainchip_drt_obstacle_reduce as r
import cloud_mainchip_drt_obstacle_reduce as host
q=r.q

def fixture():
    names=["n"+str(i).zfill(3)for i in range(373)]
    endpoints={};pins={}
    for i,name in enumerate(names):
        membership=r.MEMBERSHIPS[i%3]
        b=[2000,0,2100,100]if i==0 else[1,1,10,10]
        if i==1:
            pin=dict(owner=name,record_id=["bterm","port1","bpin",0,"box",0],
                     kind="bterm-pin",layer="Metal1",box=b,terminal="port1")
        else:
            pin=dict(owner=name,record_id=["iterm","inst"+str(i),"A","geometry",0],
                     kind="iterm-pin",layer="Metal2",box=b,instance="inst"+str(i),terminal="A",
                     master=["fixture_lib","fixture_master"],added_diode=False)
        pins[name]=pin;present=membership!="mutable_cleared_manifest"
        counts={pin["kind"]:1}
        if present:counts["wire"]=1
        if i==2:counts["special-via"]=2
        endpoints[name]=dict(identity=dict(name=name,sigtype="GROUND"if i==2 else"SIGNAL"),
          encoded=dict(wire_present=present,metadata="FIXED"if present else"ROUTED",paths=["FIXED","FIXED"]if present else[]),
          manifest_membership=membership,native_geometry_counts=counts,native_geometry_records=sum(counts.values()),
          native_geometry_sha256="a"*64,all_endpoint_pin_geometry=[pin],wire_raw_pin=None,wire_projection_pin=None)
    def witness(shape):
        # Independent known fixture oracle: every shape touches the marker.
        b=shape["box"];x=min(2000,b[2])-max(0,b[0]);y=min(2000,b[3])-max(0,b[1])
        return dict(copy.deepcopy(shape),relation=dict(closed_intersection=True,positive_area_intersection=x>0 and y>0,x_overlap_dbu=x,y_overlap_dbu=y),
          layer_relation="same_layer"if shape["layer"]=="Metal2"else"xy_projection_only_different_layer",
          observation="candidate_endpoint_obstacle_evidence_not_root_cause")
    selected=[];actual=[]
    for i in range(434):
        nets=[names[i%373],names[(i+1)%373]]
        row=dict(ordinal=i,kind="Short",layer="Metal2",nets=nets,box=[0,0,2000,2000],
          bbox_text="\tbbox = (0.0000, 0.0000) - (2.0000, 2.0000) on Layer Metal2")
        row["raw"]="violation type: Short\n\tsrcs: "+" ".join("net:"+n for n in nets)+"\n"+row["bbox_text"]+"\n"
        selected.append(row);items=[witness(pins[n])for n in nets]
        first=nets[0]
        if endpoints[first]["encoded"]["wire_present"]:
            items.append(witness(dict(owner=first,record_id=["net",first,"wire","shape",0],kind="wire",layer="Metal2",
              box=[10,10,30,30],route_metadata="FIXED",encoded_classes=["FIXED","FIXED"])))
        if names[2]in nets:
            via=dict(name="fixture_via",top="Metal2",bottom="Metal1",box=[0,0,20,20],
              components=[dict(layer="Metal1",box=[0,0,20,20],component_ordinal=0),dict(layer="Metal2",box=[0,0,20,20],component_ordinal=1)])
            items.append(witness(dict(owner=names[2],record_id=["net",names[2],"swire",0,"box",0,"component",1],
              kind="special-via",layer="Metal2",box=[20,20,40,40],via=via,origin_xy=[20,20],via_namespace="tech")))
        actual.append(dict(copy.deepcopy(row),endpoint_witnesses=items))
    other=[dict(ordinal=i,kind="Metal Spacing",layer="Metal1",nets=["other"+str(i)],raw="EXPLICIT SYNTHETIC OTHER RECORD\n")for i in range(434,596)]
    scope=dict(markers=selected,other_markers=other,endpoint_names=names,report_records=596,selected_records=434,other_records=162,dbu=1000,
      **{k:False for k in r.SOURCE_FLAGS})
    report=dict(status="COMPLETE_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION",markers=actual,other_markers=copy.deepcopy(other),endpoint_nets=endpoints,
      dbu_per_micron=1000,native_api_evidence_sha256=r.API_SHA,input_odb_unchanged=True,terminal_errors=[],read_only=True,native_tools_executed=True,
      **r.EXPECTED,**{k:False for k in r.SOURCE_FLAGS})
    return report,scope

class FullReductionControls(unittest.TestCase):
    def setUp(self):self.report,self.scope=fixture()
    def run_fixture(self):
        rows=[];result=r.reduce_report(self.report,self.scope,rows.append);return result,rows
    def reject(self,change):
        change()
        with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):self.run_fixture()
    def first(self,kind):
        return next(w for m in self.report["markers"]for w in m["endpoint_witnesses"]if w["kind"]==kind)
    def test_complete_full_census_every_witness_exactly_once(self):
        original=q.encode(self.report);source=q.encode(self.scope);result,rows=self.run_fixture()
        expected=[(mi,wi,m["ordinal"],w["owner"],w["record_id"],w["box"])for mi,m in enumerate(self.report["markers"])for wi,w in enumerate(m["endpoint_witnesses"])]
        actual=[(w["source_marker_index"],w["source_witness_index"],w["source_marker_ordinal"],w["owner"],w["record_id"],w["box"])for w in rows]
        self.assertEqual(actual,expected);self.assertEqual(len(result["markers"]),434);self.assertEqual(len(result["endpoints"]),373)
        self.assertEqual(result["summary"]["complete_pin_records_checked"],373)
        self.assertEqual(result["summary"]["complete_witness_records"],len(expected))
        self.assertEqual(result["other_markers"],self.scope["other_markers"])
        self.assertEqual(q.encode(self.report),original);self.assertEqual(q.encode(self.scope),source)
        self.assertTrue(all(result["summary"][k]is False for k in r.FLAGS))
    def test_pin_projection_boundary_and_fixed_special_evidence_stay_distinct(self):
        _,rows=self.run_fixture()
        boundary=next(w for w in rows if w["owner"]=="n000")
        self.assertFalse(boundary["relation"]["positive_area_intersection"])
        pin=next(w for w in rows if w["kind"]=="bterm-pin")
        self.assertEqual(pin["layer_relation"],"xy_projection_only_different_layer")
        wire=next(w for w in rows if w["kind"]=="wire")
        self.assertEqual(wire["evidence_group"],"ordinary-wire-FIXED")
        special=next(w for w in rows if w["kind"]=="special-via")
        self.assertEqual(special["evidence_group"],"special-PG")
        self.assertEqual(special["details"]["via"]["component_count"],2)
    def test_empty_witness_marker_is_retained(self):
        self.report["markers"][0]["endpoint_witnesses"]=[]
        result,rows=self.run_fixture()
        self.assertTrue(result["markers"][0]["no_observed_endpoint_intersection"])
        self.assertEqual(result["markers"][0]["all_witnesses"],0)
        self.assertEqual(len(result["markers"]),434)
    def test_equal_geometry_distinct_records_remain_distinct(self):
        marker=self.report["markers"][1];shape=copy.deepcopy(self.first("wire"));shape["owner"]=marker["nets"][0]
        shape["record_id"]=["net",shape["owner"],"wire","shape",1];marker["endpoint_witnesses"].append(shape)
        ep=self.report["endpoint_nets"][shape["owner"]];ep["native_geometry_counts"]["wire"]+=1;ep["native_geometry_records"]+=1
        _,rows=self.run_fixture()
        self.assertEqual(sum(w["source_marker_index"]==1 and w["kind"]=="wire"for w in rows),2)
    def test_missing_marker(self):self.reject(lambda:self.report["markers"].pop())
    def test_missing_endpoint(self):self.reject(lambda:self.report["endpoint_nets"].pop("n372"))
    def test_duplicate_original_ordinal(self):self.reject(lambda:self.scope["markers"][1].update(ordinal=0))
    def test_missing_other_kind(self):self.reject(lambda:self.report["other_markers"].pop())
    def test_changed_dbunits(self):self.reject(lambda:self.report.update(dbu_per_micron=2000))
    def test_off_grid_marker(self):self.reject(lambda:self.scope["markers"][0].update(bbox_text="\tbbox = (0.0001, 0.0000) - (2.0000, 2.0000) on Layer Metal2"))
    def test_changed_original_raw_marker(self):self.reject(lambda:self.scope["markers"][0].update(raw="changed"))
    def test_wrong_endpoint_names(self):self.reject(lambda:self.scope["endpoint_names"].reverse())
    def test_global_census(self):self.reject(lambda:self.report.update(all_instance_count=153130))
    def test_forged_physical_acceptance(self):self.reject(lambda:self.report.update(physical_acceptance=True))
    def test_changed_input_odb(self):self.reject(lambda:self.report.update(input_odb_unchanged=False))
    def test_terminal_error(self):self.reject(lambda:self.report.update(terminal_errors=[dict(error="fixture")]))
    def test_geometry_record_count(self):self.reject(lambda:self.report["endpoint_nets"]["n001"].update(native_geometry_records=999))
    def test_pin_kind_count(self):self.reject(lambda:self.report["endpoint_nets"]["n000"]["native_geometry_counts"].update(**{"iterm-pin":2}))
    def test_missing_pin_inventory(self):self.reject(lambda:self.report["endpoint_nets"]["n000"]["all_endpoint_pin_geometry"].clear())
    def test_duplicate_pin_record(self):
        row=self.report["endpoint_nets"]["n000"]
        def change():
            row["all_endpoint_pin_geometry"].append(copy.deepcopy(row["all_endpoint_pin_geometry"][0]))
            row["native_geometry_records"]+=1;row["native_geometry_counts"]["iterm-pin"]+=1
        self.reject(change)
    def test_unknown_membership(self):self.reject(lambda:self.report["endpoint_nets"]["n001"].update(manifest_membership="assumed_fixed"))
    def test_mutable_wire_not_cleared(self):self.reject(lambda:self.report["endpoint_nets"]["n000"]["encoded"].update(wire_present=True))
    def test_witness_owner(self):self.reject(lambda:self.report["markers"][0]["endpoint_witnesses"][0].update(owner="n372"))
    def test_witness_not_in_actual_pin_inventory(self):self.reject(lambda:self.first("iterm-pin").update(master=["other","other"]))
    def test_wrong_recorded_relation(self):self.reject(lambda:self.first("iterm-pin")["relation"].update(x_overlap_dbu=123))
    def test_unobserved_separated_geometry(self):self.reject(lambda:self.first("iterm-pin").update(box=[5000,5000,5100,5100]))
    def test_cross_layer_wire_is_not_pin_projection(self):
        def change():self.first("wire").update(layer="Metal1",layer_relation="xy_projection_only_different_layer")
        self.reject(change)
    def test_wire_metadata_not_endpoint_metadata(self):self.reject(lambda:self.first("wire").update(route_metadata="ROUTED"))
    def test_wire_encoded_classes(self):self.reject(lambda:self.first("wire").update(encoded_classes=["ROUTED"]))
    def test_via_component_translation(self):self.reject(lambda:self.first("special-via")["origin_xy"].__setitem__(0,21))
    def test_via_component_order(self):self.reject(lambda:self.first("special-via")["via"]["components"][1].update(component_ordinal=0))
    def test_via_component_layer(self):self.reject(lambda:self.first("special-via")["via"]["components"][1].update(layer="Metal3"))
    def test_duplicate_witness(self):self.reject(lambda:self.report["markers"][0]["endpoint_witnesses"].append(copy.deepcopy(self.report["markers"][0]["endpoint_witnesses"][0])))
    def test_scalar_bool_not_integer_coordinate(self):self.reject(lambda:self.first("iterm-pin")["box"].__setitem__(0,True))
    def test_complete_result_cannot_suppress_source_marker_fields(self):self.reject(lambda:self.report["markers"][0].pop("raw"))
    def test_recorded_different_layer_pin_relation_must_be_explicit(self):self.reject(lambda:self.first("bterm-pin").update(layer_relation="same_layer"))
    def test_source_controls_have_no_analysis_authority(self):
        with self.assertRaises(ValueError):host.actual_context()

def main():
    head=host.source_gate("controls")
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(FullReductionControls)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    raw=stream.getvalue();print(raw,end="")
    record=dict(status="PASS_SOURCE_ONLY_OBSTACLE_REDUCTION_CONTROLS"if result.wasSuccessful()else"FAIL_SOURCE_CONTROLS",
      source=head,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
      successful=result.wasSuccessful(),native_acquired=False,native_executed=False,actual_report_acquired=False,
      full_synthetic_census=dict(markers=434,endpoints=373,original_records=596),log_sha256=q.sha(raw.encode()))
    print("MAINCHIP_OBSTACLE_REDUCTION_CONTROLS "+json.dumps(record,sort_keys=True),flush=True)
    q.require(result.wasSuccessful()and not result.skipped,"all reduction controls passed without skips")
if __name__=="__main__":main()
