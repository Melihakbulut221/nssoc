# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A stage-delay diagnosis must preserve ambiguous crossings and source phase."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('stage',Path(__file__).resolve().parents[2]/'scripts/analyze_cloud_tx_tree_wave.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)


def test_linear_crossing_interpolation_retains_every_event():
    t=np.arange(9,dtype=float);y=np.asarray([-1,1,-1,1,-1,1,-1,1,-1],dtype=float)
    assert stage.crossings(t,y,0,0,8)==[.5,2.5,4.5,6.5]
    assert stage.crossings(t,y,.5,2,5)==[2.75,4.75]
    assert stage.crossings(t,y,2,0,8)==[]


@pytest.mark.parametrize('fault',['unordered','nonfinite','coverage'])
def test_invalid_capture_is_rejected(fault):
    t=np.arange(9,dtype=float);y=t-4
    begin,end=0,8
    if fault=='unordered':t[4]=t[3]
    elif fault=='nonfinite':y[4]=np.nan
    else:end=9
    with pytest.raises(AssertionError):stage.crossings(t,y,0,begin,end)


def test_stage_delay_is_diagnostic_and_does_not_move_original_sample():
    t=np.linspace(0,stage.STOP,136001)
    bits=[int(i%2==0) for i in range(256)]
    def signal(delay,amplitude):
        phase=(t-stage.START-delay)/stage.UI
        return amplitude*np.cos(np.pi*(phase-.5))
    # Crossings occur at 5, 15 and 30ps after the original bit boundary.
    clock=signal(5e-12,.16);mux=signal(15e-12,.3);output=signal(30e-12,.3)
    r=stage.transition_table(t,clock,mux,output,bits)
    assert not r['ambiguous_events']
    assert r['summary']['clock_to_mux_zero_ps']['median']==pytest.approx(10,abs=.01)
    assert r['summary']['mux_to_tx_zero_ps']['median']==pytest.approx(15,abs=.01)
    assert r['original_03ui_below_100mv']==255
    assert all(x['at_original_03ui_v']<.1 for x in r['events'])
