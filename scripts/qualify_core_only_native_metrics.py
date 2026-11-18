#!/usr/bin/env python3
"""Native parser/serialization regression; no circuit or timing pass claimed."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hw/soc/pnr"))
from core_only_routed_extraction_flow import CoreExtractedSTA, AuditedRoutedSTA
from librelane.steps.step import DefaultOutputProcessor
OUT=ROOT/"hw/soc/out/core-only-extracted-guards/metrics"
CORNER="nom_slow_1p08V_125C"
SUFFIX="__corner:"+CORNER

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    parser=object.__new__(DefaultOutputProcessor)
    parser.step=SimpleNamespace(step_dir=None)
    parser.generated_metrics={}
    parser.current_rpt=None
    values={"timing__setup__ws":("F","-0.307233"),
        "timing__hold__ws":("F","0.496148"),
        "timing__setup_vio__count":("I","2"),
        "timing__hold_vio__count":("I","0"),
        "design__max_cap_violation__count":("I","3"),
        "design__max_slew_violation__count":("I","26")}
    for key,(kind,value) in values.items():
        assert parser.process_line(f"%OL_METRIC_{kind} {key}{SUFFIX} {value}\n")
    metrics=parser.result()
    assert isinstance(metrics["timing__setup__ws"+SUFFIX],Decimal)
    step=object.__new__(CoreExtractedSTA)
    # Only the inherited native process is replaced; exercise the actual adapter.
    def invoke(name,data):
        folder=OUT/name;folder.mkdir()
        with patch.object(AuditedRoutedSTA,"run_corner",return_value=data):
            result=step.run_corner(None,{},CORNER,str(folder))
        assert result is data
        return json.loads((folder/"fresh_metrics.json").read_text())
    encoded=invoke("native-decimal",metrics)
    assert encoded["timing__setup__ws"+SUFFIX]==-0.307233
    assert encoded["timing__setup_vio__count"+SUFFIX]==2
    assert encoded["timing__hold_vio__count"+SUFFIX]==0
    # Positive result retains violations; a successful adapter is not timing closure.
    cases={}
    key="timing__setup__ws"+SUFFIX
    for name,value in [("nan",Decimal("NaN")),("inf",Decimal("Infinity")),
                       ("bool",True),("string","-0.307233")]:
        cases[name]={**metrics,key:value}
    cases["missing"]={k:v for k,v in metrics.items() if k!=key}
    count="timing__setup_vio__count"+SUFFIX
    cases["negative-count"]={**metrics,count:-1}
    cases["fractional-count"]={**metrics,count:Decimal("0.5")}
    cases["wrong-corner"]={**metrics,"timing__setup__ws__corner:wrong":Decimal("0.1")}
    rejected=[]
    for name,data in cases.items():
        try:invoke(name,data)
        except (AssertionError,ValueError):
            assert not (OUT/name/"fresh_metrics.json").exists()
            rejected.append(name)
        else:raise AssertionError("Malformed metrics accepted: "+name)
    source=ROOT/"hw/soc/pnr/core_only_routed_extraction_flow.py"
    report=dict(status="PASS_NATIVE_DECIMAL_CAPTURE_AND_REJECTION_CONTROLS",
        adapter_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        rejected=rejected, positive_setup_violations=encoded[count],
        circuit_executed=False, accepted=False)
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))
if __name__=="__main__":main()
