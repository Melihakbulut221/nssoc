# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial arithmetic and actual full-parser arbitrary-state miter."""

import hashlib
import itertools
import random
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_crc_candidates_v3.py"))


def test_all_abstract_four_step_crc_paths():
    """Overapproximate every binary parser state/counter/header combination.

    CRC never selects a state. A TLP step can continue, finish into LOOK, or
    fail the header/length check; allowing all three at every step includes
    impossible paths as well as every actual counter value, including zero
    wrapping to2047. Token classifications are also unconstrained here.
    """
    checked = 0
    for initial in range(4):
        for choices in itertools.product(range(8), repeat=4):
            # TOKEN,TLP,LOOK,DLLP = 0,1,2,3. Branch3 is the TLP-end error.
            for endings in itertools.product(range(3), repeat=4):
                state, stopped, origin = initial, False, -1
                lcrc = ("carry", ())
                dllp = ("carry", ())
                for j, token in enumerate(choices):
                    if stopped:
                        continue
                    if state == 2:
                        # This verdict observes old CRC before any same-word
                        # STP updates the origin. EDB consumes this word.
                        before_verdict = lcrc
                        if token == 4:
                            state = 0
                            assert lcrc == before_verdict
                            continue
                        if token not in (0, 1, 2, 3):
                            stopped = True
                            continue
                        state = 0
                    if state == 0:
                        if token == 1:  # Accepted STP only.
                            origin = j
                            lcrc = (j, ())
                            state = 1
                        elif token == 2:  # SDP seed includes two body bytes.
                            dllp = (j, ())
                            state = 3
                        elif token != 0:  # EDS or error stops further steps.
                            stopped = True
                    elif state == 1:
                        seed, prior = lcrc
                        lcrc = (seed, prior + (j,))
                        candidate = (
                            "carry" if origin == -1 else origin,
                            tuple(range(origin + 1, j + 1)),
                        )
                        assert lcrc == candidate
                        if endings[j] == 1:
                            state = 2
                        elif endings[j] == 2:
                            stopped = True
                    else:
                        seed, prior = dllp
                        dllp = (seed, prior + (j,))
                        assert dllp == ("carry" if j == 0 else j - 1, (j,))
                        state = 0
                checked += 1
    assert checked == 4 * 8**4 * 3**4
    # An initially ending/failure-gated parser performs no updates at all.
    # These two guards therefore add only the identity transform.


def serial(state, data, width, bits, polynomial):
    # Independent normal-polynomial long division, with reflected wire bits.
    remainder = int(f"{state:0{width}b}"[::-1], 2)
    normal = int(f"{polynomial:0{width}b}"[::-1], 2)
    for bit in range(bits):
        remainder ^= ((data >> bit) & 1) << (width - 1)
        remainder <<= 1
        if remainder & (1 << width):
            remainder ^= (1 << width) | normal
    return int(f"{remainder:0{width}b}"[::-1], 2)


