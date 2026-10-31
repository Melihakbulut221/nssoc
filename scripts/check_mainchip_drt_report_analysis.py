#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,json,os,unittest
from unittest.mock import patch
import mainchip_drt_report_analysis as m
class Controls(unittest.TestCase):
    def report(self,nets=("a","b"),kind="Short",layer="Metal2",coords=("1.0000","2.0000","3.0000","4.0000")):
        return ("violation type: "+kind+"\n\tsrcs: "+" ".join("net:"+n for n in nets)+"\n\tbbox = ("+coords[0]+", "+coords[1]+") - ("+coords[2]+", "+coords[3]+") on Layer "+layer+"\n").encode()
    def owners(self):
        flags=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        plan=dict(mutable_nets=["a"],protected_nets=["clock"],added_instances=["diode0","diode1"],attachments={"diode0":"a","diode1":"a"},**flags)
        mutation=dict(complete=True,all_guides_unchanged=True,removed={"a":{"previous":"opaque authenticated record"}},delta=dict(complete=True,all_nonmutable_exact=True,all_instances_and_guides_checked_separately=True,cleared_nets=["a"],**flags),**flags)
        return plan,mutation
    def test_exact_escaped_names_and_coordinate_lexemes_preserved(self):
        name=r"u_ibex.regfile\[31\].q[0]"
        raw=self.report((name,"$abc$net"),coords=("-0.0000","2.0000","3.0000","4.0000"))
        row=m.parse_report(raw)[0]
        self.assertEqual(row["nets"],[name,"$abc$net"]);self.assertEqual(row["raw"].encode(),raw)
        self.assertIn("-0.0000",row["bbox_text"]);self.assertEqual(row["layer"],"Metal2")
    def test_incomplete_unknown_and_nonfinite_grammar_refused(self):
        raw=self.report()
        bad=[raw[:-1],raw+b"extra\n",raw.replace(b"net:a",b"inst:a"),raw.replace(b"1.0000",b"NaN"),raw.replace(b"\n",b"\r\n"),raw.replace(b"\tsrcs:",b" srcs:"),b"\xff\n"]
        for b in bad:
            with self.subTest(raw=b):
                with self.assertRaises((ValueError,UnicodeError)):m.parse_report(b)
    def test_manifest_ownership_is_exact_and_never_assumes_fixed(self):
        o=m.ownership(*self.owners());rows=m.parse_report(self.report(("a","clock"))+self.report(("b",r"a\[0\]")))
        result=m.classify(rows,o)
        self.assertEqual(result["total_records"],2)
        self.assertEqual([x["ownership"]for x in result["records"][0]["net_ownership"]],["mutable_cleared_manifest","protected_manifest"])
        self.assertEqual(result["records"][0]["net_ownership"][0]["attached_added_instances"],["diode0","diode1"])
        self.assertEqual([x["ownership"]for x in result["records"][1]["net_ownership"]],["not_in_either_manifest"]*2)
    def test_duplicate_overlap_and_missing_attachment_censuses_refused(self):
        p,x=self.owners()
        for key,value in(("mutable_nets",["a","a"]),("protected_nets",["a"]),("added_instances",["diode0"]),("attachments",{"diode0":"b","diode1":"a"})):
            bad=copy.deepcopy(p);bad[key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):m.ownership(bad,x)
    def test_mutation_and_acceptance_guard_fail_closed(self):
        p,x=self.owners()
        for where,key,value in(("outer","complete",False),("outer","all_guides_unchanged",False),("outer","removed",{}),("delta","cleared_nets",["b"]),("delta","all_nonmutable_exact",False),("delta","physical_acceptance",True)):
            bad=copy.deepcopy(x);target=bad if where=="outer"else bad["delta"];target[key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):m.ownership(p,bad)
        p["timing_accepted"]=True
        with self.assertRaises(ValueError):m.ownership(p,x)
    def test_delta_is_multiset_and_no_coordinate_normalization(self):
        a=self.report();b=self.report(coords=("1.0001","2.0000","3.0000","4.0000"))
        delta=m.exact_delta(m.parse_report(a+a),m.parse_report(a+b))
        self.assertEqual((delta["unchanged_records"],delta["removed_records"],delta["added_records"]),(1,1,1))
        self.assertEqual(delta["removed"][0]["raw"].encode(),a);self.assertEqual(delta["added"][0]["raw"].encode(),b)
    def test_complete_synthetic_classification_retains_all_records_and_scope(self):
        p,x=self.owners()
        inputs={"fixed-routing.drc-5.rpt":self.report()+self.report(("a","clock"),"Metal Spacing","Metal4"),"fixed-routing.drc-10.rpt":self.report()+self.report(),"insertion-plan.json":m.q.encode(p),"stale-wire-mutation.json":m.q.encode(x)}
        r=m.analyze(inputs)
        self.assertEqual((r["iteration5"]["total_records"],r["iteration10"]["total_records"]),(2,2))
        self.assertEqual((r["mutable_manifest_nets"],r["protected_manifest_nets"],r["added_attachment_records"]),(1,1,2))
        self.assertEqual((r["exact_record_delta"]["unchanged_records"],r["exact_record_delta"]["removed_records"],r["exact_record_delta"]["added_records"]),(1,1,1))
        self.assertTrue(all(r[k]is False for k in m.FLAGS))
    def test_source_context_refusal_precedes_network_and_checkout(self):
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}),patch.object(m.q,"api",side_effect=AssertionError("network")),patch.object(m.subprocess,"check_output",side_effect=AssertionError("checkout")):
            with self.assertRaisesRegex(ValueError,"hosted only"):m.source_gate()
if __name__=="__main__":
    if os.environ.get("GITHUB_ACTIONS")!="true":raise RuntimeError("Run controls on GitHub only")
    unittest.main(verbosity=2)
