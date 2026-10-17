#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare one isolated, source-pinned 33-bit ALU carry-prefix experiment."""
import argparse
import hashlib
from pathlib import Path

ORIGINAL_SHA = '81fa8cb2b39fa0b879bd0bc2caa47b4ba69adf6ed361ec15ef8d3eb00165c063'
CANDIDATE_SHA = '0acd9876c32aa855e959a44939803083adb7b88ce71246cf7c2a2e4fb66f6c18'
NEGATIVE_SHA = '8ecf518f7055b09f57fbca16e9338d2ad74864721d97e03affc1a0ef503fa6dc'
OLD = 'assign adder_result_ext_o = $unsigned(adder_in_a) + $unsigned(adder_in_b);'
PREFIX = '''// Isolated research only: preserve parallel-prefix carry intermediates.
(* keep *) wire [32:0] carry_p [0:6];
(* keep *) wire [32:0] carry_g [0:6];
assign carry_p[0] = adder_in_a ^ adder_in_b;
assign carry_g[0] = adder_in_a & adder_in_b;
genvar prefix_level, prefix_bit;
generate
 for (prefix_level=0; prefix_level<6; prefix_level=prefix_level+1) begin: g_prefix_level
  for (prefix_bit=0; prefix_bit<33; prefix_bit=prefix_bit+1) begin: g_prefix_bit
   if (prefix_bit >= (1 << prefix_level)) begin: g_combine
    assign carry_g[prefix_level+1][prefix_bit] = carry_g[prefix_level][prefix_bit] |
      (carry_p[prefix_level][prefix_bit] & carry_g[prefix_level][prefix_bit-(1 << prefix_level)]);
    assign carry_p[prefix_level+1][prefix_bit] = carry_p[prefix_level][prefix_bit] &
      carry_p[prefix_level][prefix_bit-(1 << prefix_level)];
   end else begin: g_pass
    assign carry_g[prefix_level+1][prefix_bit] = carry_g[prefix_level][prefix_bit];
    assign carry_p[prefix_level+1][prefix_bit] = carry_p[prefix_level][prefix_bit];
   end
  end
 end
endgenerate
assign adder_result_ext_o = {carry_g[6][32], carry_p[0] ^ {carry_g[6][31:0],1'b0}};'''


def prepare(data):
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA:
        raise ValueError('Original generated ALU differs from C10 source')
    text = data.decode()
    if text.count(OLD) != 1:
        raise ValueError('Expected exactly one original33-bit addition')
    candidate = text.replace(OLD, PREFIX).encode()
    negative = text.replace(OLD, PREFIX.replace("{carry_g[6][31:0],1'b0}",
                                               "{carry_g[6][31:0],1'b1}")).encode()
    if hashlib.sha256(candidate).hexdigest() != CANDIDATE_SHA or hashlib.sha256(negative).hexdigest() != NEGATIVE_SHA:
        raise ValueError('Prefix preparation differs from reviewed source contract')
    return candidate, negative


def quote(path):
    value = str(path)
    if any(c in value for c in ('\n', '\r', '\0')):
        raise ValueError('Invalid Yosys path')
    return '"'+value.replace('\\', '\\\\').replace('"', '\\"')+'"'


def miter(original, candidate):
    """No internal-name matching; prove every complete ALU output for all inputs."""
    return f'''read_verilog {quote(original)}
chparam -set RV32B 0 ibex_alu
prep -top ibex_alu -flatten
rename ibex_alu gold
design -stash gold
read_verilog {quote(candidate)}
chparam -set RV32B 0 ibex_alu
prep -top ibex_alu -flatten
rename ibex_alu gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten gold gate miter
hierarchy -top miter
memory_map
opt_clean
sat -verify -prove trigger 0 -show-inputs -show-outputs
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    candidate, negative = prepare(args.source.read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in [('original', args.source.read_bytes()), ('candidate', candidate), ('negative', negative)]:
        (args.output/(name+'.v')).write_bytes(data)


if __name__ == '__main__':
    main()
