#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact native LV MOS extension; preserves the immutable converter for other devices."""
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as base
from build_pcie_local_vco_hybrid_v6 import *
NATIVE_ORDER=dict(base.NATIVE_ORDER,sg13_lv_nmos=['S','G','D','B'])
MODEL_ORDER=dict(base.MODEL_ORDER,sg13_lv_nmos=['D','G','S','B'])
MODEL_PINS=dict(base.MODEL_PINS)
MODEL_PINS['libs.tech/ngspice/models/sg13g2_moslv_mod.lib']='124c48af28aee8f4788170b50dbb4d798e7d830c6bb37516f749e16f676fa9db'
def model_params(d,tech):
    if d['model']!='sg13_lv_nmos':return base.model_params(d,tech)
    p=d['parameters']
    assert set(p)=={'L','W','AS','AD','PS','PD','rfmode'}
    assert p['L']==Decimal('.3') and p['W']in (Decimal(8),Decimal(32)) and p['rfmode']==0
    assert all(p[k]>0 for k in ('AS','AD','PS','PD'))
    return {k.lower():format(v,'f')+('p'if k in ('AS','AD')else'u'if k in ('L','W','PS','PD')else'')for k,v in p.items()}|dict(ng='1',m='1')
