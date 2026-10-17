#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

"""SRAM macro energy from the Liberty tables and the measured access pattern.

    macro_energy.py macro-activity.json --netlist soc_top.netlist.v

Current mode derives every SRAM instance and port from the mapped netlist.
Use macro_activity.py for joint-state counts. Historical six-macro figures
below require explicit --legacy-six-macros --window idle. Neither mode prices
address/data/mask switching, output loads, standard cells or physical parasitics.

WHY THIS EXISTS BESIDE `report_power`.  OpenSTA responds to the macro
control-pin annotation -- the six macros move from 4.068 mW to 2.550 mW
at the typical corner between a busy window and an idle one -- but the
weighting it applies to a `when`-conditioned `internal_power` group is
not visible in any report it writes, and the arithmetic below does not
reproduce it.  So the macros are also priced directly, from the two
things that are not in doubt: the Liberty's own numbers, and the number
of clock edges the design spends in each of the macro's states.

The state is exhaustive because `soc_mem_sram.v` ties `A_REN` to
`!do_write`, so `A_WEN` and `A_REN` are complementary on every macro on
every cycle and only four of the eight `when` conditions can occur:

    A_MEN & !A_WEN &  A_REN   a read
    A_MEN &  A_WEN & !A_REN   a write
   !A_MEN & !A_WEN &  A_REN   deselected, while the SoC is not writing
   !A_MEN &  A_WEN & !A_REN   deselected, while the SoC writes elsewhere

The third of those is the one worth reading twice.  It is the state
every macro is in on every clock edge of an idle part, and the Liberty
charges **0.5559 pJ** for it on the 2048x64 and **0.3622 pJ** on the
1024x32, against **0** for the same macro with `A_REN` low.
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

from macro_activity import STATES, digest, ports
from select_pnr_profile import mapped_macros

LEGACY_SIX_MACROS = {
    "RM_IHPSG13_1P_2048x64_c2_bm_bist": [
        ("u_ram.g_ram_2048x64.u_b0", "ram", 0),
        ("u_ram.g_ram_2048x64.u_b1", "ram", 1),
        ("u_ram.g_ram_2048x64.u_b2", "ram", 2),
        ("u_ram.g_ram_2048x64.u_b3", "ram", 3),
    ],
    "RM_IHPSG13_1P_1024x32_c2_bm_bist": [
        ("u_rom.g_rom_1024x32.u_b0", "rom", 0),
        ("u_rom.g_rom_1024x32.u_b1", "rom", 1),
    ],
}

# The corner names the SRAM Liberty uses. The fast one is characterised
# at -55 C where the standard cells are at -40 C, which is docs/47
# section 9's caveat and applies to power exactly as to timing.
SRAM_CORNER = {
    "nom_typ_1p20V_25C": "typ_1p20V_25C",
    "nom_slow_1p08V_125C": "slow_1p08V_125C",
    "nom_fast_1p32V_m40C": "fast_1p32V_m55C",
}


def read_lib(macro, corner, pdk):
    """Historical single-port view, using the same strictly parsed tables."""
    tables, leak, path = read_tables(pdk, macro, corner)
    energies = {'&'.join(('' if bit == '1' else '!')+'A_'+pin
                for pin, bit in zip(('MEN','WEN','REN'), state)): value
                for state, value in tables['A'].items()}
    return energies, leak, path


def legacy_main(args):
    if not args.window or not math.isfinite(args.period_ns) or args.period_ns <= 0:
        raise ValueError('Historical mode requires a window and a positive period')
    data = json.load(open(args.json))
    w = data["windows"][args.window]
    cycles = w["cycles"]
    if type(cycles) is not int or cycles <= 0:
        raise ValueError("Historical window must contain positive integer cycles")
    d = w["derived"]
    sc = SRAM_CORNER.get(args.corner, args.corner)

    total = 0.0
    total_leak = 0.0
    print("# HISTORICAL SIX-MACRO MODEL ONLY; excludes ECC and Ethernet SRAMs")
    print(f"# window {args.window}, {cycles} cycles, corner {args.corner}, "
          f"period {args.period_ns} ns")
    print(f"{'macro':<28}{'reads':>10}{'writes':>10}{'desel-R':>12}"
          f"{'desel-W':>10}{'energy pJ':>14}{'power mW':>11}")
    for macro, insts in LEGACY_SIX_MACROS.items():
        e, leak, path = read_lib(macro, sc, args.pdk_dir)
        E_rd = e["A_MEN&!A_WEN&A_REN"]
        E_wr = e["A_MEN&A_WEN&!A_REN"]
        E_dr = e["!A_MEN&!A_WEN&A_REN"]
        E_dw = e["!A_MEN&A_WEN&!A_REN"]
        for inst, pfx, k in insts:
            rd = d[f"{pfx}_rd{k}"]["high_cycles"]
            wr = d[f"{pfx}_wr{k}"]["high_cycles"]
            dr = d[f"{pfx}_dr{k}"]["high_cycles"]
            dw = d[f"{pfx}_dw{k}"]["high_cycles"]
            if any(type(n) is not int or n < 0 for n in (rd, wr, dr, dw)) or rd+wr+dr+dw != cycles:
                raise ValueError("Incomplete or invalid historical state counts: "+inst)
            ej = (rd * E_rd + wr * E_wr + dr * E_dr + dw * E_dw) * 1e-12
            p = ej / (cycles * args.period_ns * 1e-9) if cycles else 0.0
            total += ej
            total_leak += leak
            print(f"{inst:<28}{rd:>10}{wr:>10}{dr:>12}{dw:>10}"
                  f"{ej * 1e12:>14.1f}{(p + leak) * 1e3:>11.6f}")
    dyn = total / (cycles * args.period_ns * 1e-9) if cycles else 0.0
    print(f"{'TOTAL dynamic':<28}{'':>42}{total * 1e12:>14.1f}"
          f"{dyn * 1e3:>11.6f}")
    print(f"{'TOTAL leakage':<28}{'':>56}{total_leak * 1e3:>11.6f}")
    print(f"{'TOTAL':<28}{'':>56}{(dyn + total_leak) * 1e3:>11.6f}")
    print(f"# energy per window: {total * 1e9:.4f} nJ dynamic + "
          f"{total_leak * cycles * args.period_ns * 1e-9 * 1e9:.4f} nJ leakage")


def block(text, pattern):
    """Read one balanced Liberty group, ignoring braces inside strings."""
    match = re.search(pattern+r'\s*\{', text)
    if not match:
        raise ValueError('Missing Liberty group: '+pattern)
    start, depth = match.end(), 1
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]', text[start:]):
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if not depth:
                return text[start:start+token.start()]
    raise ValueError('Unclosed Liberty group')


def scalar(text, edge):
    body = block(text, edge+r'_power\s*\(\s*"scalar"\s*\)')
    match = re.fullmatch(r'\s*values\s*\(\s*([-+\d.eE]+)\s*\)\s*;\s*', body)
    if not match:
        raise ValueError('Expected a scalar clock energy')
    value = float(match[1])
    if not math.isfinite(value) or value < 0:
        raise ValueError('Invalid clock energy')
    return value


def read_tables(pdk, macro, corner):
    clock_ports = ports(macro)
    if corner not in SRAM_CORNER.values():
        raise ValueError('Unsupported SRAM corner: '+corner)
    path = Path(pdk)/'libs.ref/sg13g2_sram/lib'/f'{macro}_{corner}.lib'
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
    # This contract is deliberately limited to the IHP scalar energy units.
    # Never silently price a library using a different unit convention.
    for pattern in (r'capacitive_load_unit\s*\(\s*1\s*,\s*pf\s*\)',
                    r'voltage_unit\s*:\s*"1V"', r'leakage_power_unit\s*:\s*"1nW"'):
        if not re.search(pattern, text):
            raise ValueError('Unsupported Liberty units: '+str(path))
    cell = block(text, r'\bcell\s*\(\s*"?'+re.escape(macro)+r'"?\s*\)')
    leakage = re.findall(r'\bcell_leakage_power\s*:\s*([-+\d.eE]+)', cell)
    if len(leakage) != 1 or not math.isfinite(float(leakage[0])) or float(leakage[0]) < 0:
        raise ValueError('Missing or invalid cell leakage')
    tables = {}
    for port in clock_ports:
        body = block(cell, r'\bpin\s*\(\s*'+port+r'_CLK\s*\)')
        entries = {}
        for match in re.finditer(r'\binternal_power\s*\(\s*\)', body):
            group = block(body[match.start():], r'internal_power\s*\(\s*\)')
            when = re.findall(r'\bwhen\s*:\s*"([^"]+)"', group)
            if len(when) != 1:
                raise ValueError('Missing clock energy condition')
            terms = re.sub(r'\s+', '', when[0]).split('&')
            allowed = {port+'_'+s for s in ('MEN','WEN','REN')}
            if len(terms) != 3 or {t.lstrip('!') for t in terms} != allowed or any(t.startswith('!!') for t in terms):
                raise ValueError('Unsupported clock energy condition: '+when[0])
            state = ''.join('0' if '!'+port+'_'+s in terms else '1' for s in ('MEN','WEN','REN'))
            if state in entries:
                raise ValueError('Duplicate clock energy condition')
            if scalar(group, 'fall') != 0:
                raise ValueError('Nonzero falling-edge power requires a different activity model')
            entries[state] = scalar(group, 'rise')
        if set(entries) != set(STATES):
            raise ValueError('Incomplete SRAM clock state table')
        tables[port] = entries
    return tables, float(leakage[0])*1e-9, path


def estimate(data, netlist, pdk, corner):
    """Price every functional port, counting cell leakage once per macro."""
    netlist_hash = digest(netlist)
    inventory = mapped_macros(netlist)
    if data.get('format') != 1 or data.get('state_order') != ['MEN','WEN','REN']:
        raise ValueError('Use the mapped macro_activity.py format')
    if data.get('source_sha256', {}).get('netlist') != netlist_hash:
        raise ValueError('Activity belongs to a different mapped netlist')
    duration = data.get('elapsed_ns')
    if type(duration) not in (float, int) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid measurement duration')
    if duration != data['end_ns'] - data['start_ns'] or data['start_ns'] < 0:
        raise ValueError('Inconsistent measurement window')
    if set(data['macros']) != set(inventory):
        raise ValueError('Activity must cover exactly every mapped SRAM, including ECC and Ethernet')
    rows, libraries, cache = {}, {}, {}
    for name, master in inventory.items():
        row = data['macros'][name]
        if row['master'] != master or set(row['ports']) != set(ports(master)):
            raise ValueError('Macro type or port inventory mismatch: '+name)
        if master not in cache:
            library_path = Path(pdk)/'libs.ref/sg13g2_sram/lib'/f'{master}_{SRAM_CORNER.get(corner, corner)}.lib'
            before = digest(library_path)
            cache[master] = read_tables(pdk, master, SRAM_CORNER.get(corner, corner))
            if digest(library_path) != before:
                raise ValueError('Liberty changed during estimation')
            libraries[library_path.name] = before
        tables, leakage, path = cache[master]
        energy, edges = 0.0, {}
        for port, counts in row['ports'].items():
            states = counts['state_edges']
            if set(states) != set(STATES) or any(type(v) is not int or v < 0 for v in states.values()):
                raise ValueError('Incomplete or invalid joint-state counts: '+name+'/'+port)
            if type(counts['rising_edges']) is not int or sum(states.values()) != counts['rising_edges']:
                raise ValueError('State counts do not cover every rising edge: '+name+'/'+port)
            energy += sum(tables[port][state]*count for state, count in states.items())
            edges[port] = counts['rising_edges']
        rows[name] = dict(master=master, rising_edges=edges, clock_energy_pj=energy,
                          leakage_energy_pj=leakage*duration*1000)
    clock = sum(r['clock_energy_pj'] for r in rows.values())
    leak = sum(r['leakage_energy_pj'] for r in rows.values())
    if digest(netlist) != netlist_hash or any(digest(Path(pdk)/'libs.ref/sg13g2_sram/lib'/name) != sha
                                            for name, sha in libraries.items()):
        raise ValueError('Netlist or Liberty changed during estimation')
    return dict(scope='SRAM functional-clock internal energy plus scalar cell leakage only. Excludes address/data/mask pin switching, external loads, standard cells, extracted parasitics and silicon qualification.',
                netlist_sha256=netlist_hash, corner=corner, elapsed_ns=duration,
                library_sha256=libraries, macros=rows, clock_energy_pj=clock,
                leakage_energy_pj=leak, modelled_power_mw=(clock+leak)/duration)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('json', type=Path)
    ap.add_argument('--netlist', type=Path, help='Required for current mapped-macro activity')
    ap.add_argument('--pdk-dir', type=Path,
                    default=Path(os.environ.get('PWR_PDK', str(Path(os.environ.get('PDK_ROOT', str(Path.home()/'.ciel')))/'ihp-sg13g2'))))
    ap.add_argument('--corner', default='nom_typ_1p20V_25C', choices=sorted(set(SRAM_CORNER)|set(SRAM_CORNER.values())))
    ap.add_argument('--legacy-six-macros', action='store_true', help='Explicitly reproduce the historical unprotected six-macro model')
    ap.add_argument('--window', help='Historical activity window only')
    ap.add_argument('--period-ns', type=float, default=20.0, help='Historical reference period only')
    args = ap.parse_args()
    try:
        if args.legacy_six_macros:
            if args.netlist:
                raise ValueError('Historical six-macro mode cannot price a current netlist')
            legacy_main(args)
        else:
            if not args.netlist or args.window:
                raise ValueError('Current mode requires --netlist and macro_activity.py input; historical reproduction requires --legacy-six-macros --window')
            before = digest(args.json)
            result = estimate(json.loads(args.json.read_text()), args.netlist, args.pdk_dir, args.corner)
            if digest(args.json) != before:
                raise ValueError('Activity changed during estimation')
            result['activity_sha256'] = before
            print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        ap.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
