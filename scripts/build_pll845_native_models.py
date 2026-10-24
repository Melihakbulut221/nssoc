#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned whole-PLL LV/HV MOS and actual area/perimeter tap compact parameters."""
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as base
from build_pcie_local_vco_hybrid_v6 import statements,number,require
MOS=('sg13_lv_nmos','sg13_hv_nmos','sg13_lv_pmos','sg13_hv_pmos')
NATIVE_ORDER=dict(base.NATIVE_ORDER,**{m:['S','G','D','B']for m in MOS})
MODEL_ORDER=dict(base.MODEL_ORDER,**{m:['D','G','S','B']for m in MOS})
MODEL_PINS=dict(base.MODEL_PINS)
MODEL_PINS['libs.tech/ngspice/models/sg13g2_moslv_mod.lib']='124c48af28aee8f4788170b50dbb4d798e7d830c6bb37516f749e16f676fa9db'
def model_params(device,tech):
 kind=device['model'];p=device['parameters']
 if kind in MOS:
  require(set(p)=={'L','W','AS','AD','PS','PD','rfmode'},'MOS native parameter census changed')
  require(p['rfmode']==0,'Only actual non-RF MOS native instances bound here')
  require(all(p[k]>0 for k in ('L','W','AS','AD','PS','PD')),'Missing/nonpositive actual MOS geometry')
  # One native extracted transistor per instance; native AS/AD already account
  # for actual shared geometry. Do not invoke model default-area estimation.
  return {k.lower():format(v,'f')+('p'if k in ('AS','AD')else'u'if k in ('L','W','PS','PD')else'')
          for k,v in p.items()}|dict(ng='1',m='1')
 if kind in ('ptap1','ntap1'):
  require(set(p)=={'A','P'}and p['A']>0 and p['P']>0,'Invalid native tap area/perimeter')
  area=p['A']*Decimal('1e-12');perimeter=p['P']*Decimal('1e-6')
  ra=number(tech[kind+'_raspec']);rp=number(tech[kind+'_rpspec'])
  require(ra>0 and rp>0,'Invalid pinned tap model coefficients')
  resistance=1/(area/ra+perimeter/rp)
  # Pinned PDK ptap1/ntap1 subcircuits use only R. w/l are explicitly unused;
  # no fictitious rectangular dimensions or fixed-size substitutions are passed.
  return dict(R=format(resistance,'f'))
 return base.model_params(device,tech)
