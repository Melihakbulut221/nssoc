#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic contracts, never a native ODB result."""
import ast,copy,os,types,unittest
from pathlib import Path
from unittest.mock import patch
import mainchip_drt_obstacle_contract as k
import check_mainchip_drt_report_analysis as fixture_m
class Controls(unittest.TestCase):
    def fixture(self):
        f=fixture_m.Controls();p,x=f.owners()
        raw=f.report()+f.report()+f.report(("a","clock"),"Metal Spacing","Metal4")+f.report(("a","clock"),"Short","Metal3")
        rows=k.text.parse_report(raw);a=dict(status="COMPLETE_TEXTUAL_DRT_MANIFEST_CLASSIFICATION",iteration10=k.text.classify(rows,k.text.ownership(p,x)),**k.text.FLAGS)
        return f,p,x,raw,a
    def test_exact_decimal_grid_and_negative_values(self):
        f=fixture_m.Controls();row=k.text.parse_report(f.report(coords=("-0.0000","-2.0050","3.0100","4.0000")))[0]
        self.assertEqual(k.dbu_box(row,1000),[0,-2005,3010,4000])
        self.assertEqual(k.dbu_box(row,2000),[0,-4010,6020,8000])
    def test_off_grid_invalid_dbu_and_changed_layer_refused(self):
        f=fixture_m.Controls();row=k.text.parse_report(f.report(coords=("1.0001","2.0000","3.0000","4.0000")))[0]
        for dbu in(1000,True,0,-1,1000.0):
            with self.subTest(dbu=dbu),self.assertRaises(ValueError):k.dbu_box(row,dbu)
        row=k.text.parse_report(f.report())[0];row["layer"]="Metal3"
        with self.assertRaises(ValueError):k.dbu_box(row,1000)
    def test_closed_edge_point_and_positive_area_are_distinct(self):
        a=[0,0,10,10]
        expected=[([2,3,8,9],(True,True,6,6)),([10,2,12,8],(True,False,0,6)),([10,10,12,12],(True,False,0,0)),([11,2,12,8],(False,False,-1,6))]
        for b,want in expected:
            got=k.relation(a,b);self.assertEqual(tuple(got[n]for n in("closed_intersection","positive_area_intersection","x_overlap_dbu","y_overlap_dbu")),want)
        for b in([0,0,True,1],[2,0,1,1],[0,0,1],[0.0,0,1,1]):
            with self.assertRaises(ValueError):k.rectangle(b)
    def test_complete_scope_keeps_multiplicity_and_all_other_kinds(self):
        f,p,x,raw,a=self.fixture();s,o=k.scope(raw,p,x,a,1000,4,2)
        self.assertEqual([r["ordinal"]for r in s["markers"]],[0,1])
        self.assertEqual([r["ordinal"]for r in s["other_markers"]],[2,3])
        self.assertEqual(s["endpoint_names"],["a","b"])
        self.assertEqual([r["box"]for r in s["markers"]],[[1000,2000,3000,4000]]*2)
        self.assertEqual("".join(r["raw"]for r in sorted(s["markers"]+s["other_markers"],key=lambda r:r["ordinal"])).encode(),raw)
    def test_incomplete_or_reinterpreted_analysis_and_censuses_refused(self):
        f,p,x,raw,a=self.fixture()
        for total,selected in((3,2),(4,1),(4,3)):
            with self.assertRaises(ValueError):k.scope(raw,p,x,a,1000,total,selected)
        for field,value in(("physical_cause_proven",True),("status","PASS_PHYSICAL")):
            bad={**a,field:value}
            with self.assertRaises(ValueError):k.scope(raw,p,x,bad,1000,4,2)
        bad=copy.deepcopy(a);bad["iteration10"]["records"].pop()
        with self.assertRaises(ValueError):k.scope(raw,p,x,bad,1000,4,2)
    def test_two_distinct_selected_endpoints_required(self):
        f,p,x,raw,a=self.fixture()
        for nets in(("a",),("a","a"),("a","b","clock")):
            b=f.report(nets);a["iteration10"]=k.text.classify(k.text.parse_report(b),k.text.ownership(p,x))
            with self.assertRaises(ValueError):k.scope(b,p,x,a,1000,1,1)
    def test_witness_requires_exact_owner_and_layer_or_explicit_pin_projection(self):
        escaped=r"a\[0\]";m=dict(nets=[escaped,"b"],box=[0,0,10,10],layer="Metal2")
        shape=dict(owner=escaped,box=[1,2,4,6],kind="wire",layer="Metal2")
        r=k.witness(m,shape);self.assertEqual(r["layer_relation"],"same_layer");self.assertIn("not_root_cause",r["observation"])
        with self.assertRaises(ValueError):k.witness(m,{**shape,"owner":"a[0]"})
        off={**shape,"layer":"Metal1"}
        self.assertIsNone(k.witness(m,off));self.assertEqual(k.witness(m,off,True)["layer_relation"],"xy_projection_only_different_layer")
        self.assertIsNone(k.witness(m,{**shape,"box":[11,11,12,12]},True))
    def test_actual_candidate_census_and_added_endpoint_inventory(self):
        nets=["net"+str(i)for i in range(143820)]
        added=["NSSOC_BULK_NEW_"+str(i)for i in range(1351)]
        inst=["base"+str(i)for i in range(153129)]+added
        attachments={n:nets[0]for n in added}
        self.assertEqual(k.census(nets,inst,added,attachments),dict(net_count=143820,instance_count=154480,added_count=1351))
        for nn,ii,aa,at in((nets[:-1],inst,added,attachments),(nets,inst[:-1],added,attachments),
          (nets,inst[:-1]+[inst[0]],added,attachments),(nets,inst,added[:-1],attachments),
          (nets,inst,added,{**attachments,added[0]:"unknown"})):
            with self.assertRaises(ValueError):k.census(nn,ii,aa,at)
    def test_actual_context_and_native_authority_refusal(self):
        e=dict(GITHUB_ACTIONS="true",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",
          GITHUB_REF="refs/heads/codex/mainchip-drt-obstacle-readback",GITHUB_SHA="a"*40,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123")
        self.assertEqual(k.context(e,"a"*40),dict(source="a"*40,run=123,attempt=1))
        for key,val in(("GITHUB_ACTIONS","false"),("GITHUB_REPOSITORY","other/repo"),("GITHUB_EVENT_NAME","push"),
          ("GITHUB_REF","refs/heads/main"),("GITHUB_SHA","b"*40),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_RUN_ID","0")):
            with self.assertRaises(ValueError):k.context({**e,key:val},"a"*40)
        with patch.object(k,"source_gate",return_value=dict(native_readonly_authorized=False,native_routing_authorized=False)):
            with self.assertRaisesRegex(ValueError,"disabled"):k.native_authorization()
    def pin_function(self):
        path=Path(__file__).with_name("mainchip_drt_obstacle_native.py");tree=ast.parse(path.read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="all_pin_geometry"];self.assertEqual(len(nodes),1)
        geom=types.SimpleNamespace(box=lambda r:list(r),placed_box=lambda transform,b:transform[b.key])
        scope=dict(q=k.q,geom=geom);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
        return scope["all_pin_geometry"]
    def pin_fixture(self):
        ns=types.SimpleNamespace
        layer=lambda name:ns(getName=lambda:name)
        boxes=[ns(key="left",isVia=lambda:False,getTechLayer=lambda:layer("Metal1")),ns(key="right",isVia=lambda:False,getTechLayer=lambda:layer("Metal2"))]
        transformed={"left":[-30,40,-10,60],"right":[-70,80,-50,100]}
        mpins=[ns(getGeometry=lambda:[boxes[0]]),ns(getGeometry=lambda:[boxes[1],boxes[1]])]
        actual=[(layer("Metal1"),transformed["left"]),(layer("Metal2"),transformed["right"]),(layer("Metal2"),transformed["right"])]
        term=ns(getGeometries=lambda:actual,getInst=lambda:ns(getTransform=lambda:transformed),getMTerm=lambda:ns(getMPins=lambda:mpins))
        return term,actual,boxes
    def test_all_mpin_shapes_transform_layers_and_multiplicity_checked(self):
        fn=self.pin_function();term,actual,boxes=self.pin_fixture()
        self.assertEqual(fn(term),[("Metal1",[-30,40,-10,60]),("Metal2",[-70,80,-50,100]),("Metal2",[-70,80,-50,100])])
        actual.reverse();self.assertEqual(len(fn(term)),3)
        actual.pop()
        with self.assertRaises(ValueError):fn(term)
    def test_changed_pin_layer_transform_and_unqualified_via_refused(self):
        fn=self.pin_function()
        for mode in("layer","transform","via"):
            term,actual,boxes=self.pin_fixture()
            if mode=="layer":actual[0]=(types.SimpleNamespace(getName=lambda:"Metal3"),actual[0][1])
            elif mode=="transform":actual[0]=(actual[0][0],[-29,40,-10,60])
            else:boxes[0].isVia=lambda:True
            with self.subTest(mode=mode),self.assertRaises(ValueError):fn(term)
if __name__=="__main__":
    if os.environ.get("GITHUB_ACTIONS")!="true":raise RuntimeError("Hosted controls only")
    unittest.main(verbosity=2)
