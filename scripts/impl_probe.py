# SPDX-License-Identifier: Apache-2.0
"""Placement-to-global-route timing probe of the main chip from RTL.

prepare: from the native mapped netlist, build the unchanged packet-SoC
LibreLane configuration (prepare_pcie_mainchip_pnr.prepare) and apply only the
named placement overrides. collect: read every STA step's per-corner metrics
from the run directory. The flow stops before detailed routing, so its timing
uses global-route parasitics; it measures direction, not acceptance.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def prepare(mapped,netlist,out,overrides):
    from prepare_pcie_mainchip_pnr import prepare as p
    r=p(Path(mapped),Path(netlist),Path(out))
    cfg=json.loads((Path(out)/'config.json').read_text())
    ov=json.loads(overrides)
    before={k:cfg.get(k)for k in ov}
    cfg.update(ov);(Path(out)/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps(dict(macros=len(r['macros']),overrides=ov,before=before)))
def collect(run,out):
    rows=[]
    for d in sorted(Path(run).iterdir()):
        s=d/'state_out.json'
        if not s.is_file():continue
        m=json.loads(s.read_text()).get('metrics',{})
        pick={k:v for k,v in m.items()if any(k.startswith(p)for p in('timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count','design__max_slew_violation__count','design__max_cap_violation__count','design__max_fanout_violation__count','design__instance__count','route__','global_route__','design__instance__utilization'))}
        rows.append(dict(step=d.name,metrics=pick))
    Path(out).write_text(json.dumps(rows,indent=1)+'\n')
    for r in rows:
        if 'sta' in r['step'].lower()or 'resizer' in r['step'].lower():
            ws={k.split('corner:')[-1]:round(v,3)for k,v in r['metrics'].items()if k.startswith('timing__setup__ws__corner')}
            print(r['step'],ws)
if __name__=='__main__':
    {'prepare':prepare,'collect':collect}[sys.argv[1]](*sys.argv[2:])
