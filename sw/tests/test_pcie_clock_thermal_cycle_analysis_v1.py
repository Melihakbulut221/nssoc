# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import analyze_pcie_clock_thermal_cycles_v1 as m


def fixture():
    t=np.linspace(0,10e-9,20001)
    c=np.sin(2*np.pi*7.7e9*t)
    return t,c,12.6+.04*np.sin(2*np.pi*7.7e9*t+.7)


def test_periodic_ripple_is_not_secular_drift():
    t,c,v=fixture();r=m.cycles(t,c,v,1e-9,9e-9)
    assert r['max']-r['min']>.079
    assert r['max_abs_adjacent_mean_rate_per_ns']<2e-6


@pytest.mark.parametrize('rate',[-.02,.02])
def test_real_mean_drift_is_preserved(rate):
    t,c,v=fixture();r=m.cycles(t,c,v+rate*t*1e9,1e-9,9e-9)
    assert abs(r['signed_first_last_rate_per_ns']-rate)<2e-6


def test_late_drift_cannot_hide_in_wholewindow_mean():
    t,c,v=fixture();r=m.cycles(t,c,v+.04*np.maximum(t-7e-9,0)*1e9,1e-9,9e-9)
    assert r['max_abs_adjacent_mean_rate_per_ns']>.039


@pytest.mark.parametrize('fault',['no_clock','nonfinite','duplicate_time','missing_start','missing_end','wrong_length'])
def test_reject_invalid_input(fault):
    t,c,v=fixture()
    if fault=='no_clock':c[:]=1
    elif fault=='nonfinite':v[-3]=np.nan
    elif fault=='duplicate_time':t[-3]=t[-4]
    elif fault=='missing_start':t=t[10000:];c=c[10000:];v=v[10000:]
    elif fault=='missing_end':t=t[:10000];c=c[:10000];v=v[:10000]
    elif fault=='wrong_length':v=v[:-1]
    with pytest.raises(ValueError):m.cycles(t,c,v,1e-9,9e-9)
