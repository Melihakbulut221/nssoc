#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate real upper-metal TX geometries and run unchanged physical gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, digest, target):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent',
                    '--show-error', url, '-o', str(target)], check=True)
    assert sha(target) == digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('baseline', 'topmetal_trunks', 'topmetal_trunks_narrow_bus',
                                             'critical_buses', 'critical_buses_wide_escape',
                                             'critical_buses_supply_escape', 'critical_buses_power_trunks','critical_buses_power_trunks_vias',
                                             'critical_buses_interleaved_resistors', 'critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'), required=True)
    parser.add_argument('--circuit-profile', choices=('baseline','cascade14','cascade16','final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8'), default='baseline')
    args = parser.parse_args()
    if args.circuit_profile == 'cascade16':
        assert args.variant in ('critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct',), 'New prestage keeps proven dense physical geometry'
    if args.variant in ('critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal'):
        assert args.circuit_profile == 'final_drive_v8', 'Tail-path experiment binds the measured v8 circuit only'
    if args.variant in ('critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct'):
        assert args.circuit_profile == 'cascade14', 'Supply-feed experiment binds measured cascade14 prestage'
    dense_prestage = args.circuit_profile in ('cascade14','cascade16') and args.variant in ('critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct',)
    if args.variant in ('critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
        assert args.circuit_profile in ('final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8') or dense_prestage
    spec_path = ROOT / 'docs/evidence/pcie-tx-layout-cloud-input-20261013.json'
    spec = json.loads(spec_path.read_text())
    out = ROOT / 'hw/soc/out/cloud-tx-layout-repair'
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', variant=args.variant, circuit_profile=args.circuit_profile, adopted=False,
        scope='Real generated layout with54native devices. DRC/LVS and physical fault controls only; new native RC extraction and full waveform validation still required before any electrical adoption. No main-chip or full serial PHY acceptance.')

    def run(command, name):
        log = out / (name + '.log')
        with log.open('w') as stream:
            code = subprocess.call([str(x) for x in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if code:
            print(log.read_text(errors='replace')[-16000:], flush=True)
            for child in sorted((out / 'physical').glob('*/run.log')):
                print(str(child) + '\n' + child.read_text(errors='replace')[-4000:], flush=True)
            raise RuntimeError(f'{name} failed with exit{code}')

    try:
        archive = out / 'input.tar.gz'
        fetch(spec['receipt']['url'], spec['receipt']['sha256'], archive)
        with tarfile.open(archive) as tar:
            tar.extractall(ROOT, filter='data')
        archive.unlink()
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        assert all(sha(ROOT / n) == r['sha256'] for n, r in manifest['files'].items())
        originals = out / 'original-methods'
        originals.mkdir()
        for bundle in spec['method_archives']:
            fetch(bundle['url'], bundle['sha256'], archive)
            with tarfile.open(archive) as tar:
                for name, digest in bundle['members'].items():
                    member = tar.getmember(name)
                    assert member.isfile() and member.size < 1024 * 1024
                    data = tar.extractfile(member).read()
                    assert hashlib.sha256(data).hexdigest() == digest
                    if name.endswith('.spice'):
                        target = ROOT / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        target = originals / Path(name).name
                    target.write_bytes(data)
            archive.unlink()
        source = (originals / 'layout91.py').read_text()
        edits = []
        physical_source=(originals/'physical92.py').read_text()
        if args.circuit_profile in ('cascade14','cascade16','final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8'):
            if args.circuit_profile in ('cascade14','cascade16'):
                version,expected={
                    'cascade14':('v2','c97692bcc4389c256479631e820a4293b79121d2225d767f5635429cd7dd0805'),
                    'cascade16':('v3','9cc69586dbe83af7d58ff1c1f15a58aac17958ada8916cd1dbe0554e2813cd39'),
                }[args.circuit_profile]
                circuit=ROOT/f'hw/soc/analog/pcie/tx_mux2_hbt_cascade_{version}.spice'
                top=f'nssoc_tx_mux2_{args.circuit_profile}_layout_v1'
            else:
                from audit_tx_final_layout_source import audit
                audit_profile = args.circuit_profile.rsplit('_',1)[1]
                circuit=ROOT/f'hw/soc/analog/pcie/tx_mux2_final_drive_{audit_profile}_layout_core.spice'
                native=ROOT/f'hw/soc/analog/pcie/tx_mux54_passive_drive_{audit_profile}.spice'
                expected,native_digest={
                    'v5':('c74d1e0d2b7d7f1093653ee1d5ece27649ae97b1485e998fe3f4ff1b78cbfcdf','75242abe73341e04ba62b2d4a41abf5e55b725ecec6eeb55dbf6abbbe8f2232d'),
                    'v6':('2ef986b71a2b6b74d4b6b20f74048759c191a441d3bc58667259110b0b2a562f','03e40de12d6f1e340772476959abc823676766a16466bc465c2972954ba64c76'),
                    'v7':('55249822b97b01e8c5f9f90faa408fbf1a0cd34ce55f8f48a5cde87304c9217a','6f03f8557173a8528f3ad20a16c3102487cbcfe2ba0ac657190f2d46c95edc81'),
                    'v8':('ece50f76c5c8a6bd9bb334498a958c14a2c7be93cb44d008786e8112608c005d','1cae9383cc799292e85c8e95ff641410a502c76b927d8729248ebef9758f0ed8'),
                }[audit_profile]
                assert sha(native)==native_digest
                result['circuit_equivalence_before_generation']=audit(circuit.read_text(),native.read_text(),profile=audit_profile)
                top=f'nssoc_tx_mux2_final_drive_{audit_profile}_layout_v1'
            assert sha(circuit)==expected
            for before,after in [
                ('hw/soc/out/pcie-tx-mux2-20261012/tx_mux2_hbt_passive_fast_v1.spice',str(circuit.relative_to(ROOT))),
                ('4d7606b3c14ef06de2d25ce46c266dcef3635fe602218b3a8932f7f061e53101',expected),
                ('nssoc_tx_mux2_passive_topmetal_layout_v1',top)]:
                assert source.count(before)==1,before
                source=source.replace(before,after)
                edits.append(dict(before=before,after=after))
            assert physical_source.count('nssoc_tx_mux2_passive_topmetal_layout_v1')==1
            physical_source=physical_source.replace('nssoc_tx_mux2_passive_topmetal_layout_v1',top)
            result['circuit_source']=dict(path=str(circuit.relative_to(ROOT)),sha256=expected)
            result['scope']='Native '+args.circuit_profile+' circuit generated as54physical devices including27substrate contacts. Circuit equivalence is not electrical acceptance; Each sizing candidate requires independent fresh electrical screening. Same560DRC rules, strict hierarchical/flat transistor LVS and five physical/reference faults. No extracted electrical acceptance, assembled serializer layout or fullPHY/chip acceptance.'
        if args.variant != 'baseline':
            changes = [
                ('30+26*c,30+14*r', '30+28.8*c,30+14*r'),
                ('238+12*(i-19)', '260.4+14.4*(i-19)'),
                ('(collector, 1, n[0], x - 9, 0.04)', '(collector, 1, n[0], x - 10.8, 0.04)'),
                ('(base, 1, n[1], x - 6, -0.04)', '(base, 1, n[1], x - 7.2, -0.04)'),
                ('(m2[0], 2, n[2], x - 3, 0)', '(m2[0], 2, n[2], x - 3.6, 0)'),
                ('x - 6 + 3 * k', 'x - 7.2 + 3.6 * k'),
                ('"sub", x + 15', '"sub", x + 14.4'),
                ('via(3, 4, lane, y)', 'via(3, 6, lane, y)'),
                ('box(4, x - 0.6, min(sy, y) - 0.2, x + 0.6, max(sy, y) + 0.2)',
                 'box(6, x - 0.82, min(sy, y) - 0.2, x + 0.82, max(sy, y) + 0.2)'),
                ('via(4, 7, x, y)', 'via(6, 7, x, y)'),
                ('    for x, y in kelvin:via(2, 5, round(x/0.005)*0.005, round(y/0.005)*0.005, 4)\n',
                 '    # Return connections use the new thick trunks; omit the bypass.\n'),
                ('    box(5, min(x for x,y in kelvin)-1, min(y for x,y in kelvin)-6, max(x for x,y in kelvin)+1, max(y for x,y in kelvin)+6)\n',
                 '    # Old Metal5 bypass would short the new low via stacks.\n'),
            ]
            if args.variant == 'topmetal_trunks_narrow_bus':
                changes.append(("width = 16 if net in ['avdd','avss'] else 4", "width = 16 if net in ['avdd','avss'] else 3"))
            if args.variant.startswith('critical_buses'):
                changes.append(('    for i, net in enumerate(sorted(terminals)):',
                    "    ordered_nets = ['qn','qp','ea','eb','tail','sp','sn','op','on','ap','an','bp','bn','iref','avdd','avss','sub']\n"
                    "    assert len(ordered_nets) == len(terminals) and set(ordered_nets) == set(terminals)\n"
                    "    for i, net in enumerate(ordered_nets):"))
                # TM2.bR requires5um beside wide lines with>50um parallel run.
                # These are exactly the three gaps adjacent to the two supply
                # buses in the explicit critical-net order above.
                changes.append(('cursor_y = y + half + 3',
                                "cursor_y = y + half + (5 if net in ['iref','avdd','avss'] else 3)"))
            if args.variant in ('critical_buses_wide_escape','critical_buses_supply_escape','critical_buses_power_trunks','critical_buses_power_trunks_vias','critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                changes.append(('escape(pin, met, net, lane, name, 4, off)',
                                'escape(pin, met, net, lane, name, 8, off)'))
            if args.variant in ('critical_buses_supply_escape','critical_buses_power_trunks','critical_buses_power_trunks_vias','critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                # Actual measured tail-emitter lift differs from the reference
                # return. Reduce native supply/return metal resistance in GDS;
                # keep signal escape geometry and all circuit devices intact.
                # The same native DRC/LVS/fault checks decide legality.
                changes.append(('        box(3, lane - 0.2, y - 0.2, x + 0.2, y + 0.2)',
                    "        half_escape = 0.4 if net in ['avdd','avss'] else 0.2\n"
                    '        box(3, lane - half_escape, y - half_escape, x + half_escape, y + half_escape)'))
                changes.append(('            box(6, x - 0.82, min(sy, y) - 0.2, x + 0.82, max(sy, y) + 0.2)',
                    "            half_trunk = 1.0 if net in ['avdd','avss'] else 0.82\n"
                    '            box(6, x - half_trunk, min(sy, y) - 0.2, x + half_trunk, max(sy, y) + 0.2)'))
            if args.variant in ('critical_buses_power_trunks','critical_buses_power_trunks_vias','critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                # More room between routing lanes permits wider native power
                # trunks without stealing spacing from adjacent signal metal.
                # This is a new physical candidate, not a scaled RC surrogate.
                changes += [
                    ('30+28.8*c,30+14*r','30+38.4*c,30+14*r'),
                    ('260.4+14.4*(i-19)','337.2+19.2*(i-19)'),
                    ('(collector, 1, n[0], x - 10.8, 0.04)','(collector, 1, n[0], x - 14.4, 0.04)'),
                    ('(base, 1, n[1], x - 7.2, -0.04)','(base, 1, n[1], x - 9.6, -0.04)'),
                    ('(m2[0], 2, n[2], x - 3.6, 0)','(m2[0], 2, n[2], x - 4.8, 0)'),
                    ('x - 7.2 + 3.6 * k','x - 9.6 + 4.8 * k'),
                    ('"sub", x + 14.4','"sub", x + 19.2'),
                    ("half_trunk = 1.0 if net in ['avdd','avss'] else 0.82",
                     "half_trunk = 1.64 if net in ['avdd','avss'] else 0.82"),
                    ("width = 16 if net in ['avdd','avss'] else 4",
                     "width = 32 if net in ['avdd','avss'] else 4"),
                ]
            if (args.circuit_profile in ('final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8') or dense_prestage) and args.variant in ('critical_buses_power_trunks','critical_buses_power_trunks_vias','critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                # Actual first-layout extraction shorted ea to avdd: D20's
                # 18um resistor contact via at x365.4 meets D21's ea escape
                # lane x366 at the same y. DRC alone did not detect this.
                # Move whole resistor banks, preserving every device value.
                # 28.8um would align the prior substrate trunk (+19.2)
                # with the next signal lane (-9.6), also a real LVS short.
                changes.append(('337.2+19.2*(i-19)', '337.2+38.4*(i-19)'))
                if args.variant in ('critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                    # Place one resistor below each HBT bank, in dedicated
                    # inter-bank lanes. Long bleeders end below HBT tap row.
                    # Keep the same19HBT/8R/27tap circuit; actual LVS decides.
                    changes.append(('positions.update({i:(337.2+38.4*(i-19),30) for i in range(19,27)})',
                        'positions.update({19:(164.4,-50),20:(126.0,-50),21:(202.8,-50),22:(241.2,-50),23:(279.6,-50),24:(318.0,-50),25:(87.6,-50),26:(49.2,-50)})'))

            if args.variant in ('critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                # The original same-Y M5 strap crossed other via stacks. Put
                # the common return below all PCells, with separate vertical
                # M5 branches at the three actual ground-emitter pin centres.
                # Short variant joins above the tail/reference banks at64.8um,
                # avoiding resistor/tap crossings while reducing branchlength.
                # Tail/reference ground imbalance was measured in native waves.
                # Jog the reference branch: x298.8 would intersect D23's
                # substrate via at y~-69; strict LVS caught that actual short.
                changes.append(('    # Return connections use the new thick trunks; omit the bypass.\n',
                    ('    return_y = 64.8\n' if args.variant in ('critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4') else '    return_y = -92.4\n') +
                    '    assert len(kelvin) == 3\n'
                    '    return_lanes = []\n'
                    '    for index, (x, y) in enumerate(kelvin):\n'
                    '        via(2, 5, x, y, 4)\n'
                    '        lane = x + (4.8 if index == 0 else 0)\n'
                    '        return_lanes.append(lane)\n'
                    '        box(5, min(x,lane)-0.4, y-0.4, max(x,lane)+0.4, y+0.4)\n'
                    '        box(5, lane-0.4, min(return_y,y)-0.4, lane+0.4, max(return_y,y)+0.4)\n'
                    '    box(5, min(return_lanes)-0.4, return_y-0.4, max(return_lanes)+0.4, return_y+0.4)\n'))
            if args.variant in ('critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4','critical_buses_power_trunks_vias'):
                # Pin access already has8columns, but M3-to-TM1 escape retained
                # the via helper default of2. Increase actual lower-via cuts;
                # TopVia1/2 geometry and every extraction coefficient unchanged.
                changes.append(('via(3, 6, lane, y)', 'via(3, 6, lane, y, 12)' if args.variant in ('critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10') else 'via(3, 6, lane, y, 8)'))
            if args.variant in ('critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
                # Increase actual via-array parallelism without changing any
                # native extraction coefficients or device circuit parameters.
                changes.extend([
                    ('vn_rows=1,', f'vn_rows={4 if args.variant.endswith("dense4") else 2} if lo==3 and hi==6 else 1,\n                vt1_rows={4 if args.variant.endswith("dense4") else 2} if lo==3 and hi==6 else 1,'),
                    ("half_escape = 0.4 if net in ['avdd','avss'] else 0.2",
                     "half_escape = 0.4 if net in ['avdd','avss'] else 0.3"),
                    ('1 if p["w"]=="1u" else 4)', '1 if p["w"]=="1u" else 8)'),
                ])
            if args.variant in ('critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12'):
                # Native class sensitivity removed all four HBT violations only
                # when internal metal loss fell. Widen those actual TM1 trunks
                # from1.64 to3.0um on existing4.8um lanes; keep return/bias and
                # every device, cut array and PDK extraction coefficient fixed.
                # Unchanged native DRC/LVS determines physical legality.
                changes.append((
                    "half_trunk = 1.64 if net in ['avdd','avss'] else 0.82",
                    "half_trunk = 1.5 if net in ['qn','qp','ea','eb','tail'] else (1.64 if net in ['avdd','avss'] else 0.82)"))
            if args.variant.startswith('critical_buses_kelvin_signal_escape_') or args.variant == 'critical_buses_kelvin_m3_10':
                # Explore actual horizontal M3 access, whose long native-R
                # branches remain after the TM1-only improvement. Do not widen
                # clock/data bases, supply/return, or alter any PDK coefficient.
                half_access = {'08': 0.4, '10': 0.5, '12': 0.6}[args.variant[-2:]]
                # m3_10 keeps the proven dense-wide TM1 width; the sibling
                # sweep retains widened TM1 for a separate controlled axis.
                changes.append((
                    "half_escape = 0.4 if net in ['avdd','avss'] else 0.3",
                    f"half_escape = {half_access} if net in ['qn','qp','ea','eb','tail'] else (0.4 if net in ['avdd','avss'] else 0.3)"))
            if args.variant in ('critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal'):
                # Hot native waveforms measured ~66mV from selector emitters
                # to tail collectors and ~34mV emitter return lift. Widen only
                # actual tail M3/TM1 and the local common M5 return strap.
                # All devices, other signal trunks, via cuts, PDK RC values
                # and electrical gates retain the dense-wide source contract.
                changes.extend([
                    ("half_escape = 0.4 if net in ['avdd','avss'] else 0.3",
                     "half_escape = 0.5 if net == 'tail' else (0.4 if net in ['avdd','avss'] else 0.3)"),
                    ("half_trunk = 1.64 if net in ['avdd','avss'] else 0.82",
                     "half_trunk = 1.5 if net == 'tail' else (1.64 if net in ['avdd','avss'] else 0.82)"),
                    ('box(5, min(x,lane)-0.4, y-0.4, max(x,lane)+0.4, y+0.4)',
                     'box(5, min(x,lane)-0.8, y-0.8, max(x,lane)+0.8, y+0.8)'),
                    ('box(5, lane-0.4, min(return_y,y)-0.4, lane+0.4, max(return_y,y)+0.4)',
                     'box(5, lane-0.8, min(return_y,y)-0.8, lane+0.8, max(return_y,y)+0.8)'),
                    ('box(5, min(return_lanes)-0.4, return_y-0.4, max(return_lanes)+0.4, return_y+0.4)',
                     'box(5, min(return_lanes)-0.8, return_y-0.8, max(return_lanes)+0.8, return_y+0.8)'),
                ])
            if args.variant in ('critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal',):
                # Preserve the complete proven tail-path geometry and add a
                # real same-net local shunt. Existing M3->TM1 via stacks expose
                # M4, so no overlapping new cuts are inserted at those points.
                # The six tail endpoints belong to selector/tail banks only.
                # Native DRC/LVS must detect any collision with another net.
                changes.append(('    # Old Metal5 bypass would short the new low via stacks.\n',
                    '    assert len(terminals["tail"]) == 6\n'
                    '    tail_join_y = 60.0\n'
                    '    tail_xs = []\n'
                    '    for x, sy in terminals["tail"]:\n'
                    '        box(4, x-0.4, min(sy,tail_join_y)-0.4, x+0.4, max(sy,tail_join_y)+0.4)\n'
                    '        tail_xs.append(x)\n'
                    '    box(4, min(tail_xs)-0.4, tail_join_y-1.0, max(tail_xs)+0.4, tail_join_y+1.0)\n'
                    '    assert rows[17]["nets"][2] == "avss"\n'
                    '    ground_trunk_x = positions[17][0] - 4.8\n'
                    '    assert sum(abs(x-ground_trunk_x)<1e-9 for x,sy in terminals["avss"]) == 2\n'
                    '    box(5, min(ground_trunk_x,min(return_lanes))-0.8, return_y-0.8, max(ground_trunk_x,max(return_lanes))+0.8, return_y+0.8)\n'
                    '    via(5, 6, ground_trunk_x, return_y, 4)\n'))
            if args.variant in ('critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal',):
                # Actual hot loaded wave: tail emitters remain33-35mV above
                # ground and final MUX delay grows9.47ps to22.28ps. Increase
                # only the same-net local M5 return metal and its native via
                # arrays; keep all54devices, tail M4 shunt and RC rules intact.
                # Eight columns failed M4/M5 spacing at a native pin:0.190um.
                # Six columns retain parallel cuts with more native clearance.
                changes.extend([
                    ('via(2, 5, x, y, 4)', 'via(2, 5, x, y, 6)'),
                    ('box(5, min(x,lane)-0.8, y-0.8, max(x,lane)+0.8, y+0.8)',
                     'box(5, min(x,lane)-1.6, y-1.6, max(x,lane)+1.6, y+1.6)'),
                    ('box(5, lane-0.8, min(return_y,y)-0.8, lane+0.8, max(return_y,y)+0.8)',
                     'box(5, lane-1.6, min(return_y,y)-1.6, lane+1.6, max(return_y,y)+1.6)'),
                    ('box(5, min(return_lanes)-0.8, return_y-0.8, max(return_lanes)+0.8, return_y+0.8)',
                     'box(5, min(return_lanes)-1.6, return_y-1.6, max(return_lanes)+1.6, return_y+1.6)'),
                    ('box(5, min(ground_trunk_x,min(return_lanes))-0.8, return_y-0.8, max(ground_trunk_x,max(return_lanes))+0.8, return_y+0.8)',
                     'box(5, min(ground_trunk_x,min(return_lanes))-1.6, return_y-1.6, max(ground_trunk_x,max(return_lanes))+1.6, return_y+1.6)'),
                    ('via(5, 6, ground_trunk_x, return_y, 4)',
                     'via(5, 6, ground_trunk_x, return_y, 8)'),
                ])
            if args.variant in ('critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal'):
                # Native DC38411521005 measured8.029/9.196ohm prestage
                # and8.579/10.233ohm final avdd paths to load resistors. Add a real parallel
                # low TM2 feed and wide external TM1 riser; keep original
                # trunks, all54devices and extraction coefficients intact.
                # New geometry is subject to native DRC/LVS/fault controls.
                changes.append(('    assert set(ports) == set(PORTS)\n',
                    '    assert len(terminals["avdd"]) == 2\n'
                    '    feed_y = -10.0\n'
                    '    riser_x = -10.0\n'
                    '    avdd_y = ports["avdd"][1].center().y\n'
                    '    feed_xs = [x for x,sy in terminals["avdd"]]\n'
                    '    assert all(sy < feed_y < avdd_y for x,sy in terminals["avdd"])\n'
                    '    assert riser_x + 4 < min(x for ts in terminals.values() for x,sy in ts) - 4\n'
                    '    box(7, riser_x-4, feed_y-4, max(feed_xs)+4, feed_y+4)\n'
                    '    box(6, riser_x-4, feed_y-4, riser_x+4, avdd_y+4)\n'
                    '    box(7, riser_x-4, avdd_y-4, max(feed_xs)+4, avdd_y+4)\n'
                    '    via(6, 7, riser_x, feed_y)\n'
                    '    via(6, 7, riser_x, avdd_y)\n'
                    '    for x in feed_xs: via(6, 7, x, feed_y)\n'
                    '    assert set(ports) == set(PORTS)\n'))
            if args.variant == 'critical_buses_kelvin_supply_direct':
                # The verified prestage still has7.034/8.203ohm from avdd to
                # load pins and loses inputcommonmode in hot loaded operation.
                # Connect the actual resistor M1->M3 landing directly to the
                # existing low TM2 feed, bypassing the long M3 escape. Preserve
                # the old paths and all devices; native DRC/LVS must pass.
                changes.extend([
                    ('    terminals = {}\n',
                     '    terminals = {}\n    direct_avdd_pins = []\n'),
                    ('        via(met, 3, x, y, cols)\n',
                     '        via(met, 3, x, y, cols)\n'
                     '        if net == "avdd":\n'
                     '            assert met == 1\n'
                     '            direct_avdd_pins.append((x,y))\n'
                     '            via(3, 6, x, y, 8)\n'),
                    ('    assert set(ports) == set(PORTS)\n',
                     '    assert len(direct_avdd_pins) == 2\n'
                     '    assert all(y < feed_y for x,y in direct_avdd_pins)\n'
                     '    for x,y in direct_avdd_pins:\n'
                     '        box(6, x-1.64, y-0.2, x+1.64, feed_y+0.2)\n'
                     '        via(6, 7, x, feed_y)\n'
                     '    box(7, riser_x-4, feed_y-4, max(x for x,y in direct_avdd_pins)+4, feed_y+4)\n'
                     '    assert set(ports) == set(PORTS)\n'),
                ])
            if args.variant in ('critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal'):
                # Source-bound hot/cold wave diagnosis38420038719/38420042839:
                # final selector collectors lose86-103mV mean relative to the
                # compact circuit. Add actual short internal ea/eb routes on
                # different metals; keep all original paths and54devices.
                # Existing M3->TM1 stacks expose M4/M5 at every escaped pin.
                # Nine terminals each: six data emitters, two selectors and
                # one native bleeder. Native DRC and strict LVS decide legality.
                changes.append(('    assert set(ports) == set(PORTS)\n',
                    '    for local_net,local_layer,local_y in [("ea",4,16.0),("eb",5,20.0)]:\n'
                    '        assert len(terminals[local_net]) == 9\n'
                    '        local_xs = []\n'
                    '        for x,sy in terminals[local_net]:\n'
                    '            box(local_layer, x-0.4, min(sy,local_y)-0.4, x+0.4, max(sy,local_y)+0.4)\n'
                    '            local_xs.append(x)\n'
                    '        box(local_layer, min(local_xs)-0.4, local_y-1.0, max(local_xs)+0.4, local_y+1.0)\n'
                    '    assert set(ports) == set(PORTS)\n'))
            if args.variant == 'critical_buses_kelvin_compact_internal':
                # Local parallel shunts reduce DC R but hot waveform worsens.
                # Remove only the superseded ea/eb global trunks and buses,
                # retaining all nine physical terminals on each local route.
                # Advance cursor first so every other bus/port stays fixed.
                # This removes real metal; never edit extracted R/C values.
                changes.append(('        xs = []\n',
                    '        if net in ("ea", "eb"):\n'
                    '            assert net not in PORTS and len(terminals[net]) == 9\n'
                    '            continue\n'
                    '        xs = []\n'))
            if args.variant in ('critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical'):
                # The M4/M5-only short-route trial raises internal resistance
                # and fails cold selector headroom. Use original TM1/TM2
                # conductors nearer the device banks instead. The cursor has
                # already advanced, preserving all unrelated bus/port positions.
                # No local M4/M5 ea/eb shunts, no parallel obsolete upper buses.
                changes.append(('        xs = []\n',
                    '        if net in ("ea", "eb"):\n'
                    '            assert net not in PORTS and len(terminals[net]) == 9\n'
                    '            y = 16.0 if net == "ea" else 24.0\n'
                    '        xs = []\n'))
            if args.variant == 'critical_buses_kelvin_low_critical':
                # Low ea/eb routes remove wrong signs but hot margins and
                # cold selector headroom still fail. Also shorten the actual
                # qn/qp collector trunks and TM2 buses; retain the original
                # cursor and all public-port positions. No R/C scaling.
                changes.append((
                    '        if net in ("ea", "eb"):\n'
                    '            assert net not in PORTS and len(terminals[net]) == 9\n'
                    '            y = 16.0 if net == "ea" else 24.0\n',
                    '        if net in ("qn", "qp", "ea", "eb"):\n'
                    '            assert net not in PORTS\n'
                    '            assert len(terminals[net]) == (9 if net in ("ea", "eb") else 8)\n'
                    '            y = {"qn": 1.0, "qp": 9.0, "ea": 16.0, "eb": 24.0}[net]\n'))
            for before, after in changes:
                assert source.count(before) == 1, before
                source = source.replace(before, after)
                edits.append(dict(before=before, after=after))
        if args.variant in ('critical_buses_interleaved_resistors','critical_buses_kelvin_return','critical_buses_kelvin_short','critical_buses_kelvin_short_vias','critical_buses_kelvin_dense','critical_buses_kelvin_dense_wide','critical_buses_kelvin_supply_feed','critical_buses_kelvin_supply_direct','critical_buses_kelvin_tail_paths','critical_buses_kelvin_local_tail','critical_buses_kelvin_local_return','critical_buses_kelvin_local_supply','critical_buses_kelvin_low_internal','critical_buses_kelvin_low_critical','critical_buses_kelvin_local_internal','critical_buses_kelvin_compact_internal','critical_buses_kelvin_signal_trunks','critical_buses_kelvin_signal_escape_08','critical_buses_kelvin_signal_escape_10','critical_buses_kelvin_signal_escape_12','critical_buses_kelvin_m3_10','critical_buses_kelvin_dense4'):
            # Power buses no longer share an x interval. The frozen mutation
            # assumed they did and failed before injecting any physical fault.
            # Join the two verified actual pin centres using an L-shaped bridge.
            before = """    x=max(ports['avdd'][2],ports['avss'][2])+2.5
    region=pya.Region(top.shapes(L.layer(134,0)))
    for net in ['avdd','avss']:assert not (region & pya.Region(pya.DBox(x,ys[net]-.1,x+.1,ys[net]+.1).to_itype(L.dbu))).is_empty()
    top.shapes(L.layer(134,0)).insert(pya.DBox(x,min(ys['avdd'],ys['avss'])-.7,x+.5,max(ys['avdd'],ys['avss'])+.7))"""
            after = """    xa=(ports['avdd'][0]+ports['avdd'][2])/2
    xb=(ports['avss'][0]+ports['avss'][2])/2
    region=pya.Region(top.shapes(L.layer(134,0)))
    for net,x in [('avdd',xa),('avss',xb)]:assert not (region & pya.Region(pya.DBox(x-.1,ys[net]-.1,x+.1,ys[net]+.1).to_itype(L.dbu))).is_empty()
    top.shapes(L.layer(134,0)).insert(pya.DBox(min(xa,xb)-.25,ys['avdd']-.25,max(xa,xb)+.25,ys['avdd']+.25))
    top.shapes(L.layer(134,0)).insert(pya.DBox(xb-.25,min(ys['avdd'],ys['avss'])-.25,xb+.25,max(ys['avdd'],ys['avss'])+.25))
    assert (pya.Region(top.shapes(L.layer(134,0)))-region).area()>0"""
            assert physical_source.count(before)==1
            physical_source=physical_source.replace(before,after)
            result['physical_fault_geometry_adaptation']=dict(before=before,after=after,
                scope='Actual avdd/avss pin-centre bridge only. Same DRC/LVS decks, expected fault verdicts and all other controls unchanged.')
        generator = out / 'generate.py'
        generator.write_text(source)
        physical_method=out/'verify-physical.py'
        physical_method.write_text(physical_source)
        result.update(source_bindings=spec, explicit_geometry_edits=edits,
                      generator_sha256=sha(generator), original_generator_sha256=sha(originals / 'layout91.py'),
                      physical_method_sha256=sha(physical_method),original_physical_method_sha256=sha(originals/'physical92.py'))
        app = Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app) == spec['runtime_sha256']
        run([app, 'python', generator, '--pdk', ROOT / 'pdk', '--out', out / 'layout'], 'generation')
        generated = json.loads((out / 'layout/result.json').read_text())
        result['layout'] = generated
        if args.circuit_profile in ('final_drive_v5','final_drive_v6','final_drive_v7','final_drive_v8'):
            result['generated_reference_equivalence']=audit(circuit.read_text(),native.read_text(),
                (out/'layout/schematic.cir').read_text(),profile=audit_profile)
        # The controller is standard Python; launching it inside the AppImage
        # would make its native child invocations require a nested FUSE mount.
        run([sys.executable, physical_method, '--layout', out / 'layout', '--out', out / 'physical', '--app', app], 'physical')
        physical = json.loads((out / 'physical/result.json').read_text())
        assert physical['status'] == 'PASS_NATIVE_PDK_TX_MUX54_DRC_LVS_AND_FAULT_CONTROLS'
        result['physical'] = {k: v for k, v in physical.items() if k != 'inputs'}
        assert all(sha(ROOT / n) == r['sha256'] for n, r in manifest['files'].items())
        result['status'] = 'PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        report = out / 'physical/result.json'
        if report.exists():
            result['physical'] = json.loads(report.read_text())
        # Preserve compact diagnostic text alongside the exact full archive.
        # This avoids a separate hosted archive-read job for every native failure.
        result['failure_reports']={}
        for child in sorted((out/'physical').glob('*/*')):
            if child.name not in ('extracted.cir','mutation.log') or not child.is_file():
                continue
            if child.stat().st_size<=256*1024:
                result['failure_reports'][str(child.relative_to(out))]=dict(
                    sha256=sha(child),bytes=child.stat().st_size,text=child.read_text(errors='replace'))

        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('layout', 'physical', 'source_bindings')}), flush=True)


if __name__ == '__main__':
    main()
