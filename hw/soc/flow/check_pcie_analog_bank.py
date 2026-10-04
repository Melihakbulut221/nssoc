#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict native verification of RXv2 or four-lane analog bank; no PHY acceptance."""
import argparse
import json
from pathlib import Path
import re
from check_pcie_rx_cell import execute
from check_ihp_drc import digest, record_result
from prepare_ihp_drc import validate_lock, verify
from make_pcie_analog_bank import TOP as BANK, use_direction
from make_pcie_rx_cell_v2 import TOP as RX

APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'


def fault_reference(text,kind,fault):
    if kind=='rx-v2':
        changes={'wrong_load':('RRP AVDD OUTP BULK RSIL W=2U L=27.5U','RRP AVDD OUTP BULK RSIL W=2U L=28.5U'),
                 'wrong_input':('QP OUTN INP TAIL','QP OUTN INN TAIL'),
                 'missing_tap':('RTAP0 SUB BULK ptap1 A=4p P=8u\n','')}
    else:
        changes={'wrong_load':('R0RX_RP AVDD L0_RX_OUTP BULK RSIL W=2U L=27.5U','R0RX_RP AVDD L0_RX_OUTP BULK RSIL W=2U L=28.5U'),
                 'wrong_lane':('Q2RX_P L2_RX_OUTN L2_RX_INP L2_RX_TAIL','Q2RX_P L2_RX_OUTN L1_RX_INP L2_RX_TAIL'),
                 'missing_tap':('R0TX_TAP0 SUB BULK ptap1 A=4p P=8u\n','')}
    if fault not in changes:raise ValueError('Unknown strict comparison fault')
    old,new=changes[fault]
    if text.count(old)!=1:raise ValueError('Fault must bind exactly one original device')
    return text.replace(old,new)


def quote(value):
    text=str(value)
    if any(c in text for c in '{}\n\r'):raise ValueError('Unsafe Tcl path')
    return '{'+text+'}'


def lef_script(pdk,lef,top,record):
    ports=record['ports'];box=record['bbox_um']
    if isinstance(box,str):
        box=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',box)]
    lines=['read_lef '+quote(pdk/'libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'),
           'read_lef '+quote(lef),'set master [[ord::get_db] findMaster '+top+']',
           'if {$master eq "NULL"} {error "Analog master missing"}',
           f'if {{[$master getWidth] != {round(box[2]*1000)} || [$master getHeight] != {round(box[3]*1000)}}} {{error "Analog outline changed"}}',
           f'if {{[llength [$master getMTerms]] != {len(ports)}}} {{error "Analog terminal census changed"}}']
    for name,port in ports.items():
        use,direction=use_direction(name) if top==BANK else ('POWER','INOUT') if name=='AVDD' else ('GROUND','INOUT') if name in ('AVSS','SUB') else ('SIGNAL','OUTPUT' if name in ('OUTP','OUTN') else 'INPUT')
        coords=' '.join(str(round(v*1000)) for v in port['rect_um'])
        lines += ['set term [$master findMTerm '+name+']','if {$term eq "NULL"} {error "Analog terminal missing"}',
                  'if {[$term getIoType] ne "'+direction+'" || [$term getSigType] ne "'+use+'"} {error "Analog pin direction/use differs"}',
                  'set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}',
                  'if {$boxes ne {{'+port['layer']+' '+coords+'}}} {error "Analog port geometry differs"}']
    lines += ['set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}',
              'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Analog blockage layer census changed"}',
              'puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY']
    return '\n'.join(lines)+'\n'


def validate_lef(code,text,negative):
    banner='PASS_NATIVE_ANALOG_BANK_LEF_ONLY'
    if negative:
        if code==0 or banner in text or len(re.findall(r'^Error: inspect\.tcl, \d+ Analog terminal census changed$',text,re.M))!=1:
            raise ValueError('LEF negative failed for an unexpected reason')
    elif code!=0 or text.count(banner)!=1 or re.search(r'^Error:|\[ERROR',text,re.M):raise ValueError('Native LEF check failed')


