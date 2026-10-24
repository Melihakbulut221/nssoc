#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export native master and slave states without changing any divider device."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import make_pcie_clock_div2_high_input_v1 as prior
m=prior.m
BASE_PORTS=tuple(m.PORTS)
TOP='nssoc_tx_phase_divider55_v1'
PORTS=(*BASE_PORTS,'MP','MN')
NET_MAP={'DIV__XSECOND__MP':'MP','DIV__XSECOND__MN':'MN'}
original_devices=m.devices
original_placement=m.placement_plan
original_direction=m.use_direction

def devices(root):
    before=original_devices(root);after=copy.deepcopy(before)
    assert len(before)==43 and {r['kind'] for r in before}=={'hbt','resistor','capacitor'}
    assert all(n in {v for r in before for v in r['nets']}for n in NET_MAP)
    for row in after:row['nets']=[NET_MAP.get(n,n)for n in row['nets']]
    inverse={v:k for k,v in NET_MAP.items()};restored=copy.deepcopy(after)
    for row in restored:row['nets']=[inverse.get(n,n)for n in row['nets']]
    assert restored==before,'Device identity, model, geometry or topology changed'
    return after

def placement(rows):
    root=Path(__file__).resolve().parents[3]
    assert rows==devices(root)
    m.PORTS=BASE_PORTS
    try:plan,starts,nets=original_placement(original_devices(root))
    finally:m.PORTS=PORTS
    nets={rid:[NET_MAP.get(n,n)for n in values]for rid,values in nets.items()}
    assert all(len(v)==len(set(v))for v in nets.values())
    return plan,starts,nets

def direction(name):
    return ('SIGNAL','OUTPUT')if name in ('MP','MN')else original_direction(name)

m.TOP=TOP;m.PORTS=PORTS;m.devices=devices;m.placement_plan=placement;m.use_direction=direction
if __name__=='__main__':
    m.main()
    out=Path(sys.argv[sys.argv.index('--out')+1]);p=out/'result.json';r=json.loads(p.read_text())
    assert set(r['ports'])==set(PORTS)
    r['input_sha256'].update({str(p):m.sha(p)for p in [Path(__file__).resolve(),Path(prior.__file__).resolve()]})
    r.update(status='GENERATED_NATIVE_PHASE_PORTS_REQUIRES_DRC_LVS_FRESH_RC_AND_LOADED_PHASE',
      original_internal_net_to_new_port=NET_MAP,device_graph_exact_under_bijective_port_rename=True,
      phase_order_electrically_verified=False,tx_clock_driver_implemented=False,full_clock_tree_implemented=False,
      scope='Same19HBT20rppd4MIM12finite-tap high-input divider. Two real internal master nets become physical output routes. No ideal internal clock source. Native loaded quadrature, common-mode conversion,31-clock distribution and actualPLL connection remain required.')
    p.write_text(json.dumps(r,indent=2)+'\n')
