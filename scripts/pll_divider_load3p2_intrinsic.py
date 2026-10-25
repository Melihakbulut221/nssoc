#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native divider intrinsic 91 devices with finite body contacts; no wire RC."""
import argparse,json,os,re
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
from cloud_tx_driver_localpins_intrinsic import resistance,PDK
from pll_divider_load3p2_native import ORDER,PORTS
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
def nodes(r):return [r['terminals'][t]['logical_net']for t in ORDER[r['model']]]
def build(rows,tech,top):
    lines=['* Actual native divider 91-device intrinsic model; not wire RC or qualification.','.subckt '+top+' '+' '.join(PORTS)];bindings=[]
    for r in rows:
        model=r['model'];params={'R':str(resistance(r,tech))}if model=='ptap1'else compact.model_params(r,tech)
        name='XD'+str(r['id']);n=nodes(r);lines.append(' '.join([name,*n,model,*[k+'='+v for k,v in params.items()]]))
        bindings.append(dict(instance=name,native_id=r['id'],model=model,named_terminal_order=ORDER[model],nodes=n,native_parameters=r['parameters'],compact_parameters=params))
    return '\n'.join(lines+['.ends '+top,'']),bindings

def verify(text,rows,tech,top):
    lines=compact.statements(text);assert lines[0]==['.subckt',top,*PORTS]and lines[-1]==['.ends',top],'Divider wrapper changed'
    actual={l[0]:l for l in lines[1:-1]};expected={'XD'+str(r['id']):r for r in rows}
    assert len(actual)==len(lines)-2==len(expected)==91 and set(actual)==set(expected),'Divider device missing or duplicated'
    for name,r in expected.items():
        model=r['model'];p=r['parameters'];n=nodes(r);line=actual[name]
        assert line[1:len(n)+1]==n,'Named native divider terminal changed'
        assert line[len(n)+1]==model,'Native compact model changed'
        words=line[len(n)+2:];params={k:compact.number(v)for k,v in (w.split('=',1)for w in words)}
        assert len(params)==len(words),'Duplicate compact parameter'
        if model=='npn13G2':
            assert set(params)=={'Nx','we','le'}and p['m']==1,'HBT parameter or multiplicity changed'
            assert params['Nx']==p['Nx'] and p['Nx'] in (1,2,4),'HBT Nx changed'
            for k in ['we','le']:assert params[k]==Decimal(str(p[k]))*Decimal('1e-6'),'HBT physical geometry changed'
        elif model=='rppd':
            assert set(params)=={'w','l','ps','b','m','sw_et'},'Resistor parameter census changed'
            for k in ['w','l','ps']:assert abs(params[k]-Decimal(str(p[k]))*Decimal('1e-6'))<=Decimal('1e-20'),'Resistor native geometry changed'
            assert params['b']==p['b']==0 and params['m']==p['m']==params['sw_et']==1,'Resistor multiplier/body/self-heating changed'
        elif model=='cap_cmim':
            assert set(p)=={'w','l','A','P','m'} and p['m']==1,'MIM parameter census or multiplier changed'
            assert set(params)=={'w','l'},'MIM compact parameters changed'
            for k in ['w','l']:assert abs(params[k]-Decimal(str(p[k]))*Decimal('1e-6'))<=Decimal('1e-20'),'MIM physical geometry changed'
            assert abs(Decimal(str(p['A']))-Decimal(str(p['w']))*Decimal(str(p['l'])))<=Decimal('1e-10'),'MIM native area changed'
            assert abs(Decimal(str(p['P']))-2*(Decimal(str(p['w']))+Decimal(str(p['l']))))<=Decimal('1e-10'),'MIM native perimeter changed'
        else:
            assert model=='ptap1'and set(params)=={'R'},'Finite body contact changed'
            g=Decimal(str(p['A']))*Decimal('1e-12')/compact.number(tech['ptap1_raspec'])+Decimal(str(p['P']))*Decimal('1e-6')/compact.number(tech['ptap1_rpspec'])
            assert abs(params['R']*g-1)<=Decimal('1e-26'),'Finite body contact conductance changed'
    return dict(devices=91,hbt=34,resistors=33,mim=6,finite_contacts=18,ports=PORTS)

