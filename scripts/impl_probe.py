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
def sta_tcl(run,prepared,out):
    """Per-corner setup/hold on the post-global-route database (OpenROAD in LibreLane)."""
    import fnmatch,glob
    run,prepared=Path(run),Path(prepared)
    cfg=json.loads((run/'resolved.json').read_text())
    states=sorted(run.glob('*/state_out.json'))
    odb=None
    for s_ in states:
        o=json.loads(s_.read_text()).get('odb')
        if o:odb=o
    corners=cfg['STA_CORNERS']
    def libs(c):
        out=[]
        for k,v in cfg['LIB'].items():
            if fnmatch.fnmatch(c,k):out+=v
        for m in(cfg.get('MACROS')or{}).values():
            for k,v in(m.get('lib')or{}).items():
                if fnmatch.fnmatch(c,k):out+=v
        return list(dict.fromkeys(out))
    def val(v):
        if isinstance(v,bool):return '1'if v else '0'
        if isinstance(v,list):return ' '.join(map(str,v))
        return str(v)
    t=[f'set ::env({k}) {{{val(v)}}}'for k,v in cfg.items()if isinstance(v,(str,int,float,bool))or(isinstance(v,list)and all(isinstance(x,(str,int,float))for x in v))]
    t+=['set ::env(OPENLANE_SDC_IDEAL_CLOCKS) 0',f'read_db {odb}','define_corners '+' '.join(corners)]
    for c in corners:t+=[f'read_liberty -corner {c} {l}'for l in libs(c)]
    t+=[f'read_sdc {prepared/"physical.sdc"}','set_propagated_clock [all_clocks]']
    for layer,rc in cfg['LAYERS_RC']['*'].items():
        t.append(f'set_layer_rc -layer {layer} -resistance {rc["res"]} -capacitance {rc["cap"]}')
    for via,rc in((cfg.get('VIAS_RC')or{}).get('*')or{}).items():
        t.append(f'set_layer_rc -via {via} -resistance {rc["res"]}')
    t+=['set_routing_layers -signal Metal2-TopMetal2 -clock Metal4-TopMetal2',
        f'global_route -congestion_iterations {cfg.get("GRT_OVERFLOW_ITERS",50)} -allow_congestion',
        'estimate_parasitics -global_routing']
    for c in corners:
        t+=[f'puts "NSSOC_CORNER_BEGIN {c}"',
            f'report_checks -corner {c} -path_delay max -group_path_count 3 -format end',
            f'report_checks -corner {c} -path_delay min -group_path_count 3 -format end',
            f'report_checks -corner {c} -path_delay max -group_path_count 1 -fields {{cap slew fanout}} -digits 3',
            f'puts "NSSOC_CORNER_END {c}"']
    Path(out).write_text('\n'.join(t)+'\n');print('odb',odb,'corners',corners)
if __name__=='__main__':
    {'prepare':prepare,'collect':collect,'sta_tcl':sta_tcl}[sys.argv[1]](*sys.argv[2:])
