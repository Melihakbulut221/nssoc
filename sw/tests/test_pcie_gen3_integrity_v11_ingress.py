# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real original/candidate FIFO sources: valid-slot relation through full faults."""

from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_ingress_v11.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))[
    "simulate"
]


def test_exact_generated_inverse_and_wrapper_bridge():
    text = (RTL / "soc_pcie_gen3_ingress_integrity_v11.v").read_text()
    assert text == GEN["candidate"]()
    assert text.count(GEN["writer"]()) == 1
    text = text.replace(GEN["writer"](), "").replace(GEN["NEW_WRITE"], GEN["OLD_WRITE"])
    text = (
        text.replace("`default_nettype none\n", "")
        .removesuffix("`default_nettype wire\n")
        .replace("soc_pcie_gen3_ingress_integrity_v11", "soc_pcie_gen3_ingress")
    )
    assert text == GEN["SOURCE"].read_text()
    assert (RTL / "soc_pcie_gen3_framer_rx_integrity_v11.v").read_text() == GEN[
        "framer"
    ]()
    assert (RTL / "soc_pcie_gen3_continuous_rx_integrity_v11.v").read_text() == GEN[
        "wrapper"
    ]()
    for name in [
        "test_soc_pcie_gen3_continuous_rx_integrity_v10.py",
        "Makefile.soc_pcie_gen3_continuous_rx_integrity_v10",
    ]:
        parent = ROOT / "hw/soc/tb/cocotb"
        assert (parent / name.replace("_v10", "_v11")).read_text().replace(
            "integrity_v11", "integrity_v10"
        ).replace("soc_pcie_gen3_ingress_integrity_v10", "soc_pcie_gen3_ingress") == (
            parent / name
        ).read_text()


FAULTS = {
    "wrong_slot": (
        "blocks[wr_ptr]<=completed;",
        "blocks[(wr_ptr+1)%FIFO_DEPTH]<=completed;",
    ),
    "wrong_payload": (
        "blocks[wr_ptr]<=completed;",
        "blocks[wr_ptr]<=completed ^ 520'b1;",
    ),
    "lost_full_pop": (
        "if(enabled && complete_block)",
        "if(enabled && complete_block && queued<FIFO_DEPTH)",
    ),
    "early_partial_write": ("if(enabled && complete_block)", "if(enabled)"),
}


def probe(tmp_path, depth, fault):
    old = GEN["SOURCE"].read_text()
    new = (RTL / "soc_pcie_gen3_ingress_integrity_v11.v").read_text()
    if fault:
        before, after = FAULTS[fault]
        assert new.count(before) == 1
        new = new.replace(before, after)
    bench = (
        old
        + "\n"
        + new
        + """\n`timescale 1ns/1ps
module tb;
localparam DEPTH=DEPTH_VALUE;
reg clk=0,rst=0,flush=0,start=0,ready=0;reg[127:0]word=0;
wire gv,nv,ga,na,gf,nf;wire[7:0]gh,nh;wire[511:0]gp,np;
soc_pcie_gen3_ingress #(.FIFO_DEPTH(DEPTH)) gold(clk,rst,flush,start,word,gv,ready,gh,gp,ga,gf);
soc_pcie_gen3_ingress_integrity_v11 #(.FIFO_DEPTH(DEPTH)) gate(clk,rst,flush,start,word,nv,ready,nh,np,na,nf);
always #1 clk=~clk;
integer trial,k,a,seed=111005,full_pop=0,full_fault=0,valid_checks=0,restarts=0,wraps=0,hidden=0,flushes=0,resets=0;
initial begin
for(trial=0;trial<8192;trial=trial+1) begin
 @(negedge clk);#0.001;
 if({gv,ga,gf,gold.queued,gold.rd_ptr,gold.wr_ptr,gold.residual_count} !== {nv,na,nf,gate.queued,gate.rd_ptr,gate.wr_ptr,gate.residual_count})$fatal(1,"INGRESS_CONTROL_MISMATCH");
 if(gv && {gh,gp} !== {nh,np})$fatal(1,"VALID_INGRESS_SLOT_MISMATCH visible");
 for(k=0;k<DEPTH;k=k+1) begin
  a=(gold.rd_ptr+k)%DEPTH;
  if(k<gold.queued) begin
   valid_checks=valid_checks+1;
   if(gold.blocks[a] !== gate.blocks[a])$fatal(1,"VALID_INGRESS_SLOT_MISMATCH slot");
  end
 end
 if(gf && gold.blocks[0] !== gate.blocks[0]) hidden=hidden+1;
 rst=(trial%193!=75);flush=(trial%101==80);start=(trial%83==0)||(!gold.running && trial%7==0);
 // Directed full cases alternate exact full+pop replacement and invalidating
 // no-pop fault; long random stretches also wrap both physical pointers.
 if(gold.queued==DEPTH)ready=gold.complete_block && ((trial/83)%2)==0;
 else if(trial%83<4*DEPTH+4)ready=0;
 else ready=($random(seed)&7)>1;
 for(k=0;k<4;k=k+1)word[k*32+:32]=$random(seed);
 #0.001;
 if(gold.enabled&&gold.complete_block&&gold.queued==DEPTH)begin
  if(ready)full_pop=full_pop+1;else full_fault=full_fault+1;
 end
 if(start)restarts=restarts+1;
 if(flush)flushes=flushes+1;
 if(!rst)resets=resets+1;
 if(gold.pop && gold.rd_ptr==DEPTH-1)wraps=wraps+1;
end
if(full_pop<5||full_fault<5||valid_checks<1000||restarts<20||wraps<20||hidden<5||flushes<20||resets<20)$fatal(1,"INGRESS_COVERAGE fullpop=%0d fullfault=%0d valid=%0d restart=%0d wrap=%0d hidden=%0d flush=%0d reset=%0d",full_pop,full_fault,valid_checks,restarts,wraps,hidden,flushes,resets);
$display("PASS_VALID_INGRESS_QUARANTINE depth=%0d cycles=8192 fullpop=%0d fullfault=%0d valid=%0d restart=%0d wrap=%0d hidden=%0d flush=%0d reset=%0d",DEPTH,full_pop,full_fault,valid_checks,restarts,wraps,hidden,flushes,resets);$finish;
end endmodule
""".replace("DEPTH_VALUE", str(depth))
    )
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "VALID_INGRESS_SLOT_MISMATCH" in log, log
    else:
        assert result.returncode == 0 and "PASS_VALID_INGRESS_QUARANTINE" in log, log


@pytest.mark.parametrize("depth", [1, 3, 4])
def test_actual_fifo_valid_slots_full_pop_fault_reset(tmp_path, depth):
    probe(tmp_path, depth, None)


@pytest.mark.parametrize("fault", list(FAULTS))
def test_actual_fifo_writer_mutations_reject(tmp_path, fault):
    probe(tmp_path, 4, fault)