def mutation_source(gds,out,top,fault,generated):
    prefix='import pya\nl=pya.Layout()\nl.read('+repr(str(gds))+')\nc=l.cell('+repr(top)+')\n'
    if fault=='physical_open':
        row=next(r for r in generated['routes'] if (r['lane'],r['kind'],r['terminal'])==(2,'RX','INP'))
        b=row['source_m5_rect_um'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2
        prefix+=f'''matches=[]
for i in c.each_inst():
    b=i.dbbox(); child=l.cell(i.cell_index)
    if abs(b.center().x-{x!r})<0.001 and abs(b.center().y-{y!r})<0.001 and not pya.Region(child.begin_shapes_rec(l.layer(125,0))).is_empty():matches.append(i)
if len(matches)!=1:raise ValueError('Physical open must remove exactly one measured topvia1 instance')
matches[0].delete()
'''
    elif fault=='physical_bulk_short':
        prefix+='c.shapes(l.layer(134,0)).insert(pya.DBox(230,1,246,3))\n'
    elif fault=='physical_offgrid':prefix+='c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))\n'
    else:raise ValueError('Unknown physical mutation')
    return prefix+'l.write('+repr(str(out))+')\n'



def extracted_ports(text,top):
    lines=[]
    for line in text.splitlines():
        if line.startswith('+'):
            if not lines:raise ValueError('Orphan SPICE continuation')
            lines[-1]+=' '+line[1:].strip()
        elif line.strip() and not line.startswith('*'):lines.append(line.strip())
    headers=[line.split() for line in lines if line.lower().startswith('.subckt ')]
    if len(headers)!=1 or headers[0][1]!=top:raise ValueError('Extracted top differs')
    ports=headers[0][2:]
    if len(ports)!=len(set(ports)):raise ValueError('Duplicate extracted top port')
    return set(ports)


def validate_open_rejection(step,text,expected):
    # Removing the outer input via preserves internal devices but makes one
    # expected top-level port disappear. The unchanged strict deck rejects it.
    audit=step['audit']
    if (step['status']!='FAIL' or step['audit_execution']['returncode']!=1 or
        audit['circuit_status_counts']!={'Match':1} or audit['extraction_diagnostics'] or
        set(audit['reasons'])!={'Missing explicit successful deck verdict','Deck explicitly reported a mismatch'} or
        len(audit['circuits'])!=1 or audit['circuits'][0]['layout_devices_recursive']!=57 or
        audit['circuits'][0]['schematic_devices_recursive']!=57 or
        extracted_ports(text,BANK)!=set(expected)-{'L2_RX_INP'}):
        raise ValueError('Physical input open did not produce its exact strict port mismatch')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('layout','pdk','out'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--kind',choices=('bank','rx-v2'),required=True)
    a=parser.parse_args();root=Path(__file__).resolve().parents[3];out=a.out.resolve();layout=a.layout.resolve();pdk=a.pdk.resolve()
    if out.exists() or not (out.is_relative_to(root/'hw/soc/out') or out.is_relative_to(Path('/dev/shm')) and out.name.startswith('nssoc-bank-')):parser.error('Fresh project or /dev/shm/nssoc-bank- output required')
    top=BANK if a.kind=='bank' else RX;app=root/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
    if digest(app)!=APP_SHA:raise ValueError('Native runtime changed')
    generated=json.loads((layout/'result.json').read_text());gds=layout/(top+'.gds');schematic=layout/'schematic.cir'
    pins={Path(k):v for k,v in generated['input_sha256'].items()}
    for name,value in generated['output_sha256'].items():
        if digest(layout/name)!=value:raise ValueError('Generated view changed')
        pins[layout/name]=value
    for path in [Path(__file__).resolve(),app,layout/'result.json',root/'hw/soc/flow/check_pcie_rx_cell.py',root/'hw/soc/flow/check_ihp_drc.py',root/'hw/soc/flow/prepare_ihp_drc.py',root/'hw/soc/flow/audit_klayout_lvs.py',root/'hw/soc/flow/make_pcie_analog_bank.py',root/'hw/soc/flow/make_pcie_rx_cell_v2.py',pdk/'libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef']:pins[path]=digest(path)
    for typ in ('drc','lvs'):
        path=root/f'hw/soc/pnr/ihp-{typ}.lock.json';lock=json.loads(path.read_text());validate_lock(lock)
        if lock['commit']!='5e6d592e4002946a4616f798c357f0f3c06cf3b6':raise ValueError('Deck revision changed')
        pins[path]=digest(path)
        for row in lock['files']:
            path=root/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(path.read_bytes(),row);pins[path]=row['sha256']
    if any(not p.is_file() or digest(p)!=v for p,v in pins.items()):raise ValueError('Native inputs changed before execution')
    out.mkdir(parents=True);record=dict(status='RUNNING',kind=a.kind,inputs={str(p):v for p,v in pins.items()},steps=[],phy_complete=False,main_chip_integrated=False,qualified_pex=False)
    def save():(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    def mutate(name,directory):
        wrong=directory/'wrong.gds';script=directory/'mutate.py';script.write_text(mutation_source(gds,wrong,top,name,generated))
        execution=execute([app,'python',script],directory,'mutation')
        if execution['returncode']!=0 or digest(wrong)==digest(gds):raise ValueError('Physical fault did not bind')
        return wrong,execution
    faults=['wrong_load','wrong_lane' if a.kind=='bank' else 'wrong_input','missing_tap']
    if a.kind=='bank':faults+=['physical_open','physical_bulk_short']
    try:
        save()
        for name in ['drc','physical_offgrid','lvs']+faults:
            d=out/name;d.mkdir();step=dict(name=name);record['steps'].append(step);save();physical=gds;net=schematic
            if name.startswith('physical_'):physical,step['mutation_execution']=mutate(name,d)
            if name in faults and not name.startswith('physical_'):
                net=d/'wrong.cir';net.write_text(fault_reference(schematic.read_text(),a.kind,name))
            drc=name in ('drc','physical_offgrid')
            entry=root/('hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc' if drc else 'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs')
            options=['input='+str(physical),'topcell='+top,'log='+str(d/'deck.log'),'run_mode=flat' if not drc else 'run_mode=deep']
            options+=['report='+str(d/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False'] if drc else ['schematic='+str(net),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),'thr=2']
            command=[app,'klayout','-b','-zz','-r',entry]
            for option in options:command+=['-rd',option]
            step['execution']=execute(command,d,'run')
            if step['execution']['returncode']!=0:raise ValueError('Native deck did not complete')
            if drc:
                step['measurement']=record_result(d,top,0,pins);step['status']=step['measurement']['status']
                if step['measurement']['category_count']!=560 or "KLayout DRC run for tables 'main' completed" not in (d/'run.log').read_text():raise ValueError('Main DRC did not fully complete')
            else:
                step['audit_execution']=execute([app,'python',root/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',top,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
                step['audit']=json.loads((d/'audit.json').read_text());step['status']=step['audit']['status']
            save();print(name,step['status'],flush=True)
        for negative in (False,True):
            d=out/('lef_missing_pin' if negative else 'lef');d.mkdir();view=layout/(top+'.lef')
            if negative:
                pin='L0_RX_VCM' if a.kind=='bank' else 'VCM'
                text,count=re.subn(r'  PIN '+pin+r'\n.*?  END '+pin+r'\n','',view.read_text(),flags=re.S)
                if count!=1:raise ValueError('LEF fault binding differs')
                view=d/'wrong.lef';view.write_text(text)
            script=d/'inspect.tcl';script.write_text(lef_script(pdk,view,top,generated));execution=execute([app,'openroad','-exit',script],d,'native')
            validate_lef(execution['returncode'],(d/'native.log').read_text(),negative)
            record['steps'].append(dict(name=d.name,status='EXPECTED_REJECTION' if negative else 'PASS',execution=execution));save()
        for step in record['steps'][:-2]:
            name=step['name']
            if name in ('drc','lvs'):
                if not step['status'].startswith('PASS'):raise ValueError('Positive physical verification failed')
                if name=='lvs':
                    audit=step['audit'];expected=57 if a.kind=='bank' else 9
                    if extracted_ports((out/'lvs/extracted.cir').read_text(),top)!=set(generated['ports']):raise ValueError('Positive extracted ports differ')
                    if step['audit_execution']['returncode']!=0 or len(audit['circuits'])!=1 or audit['circuits'][0]['layout_devices_recursive']!=expected or audit['circuits'][0]['schematic_devices_recursive']!=expected:raise ValueError('Positive device census differs')
            elif name=='physical_open':
                validate_open_rejection(step,(out/name/'extracted.cir').read_text(),generated['ports'])
            elif name=='physical_offgrid':
                if step['status']!='FAIL' or step['measurement']['categories'].get('metal1_drw_Offgrid',0)<1:raise ValueError('Offgrid fault was not detected')
            elif step['status']!='FAIL' or step['audit_execution']['returncode']!=1 or step['audit']['circuit_status_counts'].get('NoMatch',0)<1:raise ValueError('Strict negative did not reject')
        if any(digest(p)!=v for p,v in pins.items()):raise ValueError('Inputs changed during checks')
        record['status']='PASS_NATIVE_'+('BANK4' if a.kind=='bank' else 'RX_V2')+'_MAIN_DRC_STRICT_LVS_LEF_AND_NEGATIVE_CONTROLS_ONLY'
        record['outputs']={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'result.json'};save()
    except BaseException as e:record.update(status='FAILED_OR_INCOMPLETE',error=repr(e));save();raise


if __name__=='__main__':main()
