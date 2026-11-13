# SPDX-License-Identifier: Apache-2.0
"""Strict MOS-only projection for independent SRAM topology comparison.
SPICE identifiers are case-insensitive. No body/port aliasing or node merging.
Junction geometry and RC values are outside this MOS connectivity proof.
"""
import math
from audit_sram_flat_rc import scalar, require

def canonical_reference(g):
    names=list(g['nets']); lower=[n.lower() for n in names]
    require(len(set(lower))==len(names),'case-fold net collision')
    pins={n.lower():p.lower() for n,p in g['pins'].items()}
    require(len(set(pins.values()))==len(pins),'case-fold pin collision')
    require(set(pins)<=set(lower),'pin without net')
    devices=[]
    for d in g['devices']:
        require(all(math.isfinite(d[k]) and d[k]>0 for k in ['w','l']),'invalid dimensions')
        x={**d,'model':d['model'].lower(),**{k:d[k].lower() for k in ['D','G','S','B']}}
        devices.append(x)
    netset=set(lower)
    require(all(d[k] in netset for d in devices for k in ['D','G','S','B']),'terminal without net')
    return dict(nets={n:n for n in lower},pins=pins,devices=devices,maximum_float_normalization_um=g['maximum_float_normalization_um'])

def graph_from_flat(m,expected_mos):
    require(type(expected_mos) is int and expected_mos>0,'invalid expected count')
    require(not m['R'],'collapse and audit resistance separately before MOS projection')
    require(len(m['mos'])==expected_mos,'MOS count differs from independent reference')
    require(len(set(m['ports']))==len(m['ports']),'duplicate port')
    devices=[];nets=set(m['ports']);maxerr=0
    for name,r in m['mos'].items():
        p=r['params']
        require({'w','l'}<=set(p),'missing W/L')
        require(set(p)<={'w','l','ad','as','pd','ps','m','nf'},'unsupported MOS parameters')
        for k in ['m','nf']:
            if k in p:require(scalar(p[k])==1,'multiplicity/fingers not represented by projection')
        w,l=[scalar(p[k])*1e6 for k in ['w','l']];rw,rl=round(w,12),round(l,12)
        maxerr=max(maxerr,abs(w-rw),abs(l-rl))
        require(rw>0 and rl>0 and maxerr<1e-12,'dimension normalization loss')
        require(len(r['nodes'])==4,'non-four-terminal MOS')
        devices.append(dict(name=name,model=r['model'],w=rw,l=rl,**dict(zip(['D','G','S','B'],r['nodes']))));nets.update(r['nodes'])
    return canonical_reference(dict(nets={n:n for n in nets},pins={p:p for p in m['ports']},devices=devices,maximum_float_normalization_um=maxerr))
