# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check source ordering, launch contract and whole-stage device accounting."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('mux4',ROOT/'scripts/run_cloud_tx_mux4.py')
mux4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mux4)


def points(text):
    return np.asarray([tuple(map(float,line.lstrip('+ ').split()))
                       for line in text[4:-1].splitlines() if line.strip()])


def test_four_physical_source_streams_preserve_original_bit_order_and_phase():
    bits=mux4.sequence()
    streams=[]
    for bank in range(4):
        p=points(mux4.pwl(bits[bank::4],.6,.6,4*mux4.UI,
                         mux4.START+(bank-3)*mux4.UI,invert=True))
        assert p[0].tolist()==[0,0] and p[1,0]==1e-9 and p[-1,0]==mux4.STOP
        assert np.all(np.diff(p[:,0])>0)
        streams.append(p)
    for index,bit in enumerate(bits):
        stream=streams[index%4]
        for phase in (.3,.5,.7):
            sample=mux4.START+(index+phase)*mux4.UI
            value=np.interp(sample,stream[:,0],stream[:,1])
            # Gate polarity is inverted by the physical HV common-source stage.
            assert value==pytest.approx(1.2*(1-bit),abs=1e-12)
        # A selected source is already stable before its prestage selection.
        selection=mux4.START+(index-1)*mux4.UI
        assert np.interp(selection,stream[:,0],stream[:,1])==pytest.approx(1.2*(1-bit),abs=1e-12)


def test_explicit_preclocks_select_the_original_bank_at_all_output_samples():
    selectors={}
    for name,origin,period in [('a',mux4.START-mux4.UI,2*mux4.UI),
                               ('b',mux4.START,2*mux4.UI),('final',mux4.START,mux4.UI)]:
        selectors[name]=points(mux4.pwl([int(i%2==0) for i in range(256)],1.23,.08,period,origin))
    for index in range(256):
        for phase in (.3,.5,.7):
            sample=mux4.START+(index+phase)*mux4.UI
            def choice(name):
                p=selectors[name]
                return np.interp(sample,p[:,0],p[:,1])>1.23
            bank=(0 if choice('a') else 2) if choice('final') else (1 if choice('b') else 3)
            assert bank==index%4


def test_all_native_pre_stage_devices_and_reference_are_bound():
    ports='d0p d0n d2p d2n sap san ap an avdd 0 0 ra'.split()
    name,devices=mux4.bind_devices(mux4.PRE,'xprea',ports,{'npn13g2'})
    assert len(devices)==19
    assert devices['xprea.xref']['terminals']==['ra','ra','0','0']
    assert devices['xprea.xsa_0']['terminals'][1]=='sap'
    assert devices['xprea.xap_0']['terminals'][1]=='d0p'
    assert all(row['nx'] in (1,8) for row in devices.values())
    assert all(n.startswith('xprea.') for n in devices)
