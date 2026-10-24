#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Resolve actual postroute flow configuration with original runtime and models."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/pnr'))
from mainchip_completed_postroute_flow import MainchipCompletedPostroute
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    package=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
    original=json.loads((package/'resolved-flow-config.json').read_text())
    raw=package/'trial-config.json'
    flow=MainchipCompletedPostroute(str(raw),pdk_root=original['PDK_ROOT'],pdk='ihp-sg13g2',scl='sg13g2_stdcell')
    actual=json.loads(flow.config.dumps())
    (out/'resolved.json').write_text(json.dumps(actual,indent=2)+'\n')
    ignored={'meta','DESIGN_DIR'}
    changed={k:dict(original=original.get(k),actual=v)for k,v in actual.items()if k not in ignored and (k not in original or original[k]!=v)}
    report=dict(status='CHECKING_ORIGINAL_NATIVE_CONFIG',differences=changed,
        original_sha256=sha(package/'resolved-flow-config.json'),raw_sha256=sha(raw),
        resolved_sha256=sha(out/'resolved.json'),compared_keys=sorted(set(actual)-ignored),
        metadata_differences={k:dict(original=original.get(k),actual=actual.get(k))for k in ignored},
        native_routing_started=False,final_timing_complete=False,full_phy_accepted=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not changed,('Changed postroute native configuration',changed)
    assert actual['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
    assert float(actual['CLOCK_PERIOD'])==20 and float(actual['TIME_DERATING_CONSTRAINT'])==5 and actual['STA_THREADS']==1
    assert set(actual['STA_CORNERS'])=={'nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C'}
    report['status']='PASS_ORIGINAL_NATIVE_POSTROUTE_CONFIG_NOT_ROUTED_ANALYSIS'
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(report['compared_keys']))
if __name__=='__main__':main()
