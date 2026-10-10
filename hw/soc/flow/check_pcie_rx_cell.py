#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native DRC/LVS and LEF checks for one RX preamplifier, never a PHY signoff."""
import argparse
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time

from check_ihp_drc import digest, record_result
from make_pcie_rx_cell import PORTS, TOP
from prepare_ihp_drc import validate_lock, verify


def fault_reference(source, fault):
    changes = {
        'termination_width': ('RRTP INP VCM BULK RSIL W=10U', 'RRTP INP VCM BULK RSIL W=11U'),
        'tail_nx': ('QTAIL TAIL IREF AVSS BULK NPN13G2 NX=4', 'QTAIL TAIL IREF AVSS BULK NPN13G2 NX=3'),
        'missing_tap': ('RTAP0 SUB BULK ptap1 A=4p P=8u\n', ''),
        'wrong_input': ('QP OUTN INP TAIL', 'QP OUTN INN TAIL'),
        'bulk_short': ('QTAIL TAIL IREF AVSS BULK', 'QTAIL TAIL IREF AVSS AVSS'),
    }
    if fault not in changes:
        raise ValueError('Unknown physical comparison fault')
    old, new = changes[fault]
    if source.count(old) != 1:
        raise ValueError('Fault is absent or ambiguous')
    return source.replace(old, new)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def execute(command, directory, label):
    environment = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME')}
    start = time.monotonic()
    with (directory/(label+'.log')).open('x') as log:
        proc = subprocess.run(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT,
                              env=environment, preexec_fn=limits, check=False)
    return dict(command=list(map(str, command)), returncode=proc.returncode, seconds=time.monotonic()-start,
                memory_limit_bytes=2*1024**3, elapsed_watchdog=None,
                log_sha256=digest(directory/(label+'.log')))


def validate_lef_result(code, text, negative):
    banner = 'PASS_RX_NATIVE_LEF_NINE_REAL_PORTS_SEVEN_OBSTRUCTED_LAYERS_NO_TIMING_ACCEPTANCE'
    if negative:
        if code == 0 or banner in text or len(re.findall(
                r'^Error: inspect\.tcl, \d+ RX terminal census changed$', text, re.M)) != 1:
            raise ValueError('Native missing-pin control failed for an unexpected reason')
    elif code != 0 or text.count(banner) != 1 or re.search(r'^Error:|\[ERROR', text, re.M):
        raise ValueError('Native LEF control did not pass')


