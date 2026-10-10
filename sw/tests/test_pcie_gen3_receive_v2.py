# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual public-port boundary/alias controls for the shifted bounded RX v2."""

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = Path(
    os.environ.get(
        "PCIE_RX_V2_RTL", str(ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_v2.v")
    )
)


def stp(length, sequence):
    remainder = int(f"{length:011b}"[::-1], 2) << 4
    for bit in range(14, 3, -1):
        if remainder & (1 << bit):
            remainder ^= 0b10011 << (bit - 4)
    parity = (length.bit_count() + remainder.bit_count()) % 2
    return bytes(
        (
            (length & 15) * 16 + 15,
            (length >> 4) + parity * 128,
            remainder * 16 + (sequence >> 8),
            sequence & 255,
        )
    )


def packet(size, sequence=0xFED):
    four = size > 4114
    payload = size - 18 - (4 if four else 0)
    assert 0 <= payload <= 4096 and payload % 4 == 0
    count = (payload // 4 if payload else 1) & 1023
    data = bytes(
        (
            sequence >> 8,
            sequence & 255,
            (0x40 if payload else 0) | (0x20 if four else 0),
            0,
            count >> 8,
            count & 255,
        )
    )
    data += bytes.fromhex("12345678 01020304") + (
        bytes.fromhex("11223344") if four else b""
    )
    data += bytes((index * 31 + 9) % 256 for index in range(payload))
    data += bytes.fromhex("7a11bc83")  # Framing treats caller CRC bytes as opaque.
    assert len(data) == size
    return data


def bench(capacity, header_alias=False):
    maximum = 4 * ((capacity + 2) // 4) - 2
    first = packet(146 if header_alias else maximum)
    if header_alias:
        changed = bytearray(first)
        changed[5] = 96  # 18+384=402; an8-bit header_bytes wrongly aliases146.
        first = bytes(changed)
    second = packet(18, 0x123)
    dllp = bytes.fromhex("001122334455")
    stream = bytes(44) + stp((len(first) + 2) // 4, 0xFED) + first[2:]
    if not header_alias:
        stream += b"\xf0\xac" + dllp + stp(5, 0x123) + second[2:]
    stream += bytes(4)
    stream += bytes(-len(stream) % 64)
    expected = b"" if header_alias else first + dllp + second
    blocks = [
        sum(
            int.from_bytes(stream[offset + lane : offset + 64 : 4], "little")
            << (lane * 128)
            for lane in range(4)
        )
        for offset in range(0, len(stream), 64)
    ]
    expected_assignments = "\n".join(
        f" expected[{i}]=8'h{x:02x};" for i, x in enumerate(expected)
    )
    block_assignments = "\n".join(
        f" blocks[{i}]=512'h{x:0128x};" for i, x in enumerate(blocks)
    )
    n = len(expected)
    return f"""// Generated actual-port control; no internal-register references.
module tb;
 reg clk_i=0,rst_ni=0,flush_i=0,stream_start_i=0,stream_abort_i=0;
 reg block_valid_i=0,block_error_i=0,ready_i=0;
 reg [7:0] headers_i=8'haa;reg [511:0] payload_i=0;
 wire block_ready_o,valid_o,sop_o,eop_o,dllp_o,packet_good_o,packet_nullified_o;
 wire [7:0] data_o;wire [11:0] sequence_o;
 wire framing_error_o,stream_end_o,active_o,halted_o;
 soc_pcie_gen3_framer_rx_v2 #(.MAX_ENCODED_BYTES({capacity})) dut(.*);
 reg [7:0] expected[0:{max(1, n) - 1}];reg [511:0] blocks[0:{len(blocks) - 1}];
 integer received=0,goods=0,errors=0,nulls=0,cycles=0,i,j;
 reg held=0;reg [10:0] held_value;
 task tick;
 begin
   ready_i=(cycles%7==0 || cycles%7==3 || cycles%7==4);
   #5;
   if(rst_ni && !stream_start_i && !flush_i) begin
     if(held && (!valid_o || {{data_o,sop_o,eop_o,dllp_o}}!==held_value))
       $fatal(1,"held packet changed");
     held=valid_o && !ready_i;held_value={{data_o,sop_o,eop_o,dllp_o}};
     if(valid_o && ready_i) begin
       if(received>={n}) $fatal(1,"unexpected packet delivery/header alias");
       if(data_o!==expected[received]) $fatal(1,"byte or sequence mismatch at%0d",received);
       if(sop_o !== (received==0 || received=={len(first)} || received=={len(first) + 6}))
         $fatal(1,"SOP mismatch");
       if(eop_o !== (received=={len(first) - 1} || received=={len(first) + 5} || received=={n - 1}))
         $fatal(1,"EOP/count mismatch");
       if(dllp_o !== (received>={len(first)} && received<{len(first) + 6}))
         $fatal(1,"packet kind mismatch");
       received=received+1;
     end
   end
   clk_i=1;#5;
   if(rst_ni) begin
     goods=goods+packet_good_o;errors=errors+framing_error_o;nulls=nulls+packet_nullified_o;
   end
   clk_i=0;cycles=cycles+1;
   if(cycles>60000) $fatal(1,"bounded port progress timeout");
 end
 endtask
 initial begin
{expected_assignments}
{block_assignments}
   tick;tick;rst_ni=1;stream_start_i=1;tick;stream_start_i=0;
   for(i=0;i<{len(blocks)};i=i+1) begin
     if(!halted_o) begin
       payload_i=blocks[i];block_valid_i=1;#1;
       while(!block_ready_o && !halted_o) tick;
       if(!halted_o) tick;
       block_valid_i=0;tick;
     end
   end
   for(j=0;j<60000 && received<{n} && !halted_o;j=j+1) tick;
   for(j=0;j<100;j=j+1) tick;
   if({int(header_alias)}) begin
     if(errors!=1 || goods!=0 || received!=0 || !halted_o)
       $fatal(1,"wide header-length alias was not rejected");
   end else begin
     if(errors!=0 || nulls!=0 || goods!=3 || received!={n} || halted_o)
       $fatal(1,"boundary/consume mismatch received%0d good%0d error%0d",received,goods,errors);
   end
   $display("PASS_BOUNDED_RX_V2_PORTS capacity={capacity} alias={int(header_alias)}");$finish;
 end
endmodule
"""


def run_ports(directory, source, capacity=150, header_alias=False):
    directory.mkdir()
    rtl = directory / "candidate.v"
    rtl.write_text(source)
    tb = directory / "tb.v"
    tb.write_text(bench(capacity, header_alias))
    installed = shutil.which("iverilog")
    tools = (
        Path(installed).parent if installed else ROOT / "hw/soc/tools/oss-cad-suite/bin"
    )
    assert all(os.access(tools / t, os.X_OK) for t in ("iverilog", "vvp"))

    def pin(path):
        data = path.read_bytes()
        return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    inputs = {
        str(path): pin(path) for path in (rtl, tb, tools / "iverilog", tools / "vvp")
    }
    command = [
        str(tools / "iverilog"),
        "-g2012",
        "-s",
        "tb",
        "-o",
        str(directory / "sim.vvp"),
        str(rtl),
        str(tb),
    ]
    compile_result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20
    )
    (directory / "compile.log").write_text(compile_result.stdout)
    assert compile_result.returncode == 0, compile_result.stdout
    process = subprocess.run(
        [str(tools / "vvp"), str(directory / "sim.vvp")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )
    (directory / "simulation.log").write_text(process.stdout)
    assert inputs == {path: pin(Path(path)) for path in inputs}
    (directory / "result.json").write_text(
        json.dumps(
            dict(
                returncode=process.returncode,
                capacity=capacity,
                header_alias=header_alias,
                command=command,
                inputs=inputs,
                inputs_rechecked=True,
            ),
            indent=2,
        )
        + "\n"
    )
    return process


@pytest.mark.parametrize(
    "capacity", [18, 30, 31, 32, 33, 126, 127, 128, 129, 150, 254, 255, 256, 257, 4118]
)
def test_actual_boundary_capacity_and_packed_successor(tmp_path, capacity):
    result = run_ports(tmp_path / "capture", RTL.read_text(), capacity)
    assert result.returncode == 0 and "PASS_BOUNDED_RX_V2_PORTS" in result.stdout


def test_actual_wide_header_alias_rejected(tmp_path):
    result = run_ports(tmp_path / "capture", RTL.read_text(), header_alias=True)
    assert result.returncode == 0 and "PASS_BOUNDED_RX_V2_PORTS" in result.stdout


FAULTS = (
    (
        "position_truncation",
        "$clog2(MAX_ENCODED_BYTES+1)",
        "$clog2(MAX_ENCODED_BYTES+1)-1",
        False,
    ),
    ("header_alias", "reg [12:0] header_bytes;", "reg [POS_W-1:0] header_bytes;", True),
    (
        "no_shift",
        "block_data <= {8'b0,block_data[511:392],8'b0,block_data[383:264],\n                  8'b0,block_data[255:136],8'b0,block_data[127:8]};",
        "block_data <= block_data;",
        False,
    ),
    ("repeat_lane_byte", "8'b0,block_data[383:264]", "8'b0,block_data[375:256]", False),
    (
        "skip_word",
        "block_data <= {8'b0,block_data[511:392],8'b0,block_data[383:264],\n                  8'b0,block_data[255:136],8'b0,block_data[127:8]};",
        "block_data <= {16'b0,block_data[511:400],16'b0,block_data[383:272],16'b0,block_data[255:144],16'b0,block_data[127:16]};",
        False,
    ),
    (
        "lose_successor",
        "               packet_good_o<=1;state<=EMIT;read_pos<=0;",
        "               packet_good_o<=1;state<=EMIT;read_pos<=0;consume_word();",
        False,
    ),
    (
        "shift_while_emit",
        "if(valid_o && ready_i) begin",
        "if(valid_o && ready_i) begin consume_word();",
        False,
    ),
    (
        "tlp_first_byte",
        "               packet_good_o<=1;state<=EMIT;read_pos<=0;read_data<=packet[0];",
        "               packet_good_o<=1;state<=EMIT;read_pos<=0;read_data<=packet[1];",
        False,
    ),
    (
        "dllp_first_byte",
        "consume_word();packet_good_o<=1;state<=EMIT;read_pos<=0;read_data<=packet[0];",
        "consume_word();packet_good_o<=1;state<=EMIT;read_pos<=0;read_data<=packet[2];",
        False,
    ),
    (
        "output_reload",
        "read_data<=packet[read_pos+1'b1]",
        "read_data<=packet[read_pos]",
        False,
    ),
    (
        "output_stall",
        "if(valid_o && ready_i) begin",
        "if(valid_o) begin",
        False,
    ),
)


@pytest.mark.parametrize("name,before,after,alias", FAULTS, ids=[x[0] for x in FAULTS])
def test_real_width_and_shift_fault_rejected(tmp_path, name, before, after, alias):
    source = RTL.read_text()
    assert source.count(before) == 1
    result = run_ports(
        tmp_path / "capture", source.replace(before, after), header_alias=alias
    )
    assert result.returncode != 0 and "FATAL:" in result.stdout
    assert "PASS_BOUNDED_RX_V2_PORTS" not in result.stdout


def test_all_supported_capacity_length_pairs_preserve_reachable_bounds():
    # Induction step is write_pos+=4 while remaining_dw decreases by1; enumerate
    # every accepted(capacity,L), check both monotone endpoints and final count.
    pairs = 0
    for capacity in range(18, 4119):
        width = capacity.bit_length()  # ceil(log2(capacity+1)).
        for length in range(5, min(1152, (capacity + 2) // 4 + 1)):
            count = 4 * length - 2
            last_start = 2 + 4 * (length - 2)
            assert 18 <= count <= capacity < 1 << width
            assert last_start + 3 == count - 1 < capacity
            assert last_start + 4 == count < 1 << width
            assert count - 1 + 1 == count  # EMIT stops before any additional increment.
            pairs += 1
    assert pairs == 2104326
