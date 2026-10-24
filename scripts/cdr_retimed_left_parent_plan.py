#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same41source cards/394devices with the verified left-output physical sampler."""
import copy
import cdr_retimed_parent_plan as original
TYPES=copy.deepcopy(original.TYPES)
TYPES['sampler']['top']='nssoc_rx_sampler_hbt_v2_left_v1'
def build():
    plan=original.build();plan['types']=copy.deepcopy(TYPES)
    return plan
def verify(plan):
    assert plan==build(),'Left-output physical hierarchy differs from frozen native PD source'
    return True
def controls():
    prior=original.controls();p=build();verify(p)
    assert p['nodes']==prior['plan']['nodes']and p['source_sha256']==prior['plan']['source_sha256']
    assert sum(n['kind']=='sampler'for n in p['nodes'])==4
    bad=copy.deepcopy(p);bad['types']['sampler']['top']='nssoc_rx_sampler_hbt_v2_compact_v1'
    try:verify(bad)
    except AssertionError:pass
    else:raise AssertionError('Accepted old sampler physical identity')
    return dict(status='PASS_ORIGINAL_SOURCE_CONTROLS_AND_EXACT_FOUR_LEFT_OUTPUT_PHYSICAL_IDENTITIES',
        original_controls=prior,rejected_additional=['old_sampler_physical_top'],plan=p,full_phy_accepted=False)
