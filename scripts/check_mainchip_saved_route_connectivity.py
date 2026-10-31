#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,json,tempfile,unittest
from pathlib import Path
import cloud_mainchip_saved_route_connectivity as h
import mainchip_net459_connectivity as graph
class ConnectivityControls(unittest.TestCase):
    def test_original_geometric_connectivity_controls(self):
        r=graph.controls()
        self.assertEqual((r["positive_count"],r["refusal_count"]),(11,10))
        self.assertFalse(r["pin_internal_connectivity_inferred"])
    def test_exact_source_projection(self):
        self.assertTrue(h.source_guard()["native_readback_authorized"])
    def test_original_acquisition_body_is_unchanged(self):
        f=h.bind_function(h.saved.acquire,SELECTED=h.SELECTED)
        self.assertIs(f.__code__,h.saved.acquire.__code__)
        self.assertEqual(f.__globals__["SELECTED"],{h.CANDIDATE,h.PLAN})
        self.assertNotEqual(h.saved.acquire.__globals__["SELECTED"],h.SELECTED)
    def test_unknown_binding_refused(self):
        with self.assertRaises(AssertionError):h.bind_function(h.saved.acquire,UNOWNED_OVERRIDE=True)
    def fixture(self,root):
        (root/"scripts").mkdir();(root/"x.py").write_bytes(b"source")
        m=dict(schema="mainchip-saved-route-connectivity-pins-v1",native_readback_authorized=True,
          routing_authorized=False,files={"x.py":h.pin(root/"x.py")["sha256"]},**h.FLAGS)
        (root/h.MANIFEST).write_text(json.dumps(m));return m
    def test_mutated_source_refused(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td);self.fixture(p);(p/"x.py").write_bytes(b"changed")
            with self.assertRaises(AssertionError):h.source_guard(p)
    def test_routing_authority_refused(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td);m=self.fixture(p);m["routing_authorized"]=True
            (p/h.MANIFEST).write_text(json.dumps(m))
            with self.assertRaises(AssertionError):h.source_guard(p)
if __name__=="__main__":unittest.main(verbosity=2)
