#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Calibrate the SRAM activity reader against native models and a real inventory.

This constructs a separate testbench containing the netlist's SRAM instances,
with known controls and independent A/B clocks. It does NOT simulate the SoC
workload and its energy numbers must never be quoted as SoC power.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

from macro_activity import collect, digest, ports
from macro_energy import estimate
from select_pnr_profile import mapped_macros

ROOT = Path(__file__).resolve().parents[3]


def bench(inventory, vcd):
    if any(c in str(vcd) for c in '\n\r"\\'):
        raise ValueError('VCD path cannot be represented as a Verilog string')
    text = ('`timescale 1ns/1ps\nmodule tb;\n'
            'reg ca=0, cb=0; reg [2:0] state=0; integer i;\n'
            'always #5 ca=~ca; always #7 cb=~cb;\n')
    for name, master in sorted(inventory.items()):
        if any(c.isspace() for c in name):
            raise ValueError('Invalid escaped instance name')
        geometry = re.search(r'_(\d+)x(\d+)_', master)
        depth, width = map(int, geometry.groups())
        addr_width = (depth-1).bit_length()
        connections = []
        for port in ports(master):
            values = dict(CLK='ca' if port=='A' else 'cb', MEN='state[2]', WEN='state[1]',
                          REN='state[0]', ADDR=f"{addr_width}'d"+('0' if port=='A' else '1'),
                          DIN=f"{width}'d0", DLY="1'b0", DOUT='', BM=f"{width}'d0",
                          BIST_CLK="1'b0", BIST_EN="1'b0", BIST_MEN="1'b0", BIST_WEN="1'b0",
                          BIST_REN="1'b0", BIST_ADDR=f"{addr_width}'d0", BIST_DIN=f"{width}'d0", BIST_BM=f"{width}'d0")
            connections += [f'.{port}_{pin}({value})' for pin,value in values.items()]
        text += f'{master} \\{name} ('+', '.join(connections)+');\n'
    text += ('initial begin\n$dumpfile("'+str(vcd)+'");\n')
    for name in sorted(inventory):
        text += '$dumpvars(1, tb.\\'+name+' );\n'
    text += ('#1; for(i=0;i<8;i=i+1) begin state=i; #70; end\n'
             '$display("MACRO_CALIBRATION_DONE"); $finish; end\nendmodule\n')
    return text


def check(netlist, pdk, iverilog, output):
    netlist, pdk, output = (Path(p).resolve() for p in (netlist,pdk,output))
    if not output.is_relative_to(ROOT/'hw/soc/out') or output.exists():
        raise ValueError('Use a fresh output directory under hw/soc/out')
    inventory = mapped_macros(netlist)
    models = pdk/'libs.ref/sg13g2_sram/verilog'
    sources = [models/(master+'.v') for master in sorted(set(inventory.values()))]
    if any('_1P_' in m for m in inventory.values()):
        sources += [models/'RM_IHPSG13_1P_core_behavioral_bm_bist.v']
    if any('_2P_' in m for m in inventory.values()):
        sources += [models/(name+'.v') for name in (
            'RM_IHPSG13_2P_core_behavioral_bm_bist_ideal', 'RM_IHPSG13_2P_core_behavioral_ideal')]
    hashes = {str(p.relative_to(pdk)):digest(p) for p in sources}
    nl_hash = digest(netlist)
    output.mkdir(parents=True)
    version = subprocess.run([str(iverilog),'-V'],capture_output=True,text=True,check=True)
    (output/'iverilog-version.log').write_text(version.stdout+version.stderr)
    match = re.search(r'Icarus Verilog version (\d+)',version.stdout)
    if not match or int(match[1]) < 13:
        raise ValueError('Native SRAM calibration requires Icarus >=13')
    tb=output/'tb.v'; vcd=output/'calibration.vcd'; exe=output/'sim.vvp'
    tb.write_text(bench(inventory,vcd))
    compile_command=[str(iverilog),'-g2012','-s','tb','-o',str(exe),str(tb)]+list(map(str,sources))
    with (output/'compile.log').open('w') as stream:
        subprocess.run(compile_command,stdout=stream,stderr=subprocess.STDOUT,timeout=120,check=True)
    run_command=[str(Path(iverilog).with_name('vvp')),str(exe)]
    with (output/'simulation.log').open('w') as stream:
        subprocess.run(run_command,stdout=stream,stderr=subprocess.STDOUT,timeout=120,check=True)
    if 'MACRO_CALIBRATION_DONE' not in (output/'simulation.log').read_text():
        raise ValueError('Calibration did not finish')
    # State changes at 1,71,... ns; each phase has 7 A edges and 5 B edges.
    activity=collect(vcd,netlist,'tb',2,561)
    for entry in activity['macros'].values():
        for port,row in entry['ports'].items():
            expected=7 if port=='A' else 5
            if set(row['state_edges'].values()) != {expected} or row['rising_edges'] != 8*expected:
                raise ValueError('Calibration disagrees with the independent clock/state schedule')
    (output/'activity.json').write_text(json.dumps(activity,indent=2)+'\n')
    results={corner:estimate(activity,netlist,pdk,corner) for corner in
             ('typ_1p20V_25C','slow_1p08V_125C','fast_1p32V_m55C')}
    if nl_hash != digest(netlist) or hashes != {str(p.relative_to(pdk)):digest(p) for p in sources}:
        raise ValueError('Calibration inputs changed')
    result=dict(status='PASS',scope=__doc__,netlist_sha256=nl_hash,macros=len(inventory),
                clock_ports=sum(len(ports(m)) for m in inventory.values()),
                model_sha256=hashes,commands=[compile_command,run_command],
                source_sha256={str(p.relative_to(ROOT)):digest(p) for p in
                 [Path(__file__).resolve(),ROOT/'hw/soc/flow/macro_activity.py',ROOT/'hw/soc/flow/macro_energy.py',ROOT/'hw/soc/flow/select_pnr_profile.py',ROOT/'hw/soc/flow/vcd_activity.py']},
                artifacts={p.name:digest(p) for p in (tb,vcd,output/'activity.json',output/'simulation.log')},
                calibration_energy_only=results)
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--netlist',required=True,type=Path)
    ap.add_argument('--pdk-dir',required=True,type=Path)
    ap.add_argument('--iverilog',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    try:
        result=check(args.netlist,args.pdk_dir,args.iverilog.resolve(),args.output)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        ap.exit(2,str(error)+'\n')
    print(json.dumps({k:result[k] for k in ('status','macros','clock_ports')}))


if __name__=='__main__':
    main()