def lef_script(pdk, lef, generated):
    def quote(value):
        text = str(value)
        if any(c in text for c in '{}\n\r'):
            raise ValueError('Unsafe Tcl path')
        return '{'+text+'}'
    lines = ['read_lef '+quote(pdk/'libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'),
             'read_lef '+quote(lef), 'set master [[ord::get_db] findMaster '+TOP+']',
             'if {$master eq "NULL"} {error "RX master missing"}',
             'if {[$master getWidth] != 167000 || [$master getHeight] != 158000} {error "RX outline changed"}',
             'if {[llength [$master getMTerms]] != 9} {error "RX terminal census changed"}']
    for name in PORTS:
        coords = ' '.join(str(round(v*1000)) for v in generated['ports'][name]['rect_um'])
        use = 'POWER' if name == 'AVDD' else 'GROUND' if name in ('AVSS', 'SUB') else 'SIGNAL'
        direction = 'OUTPUT' if name in ('OUTP', 'OUTN') else 'INOUT' if use != 'SIGNAL' else 'INPUT'
        lines += ['set term [$master findMTerm '+name+']',
                  'if {$term eq "NULL"} {error "RX terminal missing"}',
                  'if {[$term getIoType] ne "'+direction+'" || [$term getSigType] ne "'+use+'"} {error "RX terminal type differs"}',
                  'set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}',
                  'if {$boxes ne {{Metal5 '+coords+'}}} {error "RX terminal geometry differs: '+name+'"}']
    lines += ['set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}',
              'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "RX obstruction layer census differs"}',
              'if {[llength $obs] != 20} {error "RX obstruction box census differs"}',
              'puts PASS_RX_NATIVE_LEF_NINE_REAL_PORTS_SEVEN_OBSTRUCTED_LAYERS_NO_TIMING_ACCEPTANCE']
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--pdk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve(); layout = args.layout.resolve(); pdk = args.pdk.resolve()
    if out.exists() or not (out.is_relative_to(root/'hw/soc/out') or out.is_relative_to(Path('/dev/shm')) and out.name.startswith('nssoc-rx-')):
        parser.error('Use a fresh project or /dev/shm/nssoc-rx- output directory')
    generated = json.loads((layout/'result.json').read_text())
    app = root/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
    if digest(app) != 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466':
        raise ValueError('Physical runtime differs from the validated runtime')
    gds = layout/(TOP+'.gds'); schematic = layout/'schematic.cir'
    for name, expected in generated['output_sha256'].items():
        if digest(layout/name) != expected:
            raise ValueError('Generated physical input changed')
    pins = {Path(path): sha for path, sha in generated['input_sha256'].items()}
    for path in (Path(__file__).resolve(), root/'hw/soc/flow/check_ihp_drc.py', root/'hw/soc/flow/audit_klayout_lvs.py',
                 app, layout/'result.json', gds, schematic, layout/(TOP+'.lef'), pdk/'libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'):
        pins[path] = digest(path)
    for typ in ('drc', 'lvs'):
        lock_path = root/f'hw/soc/pnr/ihp-{typ}.lock.json'
        lock = json.loads(lock_path.read_text()); validate_lock(lock)
        if lock['commit'] != '5e6d592e4002946a4616f798c357f0f3c06cf3b6':
            raise ValueError('Native verification revision differs')
        pins[lock_path] = digest(lock_path)
        for row in lock['files']:
            path = root/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path']
            verify(path.read_bytes(), row)
            pins[path] = row['sha256']
    pins[root/'hw/soc/flow/prepare_ihp_drc.py'] = digest(root/'hw/soc/flow/prepare_ihp_drc.py')
    if any(not p.is_file() or digest(p) != v for p, v in pins.items()):
        raise ValueError('Generation source changed before verification')
    out.mkdir(parents=True)
    record = dict(status='RUNNING', inputs={str(p): h for p,h in pins.items()}, steps=[], phy_complete=False,
                  qualified_pex=False, manufacturing_approval=False, scope='One native RX preamplifier only; no full-chip inputs.')
    def save():
        (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    try:
        save()
        for name in ('drc', 'drc_offgrid', 'lvs', 'termination_width', 'tail_nx', 'missing_tap', 'wrong_input', 'bulk_short'):
            directory=out/name;directory.mkdir();step=dict(name=name);record['steps'].append(step);save()
            if name in ('drc', 'drc_offgrid'):
                physical = gds
                if name == 'drc_offgrid':
                    physical = directory/'wrong.gds'
                    mutation = directory/'mutate.py'
                    mutation.write_text('import pya\nl=pya.Layout()\nl.read('+repr(str(gds))+')\n'
                                        'c=l.cell('+repr(TOP)+')\n'
                                        'c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2.0,2.102,2.1))\n'
                                        'l.write('+repr(str(physical))+')\n')
                    step['mutation_execution'] = execute([app,'python',mutation],directory,'mutate')
                    if step['mutation_execution']['returncode'] != 0 or digest(physical) == digest(gds):
                        raise ValueError('Physical off-grid fault did not bind')
                entry=root/'hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc'
                options=['input='+str(physical),'topcell='+TOP,'report='+str(directory/'drc.lyrdb'),'log='+str(directory/'deck.log'),
                         'threads=2','run_mode=deep','no_recommended=False','precheck_drc=False']
            else:
                entry=root/'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs';net=schematic
                if name!='lvs':
                    net=directory/'wrong.cir';net.write_text(fault_reference(schematic.read_text(), name))
                options=['input='+str(gds),'schematic='+str(net),'topcell='+TOP,'report='+str(directory/'result.lvsdb'),
                         'log='+str(directory/'deck.log'),'target_netlist='+str(directory/'extracted.cir'),'run_mode=deep','thr=2']
            command=[app,'klayout','-b','-zz','-r',entry]
            for option in options:command+=['-rd',option]
            step['execution']=execute(command,directory,'run')
            if name in ('drc', 'drc_offgrid'):
                step['measurement']=record_result(directory,TOP,step['execution']['returncode'],pins)
                step['status']=step['measurement']['status']
                if step['measurement'].get('category_count') != 560:
                    raise ValueError('Incomplete native main-rule category census')
                if "KLayout DRC run for tables 'main' completed" not in (directory/'run.log').read_text():
                    raise ValueError('Native main deck did not record completion')
            else:
                command=[app,'python',root/'hw/soc/flow/audit_klayout_lvs.py',directory/'result.lvsdb','--top',TOP,
                         '--deck-log',directory/'deck.log','--output',directory/'audit.json']
                step['audit_execution']=execute(command,directory,'audit')
                step['audit']=json.loads((directory/'audit.json').read_text());step['status']=step['audit']['status']
            save();print(name,step['status'],flush=True)
        for negative in (False,True):
            directory=out/('lef_missing_pin' if negative else 'lef');directory.mkdir();lef=layout/(TOP+'.lef')
            if negative:
                text=lef.read_text();text,count=re.subn(r'  PIN VCM\n.*?  END VCM\n','',text,flags=re.S)
                if count!=1:raise ValueError('Missing-pin LEF fault did not bind')
                lef=directory/'wrong.lef';lef.write_text(text)
            script=directory/'inspect.tcl';script.write_text(lef_script(pdk,lef,generated))
            step=dict(name=directory.name,execution=execute([app,'openroad','-exit',script],directory,'native'))
            text=(directory/'native.log').read_text()
            validate_lef_result(step['execution']['returncode'], text, negative)
            step['status']='EXPECTED_REJECTION' if negative else 'PASS';record['steps'].append(step);save()
        for step in record['steps'][:8]:
            if step['execution']['returncode']!=0:raise ValueError('Native deck did not complete')
            if step['name'] in ('drc','lvs'):
                if not step['status'].startswith('PASS'):raise ValueError('RX physical check failed')
                if step['name']=='lvs' and step['audit_execution']['returncode']!=0:
                    raise ValueError('Native positive LVS audit did not complete')
            elif step['name'] == 'drc_offgrid':
                if step['status'] != 'FAIL' or step['measurement']['categories'].get('metal1_drw_Offgrid',0) <= 0:
                    raise ValueError('Physical off-grid fault was accepted')
            elif step['status']!='FAIL' or step['audit_execution']['returncode']!=1 or step['audit']['circuit_status_counts'].get('NoMatch',0)<1:
                raise ValueError('RX negative comparison was accepted')
        if any(digest(p)!=h for p,h in pins.items()):raise ValueError('Physical verification inputs changed')
        record['output_sha256'] = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p != out/'result.json'}
        record['status']='PASS_RX_CELL_MAIN_DRC_LVS_AND_SEVEN_NEGATIVE_CONTROLS_WITH_NATIVE_LEF_ONLY';save()
    except BaseException as error:
        record.update(status='FAILED_OR_INCOMPLETE',error=repr(error));save();raise


if __name__=='__main__':
    main()
