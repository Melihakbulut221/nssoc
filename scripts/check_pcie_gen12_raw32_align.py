#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only HDL proof with a serial stream indexing oracle, not RTL emulation."""
import hashlib
import json
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hw/soc/out/gen12-raw32-align"
RTL = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen12_raw32_align.v"
COMS = (0x17c, 0x283)

def bits(value, width):
    return [(value >> n) & 1 for n in range(width)]

def number(seq):
    return sum(b << n for n, b in enumerate(seq))

class StreamOracle:
    """Global input bit coordinates; no local shift register or RTL remainder."""
    def __init__(self):
        self.stream = []
        self.start = None
        self.emitted = 0
        self.previous_polarity = 0

    def step(self, reset, enable, force, polarity, valid, raw):
        acquired = 0
        rd = 0
        if not reset:
            self.__init__()
        elif not enable or force or polarity != self.previous_polarity:
            self.stream = []
            self.start = None
            self.emitted = 0
        elif valid:
            self.stream.extend(bits(raw ^ (0xffffffff if polarity else 0), 32))
            if self.start is None:
                for at in range(len(self.stream) - 9):
                    code = number(self.stream[at:at + 10])
                    if code in COMS:
                        self.start = at
                        acquired = 1
                        rd = int(code == COMS[1])
                        break
        if reset:
            self.previous_polarity = polarity
        values = []
        if reset and enable and not force and valid and self.start is not None:
            end = (len(self.stream) - self.start) // 10
            values = [number(self.stream[self.start + j * 10:self.start + (j + 1) * 10])
                      for j in range(self.emitted, end)]
            self.emitted = end
        assert len(values) <= 4
        return (number([b for v in values for b in bits(v, 10)]), len(values),
                sum((v in COMS) << j for j, v in enumerate(values)),
                int(self.start is not None), acquired, rd)

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    oracle = StreamOracle()
    vectors = []
    stats = {"offsets": [], "polarities": [0, 1], "initial_rd": [0, 1],
             "all_raw10_payload_codes": 1024, "transitions": 0,
             "gap_cycles": 0, "reset_cycles": 0, "empty_search_words": 0}
    def add(reset=1, enable=1, force=0, polarity=0, valid=1, raw=0):
        expected = oracle.step(reset, enable, force, polarity, valid, raw)
        vectors.append((reset, enable, force, polarity, valid, raw, *expected))
        stats["gap_cycles"] += int(not valid)
        stats["reset_cycles"] += int(not reset)

    rng = random.Random(0x12a11)
    # Every phase in two words, both explicit polarities and both COM forms.
    # Stream index oracle discovers COM itself; prefix cannot hide an earlier COM.
    for offset in range(64):
        stats["offsets"].append(offset)
        for polarity in (0, 1):
            for rd in (0, 1):
                add(reset=0, valid=0)
                add(polarity=polarity, valid=0)  # explicit polarity-set flush
                payload = [COMS[rd]] + list(range(1024)) + [COMS[rd ^ 1]]
                stream = [0] * offset + [b for v in payload for b in bits(v, 10)]
                stream += [0] * ((-len(stream)) % 32)
                for n in range(0, len(stream), 32):
                    word = number(stream[n:n + 32]) ^ (0xffffffff if polarity else 0)
                    if rng.randrange(7) == 0:
                        add(polarity=polarity, valid=0, raw=rng.getrandbits(32))
                    add(polarity=polarity, raw=word)
    # There must be no boundary or output from a stream without a complete COM.
    add(reset=0, valid=0)
    for _ in range(80):
        add(raw=0)
        stats["empty_search_words"] += 1

    # Flush each actual retained residue, and flush while an incomplete COM
    # is in the search tail. Coverage is measured from global serial positions.
    residues = set()
    search_flushes = set()
    for odd_offset in (0, 1):
        for phase in range(5):
            for action in ("reset", "disable", "force", "polarity"):
                add(reset=0, valid=0)
                for n in range(phase + 1):
                    add(raw=(COMS[0] << odd_offset) if n == 0 else rng.getrandbits(32))
                assert oracle.start == odd_offset
                residues.add((len(oracle.stream) - oracle.start) % 10)
                pol = 0
                if action == "reset":
                    add(reset=0, raw=0xffffffff)
                elif action == "disable":
                    add(enable=0, raw=0xffffffff)
                elif action == "force":
                    add(force=1, raw=0xffffffff)
                else:
                    pol = 1
                    add(polarity=pol, raw=0xffffffff)
                stats["transitions"] += 1
                for _ in range(3):
                    add(polarity=pol, raw=0xffffffff if pol else 0)
                data = bits(COMS[1], 10) + [rng.randrange(2) for _ in range(310)]
                for n in range(0, len(data), 32):
                    add(polarity=pol, raw=number(data[n:n + 32]) ^ (0xffffffff if pol else 0))
    assert residues == set(range(10)), residues
    stats["aligned_flush_residues"] = sorted(residues)
    for action in ("reset", "disable", "force", "polarity"):
        add(reset=0, valid=0)
        # A complete COM is absent: only its first nine bits enter this word.
        add(raw=(COMS[0] & 0x1ff) << 23)
        assert oracle.start is None
        pol = 0
        if action == "reset":
            add(reset=0, raw=0xffffffff)
        elif action == "disable":
            add(enable=0, raw=0xffffffff)
        elif action == "force":
            add(force=1, raw=0xffffffff)
        else:
            pol = 1
            add(polarity=pol, raw=0xffffffff)
        for _ in range(3):
            add(polarity=pol, raw=0xffffffff if pol else 0)
            assert oracle.start is None
        add(polarity=pol, raw=COMS[1] ^ (0xffffffff if pol else 0))
        assert oracle.start == 96
        search_flushes.add(action)
    assert search_flushes == {"reset", "disable", "force", "polarity"}
    stats["search_flush_controls"] = sorted(search_flushes)
    for _ in range(5):
        add(valid=0, raw=rng.getrandbits(32))
    vector_path = OUT / "vectors.txt"
    vector_path.write_text("".join(
        f"{r:x} {e:x} {f:x} {p:x} {v:x} {w:08x} {s:010x} {c:x} {m:x} {b:x} {a:x} {d:x}\n"
        for r, e, f, p, v, w, s, c, m, b, a, d in vectors))
    tb = r"""
module tb;
reg clk=0;
always #5 clk=~clk;
reg rst, en, force_align, pol, valid;
reg [31:0] raw;
wire [39:0] symbols;
wire [2:0] count;
wire [3:0] comma;
wire boundary, acquired, rd;
soc_pcie_gen12_raw32_align dut(clk,rst,en,force_align,pol,valid,raw,
                              symbols,count,comma,boundary,acquired,rd);
integer fd, n, row=0, seen;
reg er,ee,ef,ep,ev;
reg [31:0] ew;
reg [39:0] es;
reg [2:0] ec;
reg [3:0] em;
reg eb,ea,ed;
initial begin
  rst=0;en=0;force_align=0;pol=0;valid=0;raw=0;
  fd=$fopen("vectors.txt","r");
  if (!fd) $fatal(1,"missing vectors");
  while (!$feof(fd)) begin
    seen=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h\n",
                 er,ee,ef,ep,ev,ew,es,ec,em,eb,ea,ed);
    if (seen==12) begin
      @(negedge clk);
      rst=er;en=ee;force_align=ef;pol=ep;valid=ev;raw=ew;
      @(posedge clk); #1;
      if ({symbols,count,comma,boundary,acquired,rd} !== {es,ec,em,eb,ea,ed})
        $fatal(1,"row %0d actual=%h/%0d/%h/%b/%b/%b expected=%h/%0d/%h/%b/%b/%b",
               row,symbols,count,comma,boundary,acquired,rd,es,ec,em,eb,ea,ed);
      row=row+1;
    end else if (seen!=-1) $fatal(1,"bad vector row");
  end
  if (row<80000) $fatal(1,"truncated coverage %0d",row);
  $display("PASS %0d exact vector cycles",row);
  $finish;
end
endmodule
"""
    (OUT / "tb.v").write_text(tb)
    def simulate(source, label, must_pass):
        exe = OUT / (label + ".vvp")
        compile_cmd = ["iverilog", "-g2012", "-s", "tb", "-o", str(exe),
                       str(OUT / "tb.v"), str(source)]
        compiled = subprocess.run(compile_cmd, capture_output=True, text=True)
        (OUT / (label + ".compile.log")).write_text(compiled.stdout + compiled.stderr)
        if compiled.returncode:
            raise AssertionError(label + " failed to compile; not a detected behavioral fault")
        result = subprocess.run(["vvp", str(exe)], cwd=OUT, capture_output=True, text=True)
        (OUT / (label + ".log")).write_text(result.stdout + result.stderr)
        if must_pass:
            assert result.returncode == 0 and "PASS " in result.stdout, result.stdout + result.stderr
        else:
            assert result.returncode != 0 and "row " in result.stdout, label + " mutation not detected"
        return {"label": label, "returncode": result.returncode,
                "log_sha256": hashlib.sha256((result.stdout + result.stderr).encode()).hexdigest()}
    checks = [simulate(RTL, "positive", True)]
    source = RTL.read_text()
    mutations = {
        "wrong_com": ("10'h17c", "10'h17d"),
        "drop_cross_word_bit": ("(available - 9)", "(available - 8)"),
        "ignore_polarity": ("raw_i ^ {32{polarity_i}}", "raw_i"),
        "lose_force_flush": ("!enable_i || force_realign_i ||", "!enable_i ||"),
        "lose_disable_flush": ("!enable_i || force_realign_i ||", "force_realign_i ||"),
        "lose_polarity_flush": (" || polarity_i != polarity_q", ""),
        "ignore_valid_gap": ("else if (raw_valid_i)", "else if (1'b1)"),
        "drop_fourth_symbol": ("i < 4; i = i + 1", "i < 3; i = i + 1"),
        "wrong_acquired_rd": ("(shifted[9:0] == COM_POS);", "(shifted[9:0] == COM_NEG);"),
        "leak_gap_output": ("symbols_d = 40'b0;", "symbols_d = symbols_o;"),
    }
    for label, (old, new) in mutations.items():
        assert source.count(old) == 1, (label, source.count(old))
        mutant = OUT / (label + ".v")
        mutant.write_text(source.replace(old, new))
        checks.append(simulate(mutant, label, False))
    synth = subprocess.run(["yosys", "-Q", "-T", "-p",
        f"read_verilog {RTL}; hierarchy -check -top soc_pcie_gen12_raw32_align; "
        "proc; opt; check -assert; synth -top soc_pcie_gen12_raw32_align; check -assert; stat"],
        capture_output=True, text=True)
    (OUT / "synthesis.log").write_text(synth.stdout + synth.stderr)
    assert synth.returncode == 0, synth.stdout[-5000:] + synth.stderr
    result = {"status": "PASS", "source_sha256": hashlib.sha256(RTL.read_bytes()).hexdigest(),
              "vector_sha256": hashlib.sha256(vector_path.read_bytes()).hexdigest(),
              "cycles": len(vectors), "coverage": stats, "checks": checks,
              "synthesis": "PASS", "full_phy_accepted": False,
              "ltssm_accepted": False, "low_rate_analog_accepted": False}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run()