def simulate(tmp_path, source, extras=()):
    tool = shutil.which("iverilog")
    runtime = shutil.which("vvp")
    assert tool and runtime, "Actual Icarus execution is required"
    path = tmp_path / "tb.v"
    path.write_text(source)
    output = tmp_path / "sim.vvp"
    with (tmp_path / "compile.log").open("w") as log:
        result = subprocess.run(
            [
                tool,
                "-g2012",
                "-s",
                "tb",
                "-o",
                str(output),
                str(path),
                *map(str, extras),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    assert result.returncode == 0, (tmp_path / "compile.log").read_text()
    with (tmp_path / "run.log").open("w") as log:
        result = subprocess.run(
            [runtime, str(output)], stdout=log, stderr=subprocess.STDOUT
        )
    return result, (tmp_path / "run.log").read_text()


def test_generated_source_and_frozen_wrapper_bridge():
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v3.v").read_text()
    assert GEN["functions"]() in source and GEN["candidates"]() in source
    for stem in (
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_",
    ):
        suffix = ".v" if stem.startswith("hw/soc/rtl") else ".py"
        assert (ROOT / (stem + "v3" + suffix)).read_text().split(
            "# BEGIN V3 ALIGNMENT CASE", 1
        )[0].replace("integrity_v3", "integrity_v2") == (
            ROOT / (stem + "v2" + suffix)
        ).read_text() + ("\n\n" if suffix == ".py" else "")
    # Explicit inverse of every parser edit: the old parser/storage/handshake body is conserved.
    source = source.replace(
        "soc_pcie_gen3_framer_rx_integrity_v3", "soc_pcie_gen3_framer_rx_integrity_v2"
    )
    old = (RTL / "soc_pcie_gen3_framer_rx_integrity_v2.v").read_text()
    old_functions = old[
        old.index(" // BEGIN GENERATED CRC FUNCTIONS") : old.index(
            " // END GENERATED CRC FUNCTIONS"
        )
        + len(" // END GENERATED CRC FUNCTIONS\n")
    ]
    source = source.replace(GEN["functions"](), old_functions).replace(
        GEN["candidates"](), ""
    )
    source = source.replace(";crc_origin=0;", ";")
    source = source.replace(
        "lcrc_n=crc_seed[j];crc_origin=j+1;",
        "lcrc_n=crc32_16(32'hffffffff,{word[31:24],4'b0,word[19:16]});",
    )
    source = source.replace(
        "dllp_crc_n=dllp_seed[j];", "dllp_crc_n=crc16_16(16'hffff,word[31:16]);"
    )
    source = source.replace(
        "dllp_crc_n=dllp_finish[j];", "dllp_crc_n=crc16_32(dllp_crc_n,word);"
    )
    source = source.replace(
        """case(crc_origin)
               0:lcrc_n=crc_carry[j];
               1:lcrc_n=crc_stp0[j];
               2:lcrc_n=crc_stp1[j];
               3:lcrc_n=crc_stp2[j];
               default:lcrc_n=crc_stp3[j];
             endcase""",
        "lcrc_n=crc32_32(lcrc_n,word);",
    )
    assert source == old


@pytest.mark.parametrize("fault", [None, "state_bit", "data_bit", "polynomial"])
def test_actual_crc_basis_and_random_vectors(tmp_path, fault):
    functions = GEN["functions"]()
    if fault == "state_bit":
        functions = functions.replace("state[0]", "state[1]", 1)
    elif fault == "data_bit":
        functions = functions.replace("data[0]", "data[1]", 1)
    elif fault == "polynomial":
        functions = functions.replace("crc32_128[0]=", "crc32_128[0]=1'b1^", 1)
    lines = ["module tb;", functions, "initial begin"]
    count = 0
    rng = random.Random(932791)
    for width, polynomial, counts in GEN["TRANSFORMS"]:
        for bits in counts:
            vectors = (
                [(0, 0)]
                + [(1 << i, 0) for i in range(width)]
                + [(0, 1 << i) for i in range(bits)]
            )
            vectors += [
                (rng.getrandbits(width), rng.getrandbits(bits)) for _ in range(64)
            ]
            for state, data in vectors:
                expected = serial(state, data, width, bits, polynomial)
                lines.append(
                    f"if(crc{width}_{bits}({width}'h{state:x},{bits}'h{data:x})!=={width}'h{expected:x}) $fatal(1,\"CRC_VECTOR_{count}\");"
                )
                count += 1
    lines += [f'$display("PASS {count} ACTUAL_CRC_VECTORS");$finish;end endmodule']
    result, log = simulate(tmp_path, "\n".join(lines))
    if fault:
        assert result.returncode != 0 and "CRC_VECTOR_" in log
    else:
        assert result.returncode == 0 and f"PASS {count}" in log


PARSER_INPUTS = {
    "state": 2,
    "lcrc": 32,
    "dllp_crc": 16,
    "current_block": 512,
    "slice": 2,
    "write_ptr": 7,
    "commit_ptr": 7,
    "packet_tag": 7,
    "packet_bytes": 13,
    "expected_bytes": 13,
    "remaining": 11,
    "packet_sequence": 12,
    "header_first": 1,
    "header_bad": 1,
    "ending": 1,
}
PARSER_OUTPUTS = (
    "lcrc_n",
    "dllp_crc_n",
    "state_n",
    "commit_n",
    "tag_n",
    "bytes_n",
    "expected_n",
    "remaining_n",
    "sequence_n",
    "header_first_n",
    "header_bad_n",
    "ending_n",
    "write_data",
    "write_keep",
    "write_sop",
    "write_eop",
    "write_dllp",
    "write_sequence",
    "write_tags",
    "verdict_tags",
    "verdict_enable",
    "verdict_value",
    "event_crc_bad",
    "event_dllp",
    "event_good",
    "event_nullified",
    "event_sequence",
    "token_failure",
)


def parser_miter(fault=None):
    lines = [
        "module tb;integer trial,j,b,k;reg [31:0] words[0:3];reg [31:0] choices[0:7];"
    ]
    for name, width in PARSER_INPUTS.items():
        lines.append(f"reg [{width - 1}:0] f_{name};")
    for version, instance in [("v2", "gold"), ("v3", "gate")]:
        lines.append(
            f"soc_pcie_gen3_framer_rx_integrity_{version} {instance}(.clk_i(1'b0),.rst_ni(1'b0),.flush_i(1'b0),.stream_start_i(1'b0),.stream_abort_i(1'b0),.block_valid_i(1'b0),.headers_i(8'haa),.payload_i(512'b0),.block_error_i(1'b0),.ready_i(1'b0));"
        )
    lines.append("initial begin")
    for instance in ["gold", "gate"]:
        for name in PARSER_INPUTS:
            lines.append(f"force {instance}.{name}=f_{name};")
    # Independent polynomial STP encoding for length5 (minimum TLP) and varying sequence.
    length = 5
    value = int(f"{length:011b}"[::-1], 2) << 4
    for bit in range(14, 3, -1):
        if value & (1 << bit):
            value ^= 0x13 << (bit - 4)
    parity = (length.bit_count() + value.bit_count()) & 1
    stp = (
        0xF
        | ((length & 15) << 4)
        | ((length >> 4) << 8)
        | (parity << 15)
        | (value << 20)
        | (0xAB << 24)
        | (3 << 16)
    )
    lines += [
        f"choices[0]=0;choices[1]=32'h{stp:08x};choices[2]=32'h0000acf0;choices[3]=32'hc0c0c0c0;choices[4]=32'h0090801f;choices[5]=32'h01000000;choices[6]=32'hffffffff;choices[7]=32'h12345678;",
        "for(trial=0;trial<32768;trial=trial+1) begin",
    ]
    for name in PARSER_INPUTS:
        if name != "current_block":
            lines.append(f"f_{name}=$random;")
    lines += [
        "f_state=trial%4;f_ending=(trial%19==0);f_remaining=(trial/4)%8;",
        "if(trial%23==0) f_remaining=2047;",
        "for(j=0;j<4;j=j+1) begin",
        " k=(trial>>(3*j))&7;words[j]=choices[k];",
        " if(trial%17==0) words[j]=$random;",
        " for(b=0;b<4;b=b+1) f_current_block[b*128+j*8+:8]=words[j][b*8+:8];end",
        "#1;",
        "if({"
        + ",".join("gold." + p for p in PARSER_OUTPUTS)
        + "} !== {"
        + ",".join("gate." + p for p in PARSER_OUTPUTS)
        + '}) $fatal(1,"PARSER_ARBITRARY_STATE_MISMATCH trial=%0d state=%0d",trial,f_state);',
        'end $display("PASS 32768 ACTUAL_FULL_PARSER_CASES");$finish;end endmodule',
    ]
    return "\n".join(lines)


@pytest.mark.parametrize("fault", [None, "initial_dllp", "selector", "carry_word"])
def test_actual_parser_arbitrary_state_comparison(tmp_path, fault):
    gate = (RTL / "soc_pcie_gen3_framer_rx_integrity_v3.v").read_text()
    mutations = {
        "initial_dllp": (
            "crc16_32(dllp_crc,crc_word[0])",
            "crc16_32(16'hffff,crc_word[0])",
        ),
        "selector": ("crc_origin=j+1;", "crc_origin=0;"),
        "carry_word": (
            "crc32_64(lcrc,{crc_word[1],crc_word[0]})",
            "crc32_64(lcrc,{crc_word[0],crc_word[1]})",
        ),
    }
    if fault:
        before, after = mutations[fault]
        assert gate.count(before) == 1
        gate = gate.replace(before, after)
    candidate = tmp_path / "candidate.v"
    candidate.write_text(gate)
    result, log = simulate(
        tmp_path,
        parser_miter(),
        [RTL / "soc_pcie_gen3_framer_rx_integrity_v2.v", candidate],
    )
    if fault:
        assert result.returncode != 0 and "PARSER_ARBITRARY_STATE_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS 32768" in log
    (tmp_path / "candidate.sha256").write_text(
        hashlib.sha256(gate.encode()).hexdigest() + "\n"
    )
