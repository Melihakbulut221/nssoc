# SPDX-License-Identifier: Apache-2.0
"""Shared-front normal composition: public all-lane barrier and epoch fault gates."""
import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_gen3_recovered_events_v2 import Link

@cocotb.test()
async def stopped_lane_keeps_normal_all_lane_barrier(d):
    p=Link(d,count=36,batch=12);p.paused[3]=True
    try:
        await p.start(auto_arm=False)
        await Timer(200000,unit="ps")
        assert int(d.lanes_ready_o.value)==int(d.active_o.value)==0,"Normal path released before all common domains were ready"
        assert int(d.event_valid_o.value)==int(d.tlp_valid_o.value)==int(d.fault_o.value)==0
        p.paused[3]=False;await p.arm()
        await p.until(lambda:p.ends==1)
        assert p.event_count==36 and p.starts==p.stops==1
        assert int(d.equivalent_o.value)==int(d.normal_equivalent_o.value)==1
    finally:await p.close()

@cocotb.test()
async def early_arm_faults_both_compositions_and_reset_recovers(d):
    p=Link(d,count=36,batch=12);p.paused[3]=True;p.allow_fault=True
    try:
        await p.start(auto_arm=False)
        await p.until(lambda:not int(d.common_clk_i.value))
        d.arm_i.value=1
        await p.until(lambda:int(d.common_clk_i.value))
        await Timer(1,unit="ps");d.arm_i.value=0
        await p.until(lambda:int(d.fault_o.value))
        assert int(d.event_valid_o.value)==int(d.tlp_valid_o.value)==0,"Early arm leaked owned output"
        p.enabled=[False]*4;d.reset_i.value=1;p.paused[3]=False
        await Timer(50000,unit="ps")
        p.allow_fault=False;d.reset_i.value=0
        await p.arm();await p.until(lambda:p.ends==1)
        assert p.event_count==36 and p.starts==p.stops==1
        assert int(d.equivalent_o.value)==int(d.normal_equivalent_o.value)==1
    finally:await p.close()
