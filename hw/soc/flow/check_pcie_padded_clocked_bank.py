#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict native checks for the fixed VCO and eight real sampler clock branches."""

import argparse
import json
from pathlib import Path
import re
from collections import Counter

from check_ihp_drc import digest, record_result
from check_pcie_analog_bank import extracted_ports, quote, validate_lef
from check_pcie_rx_cell import execute
from make_pcie_padded_clocked_bank import PORTS, TOP, HEIGHT, WIDTH, PARENTS, LAYERS, SERIAL, reference as physical_reference, use_direction
from prepare_ihp_drc import validate_lock, verify

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
REFERENCE_FAULTS = ("wrong_lane", "missing_tap", "wrong_diode", "wrong_return", "wrong_clamp_rail", "wrong_clock", "wrong_follower")
PHYSICAL_FAULTS = tuple("open_" + name for name in SERIAL) + ("return_avss_short", "return_sub_short", "clamp_supply_short")


def fault_reference(text, fault):
    changes={
      "wrong_lane":("QBANK_2RX_P L2_RX_OUTN L2_RX_INP L2_RX_TAIL", "QBANK_2RX_P L2_RX_OUTN L1_RX_INP L2_RX_TAIL"),
      "missing_tap":("RVCO_TAP0 SUB ESD_RETURN ptap1 A=4p P=8u\n", ""),
      "wrong_diode":("D0TX_Pdd ESD_VDD L0_TX_OUTP ESD_RETURN diodevdd_2kv m=1", "D0TX_Pdd ESD_VDD L0_TX_OUTP ESD_RETURN diodevdd_2kv m=2"),
      "wrong_return":("D0TX_Pdd ESD_VDD L0_TX_OUTP ESD_RETURN", "D0TX_Pdd ESD_VDD L0_TX_OUTP AVSS"),
      "wrong_clamp_rail":("D0RX_Nss ESD_VDD L0_RX_INN ESD_RETURN", "D0RX_Nss AVDD1V8 L0_RX_INN ESD_RETURN"),
      "wrong_clock":("QBANK_2SAMPLER_M_CS L2_SAMPLER_M_SE CLOCKN", "QBANK_2SAMPLER_M_CS L2_SAMPLER_M_SE CLOCKP"),
      "wrong_follower":("QVCO_FPD2 AVDD2V3 VCO_BO_P CLOCKP ESD_RETURN npn13G2 Nx=4", "QVCO_FPD2 AVDD2V3 VCO_BO_P CLOCKP ESD_RETURN npn13G2 Nx=3")}
    if fault not in changes:raise ValueError('Unknown reference fault')
    old,new=changes[fault]
    if text.count(old)!=1:raise ValueError('Reference fault must bind exactly once')
    return text.replace(old,new)


def mutation_source(gds, output, generated, fault):
    lines=["import pya", "l=pya.Layout()", "l.read("+repr(str(gds))+")", "c=l.cell("+repr(TOP)+")"]
    if fault=='offgrid':
        lines += ["c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))"]
    elif fault.startswith('open_') and fault[5:] in SERIAL:
        hits=[row for row in generated['serial_connections'] if row['net']==fault[5:]]
        if len(hits)!=1:raise ValueError('Exact serial bridge missing')
        b=hits[0]['bridge']['rect_um'];x=round((b[0]+b[2])/2/.005)*.005;y=(b[1]+b[3])/2
        lines += ['region=pya.Region(c.shapes(l.layer(126,0)))', f'region-=pya.Region(pya.DBox({x-.1!r},{y-2!r},{x+.1!r},{y+2!r}).to_itype(l.dbu))', 'c.shapes(l.layer(126,0)).clear()', 'c.shapes(l.layer(126,0)).insert(region)']
    elif fault in ('return_avss_short','return_sub_short','clamp_supply_short'):
        pair={'return_avss_short':('ESD_RETURN','AVSS'),'return_sub_short':('ESD_RETURN','SUB'),'clamp_supply_short':('ESD_VDD','AVDD2V5')}[fault]
        xs=[sum(generated['ports'][n]['rect_um'][i] for i in (0,2))/2 for n in pair]
        hits=[r for r in generated['vias'] if r['net']=='ESD_RETURN' and r['bottom']=='Metal5' and r['top']=='TopMetal2']
        if len(hits)!=1:raise ValueError('Exact native via witness missing')
        x,y=hits[0]['center_um'];yy=HEIGHT-10
        lines += [f'matches=[i for i in c.each_inst() if i.dbbox().center()==pya.DPoint({x!r},{y!r}) and not pya.Region(l.cell(i.cell_index).begin_shapes_rec(l.layer(133,0))).is_empty()]', "if len(matches)!=1:raise ValueError('Native via witness does not bind once')", 'native=matches[0]', f'for xx in {xs!r}:', f' t=native.dtrans; t.disp=pya.DVector(t.disp.x+xx-{x!r},t.disp.y+{yy!r}-{y!r}); c.insert(pya.DCellInstArray(native.cell_index,t))', f'c.shapes(l.layer(67,0)).insert(pya.DBox({min(xs)!r},{yy-1!r},{max(xs)!r},{yy+1!r}))']
    else:raise ValueError('Unknown actual geometry fault')
    return '\n'.join(lines+["l.write("+repr(str(output))+")",''])


def lef_script(pdk, lef, generated):
    box = generated["bbox_um"]
    lines = ["read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
             "read_lef " + quote(lef), "set master [[ord::get_db] findMaster " + TOP + "]",
             'if {$master eq "NULL"} {error "Padded padded clocked bank master missing"}',
             f'if {{[$master getWidth] != {round(box[2]*1000)} || [$master getHeight] != {round(box[3]*1000)}}} {{error "Padded padded clocked bank outline changed"}}',
             'if {[llength [$master getMTerms]] != 56} {error "Analog terminal census changed"}']
    if set(generated["ports"]) != set(PORTS):
        raise ValueError("Padded padded clocked bank LEF pin census differs")
    for name in PORTS:
        use, direction = use_direction(name)
        coords = " ".join(str(round(v*1000)) for v in generated["ports"][name]["rect_um"])
        metal = generated["ports"][name]["layer"]
        lines += ["set term [$master findMTerm " + name + "]",
                  'if {$term eq "NULL"} {error "Padded padded clocked bank terminal missing"}',
                  'if {[$term getIoType] ne "' + direction + '" || [$term getSigType] ne "' + use + '"} {error "Padded padded clocked bank terminal type differs"}',
                  'set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}',
                  'if {$boxes ne {{' + metal + ' ' + coords + '}}} {error "Padded padded clocked bank terminal geometry differs"}']
    lines += ['set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}',
              'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Padded padded clocked bank blockage layer census changed"}',
              'foreach term [$master getMTerms] {foreach pin [$term getMPins] {foreach pb [$pin getGeometry] {foreach ob [$master getObstructions] {',
              'if {[[$pb getTechLayer] getName] eq [[$ob getTechLayer] getName] && [$pb xMin] < [$ob xMax] && [$ob xMin] < [$pb xMax] && [$pb yMin] < [$ob yMax] && [$ob yMin] < [$pb yMax]} {error "Padded padded clocked bank pin obstruction overlap"}',
              '}}}}', 'puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY']
    return "\n".join(lines) + "\n"


def validate_lvs(step, text, positive):
    audit = step["audit"]
    if positive:
        if (audit["status"] != "PASS within comparison scope" or step["audit_execution"]["returncode"] != 0 or
                extracted_ports(text, TOP) != set(PORTS) or len(audit["circuits"]) != 1 or
                audit["circuits"][0]["layout_devices_recursive"] != 232 or
                audit["circuits"][0]["schematic_devices_recursive"] != 232):
            raise ValueError("Positive padded clocked bank LVS/port/device census did not pass")
    elif audit["status"] != "FAIL" or step["audit_execution"]["returncode"] != 1:
        raise ValueError("Native padded clocked bank negative was accepted")
    elif audit["circuit_status_counts"].get("NoMatch", 0) < 1:
        raise ValueError("Native padded clocked bank fault failed for an unrelated reason")


def validate_device_rows(rows):
    counts=Counter(r['model'] for r in rows)
    if counts!={'npn13G2':110,'rsil':24,'rppd':57,'cap_cmim':6,'sg13_hv_pmos':1,'ptap1':1,'ntap1':1,'diodevdd_2kv':16,'diodevss_2kv':16}:
        raise ValueError('Complete232-device census differs')
    esd=[];expanded=[];parallel={};tap=[]
    for row in rows:
        model,nets,parameters=row['model'],row['nets'],row['parameters']
        if model=='npn13G2':
            if nets['S']!='ESD_RETURN' or parameters['we']!=.07 or parameters['le']!=.9:
                raise ValueError('Native HBT shared body/geometry differs')
            nx,m=parameters['Nx'],parameters['m']
            if nx not in (1,2,4,8) or m not in (1,4):raise ValueError('Native HBT multiplicity differs')
            expanded += [int(nx)]*int(m)
            if m==4:
                if nets['C']=='AVDD2V3' and nets['E'] not in PORTS and nx==4:identity=('follower',nets['E'])
                elif nets['C'] not in PORTS and nets['E']=='AVSS' and nx==2:identity=('sink',nets['C'])
                else:raise ValueError('Actual strong driver topology differs')
                if identity in parallel:raise ValueError('Duplicate driver group')
                parallel[identity]=nets
        if model in ('rsil','rppd') and nets[model+'_sub']!='ESD_RETURN':raise ValueError('Actual resistor body differs')
        if model=='ptap1':
            if nets!={'TIE':'SUB','WELL':'ESD_RETURN'} or parameters['A']!=432 or parameters['P']!=864:raise ValueError('108 finite SUB taps lost/shorted')
            tap.append(row)
        if model=='ntap1':
            if nets['TIE']!='AVDD2V3' or nets['WELL'] in PORTS or parameters['A']!=4 or parameters['P']!=8:raise ValueError('Finite NWell contact differs')
        if model in ('diodevdd_2kv','diodevss_2kv'):
            expected={'C':'ESD_RETURN' if model=='diodevdd_2kv' else 'ESD_VDD','B':'ESD_VDD' if model=='diodevdd_2kv' else 'ESD_RETURN'}
            if any(nets[k]!=v for k,v in expected.items()) or parameters['m']!=1:raise ValueError('Native ESD named terminals/return differs')
            esd.append((model,nets['E']))
    if sorted(expanded)!=[1]*14+[2]*49+[4]*47+[8]*12 or {n for k,n in parallel if k=='follower'}!={n for k,n in parallel if k=='sink'} or len(parallel)!=4:raise ValueError('Expanded122 branches and actual pairs differ')
    if Counter(esd)!=Counter((m,n) for m in ('diodevdd_2kv','diodevss_2kv') for n in SERIAL):raise ValueError('Exact16serial/32ESD graph differs')
    return dict(device_counts=dict(counts),named_esd_connections=esd,finite_substrate_contact=tap,expanded_hbt_instances=len(expanded),actual_driver_pairs=parallel.keys())


def inspect_native(layout,dbpath,out):
    import pya
    rec=json.loads((layout/'result.json').read_text());l=pya.Layout();l.read(str(layout/(TOP+'.gds')));top=l.cell(TOP)
    for label,contract in PARENTS.items():
        paths=[Path(p) for p,h in rec['input_sha256'].items() if Path(p).name==contract['top']+'.gds' and h==contract['gds']]
        if len(paths)!=1:raise ValueError('Exact parent source binding missing')
        native=pya.Layout();native.read(str(paths[0]));old=native.cell(contract['top']);copied=l.cell('padded_clocked_'+label)
        for info in set(native.layer_infos())|set(l.layer_infos()):
            if info.datatype in (2,25):continue
            if not(pya.Region(old.begin_shapes_rec(native.layer(info)))^pya.Region(copied.begin_shapes_rec(l.layer(info)))).is_empty():raise ValueError('Frozen parent conductive/device geometry changed')
    found=[]
    for inst in top.each_inst():
        name=l.cell(inst.cell_index).name
        if name in ('padded_clocked_bank','padded_clocked_pad'):found.append((name,str(inst.dtrans)))
    expected=[('padded_clocked_bank',str(pya.DTrans(400.,400.)))]+[('padded_clocked_pad',str(pya.DTrans(float(500+240*i),20.))) for i in range(8)]
    if Counter(found)!=Counter(expected):raise ValueError('Nine actual parent placements differ')
    for n,row in rec['ports'].items():
        b=pya.DBox(*row['rect_um']);metal=LAYERS[row['layer']]
        if not(pya.Region(b.to_itype(l.dbu))-pya.Region(top.begin_shapes_rec(l.layer(metal,0)))).is_empty():raise ValueError('Public port lacks conductive access')
        labels=[s.dtext.string for s in top.each_shape(l.layer(metal,25)) if s.is_text() and s.dtext.string==n and b.contains(s.dtext.trans.disp)]
        if labels!=[n]:raise ValueError('Actual named access missing/duplicated')
    text=(layout/(TOP+'.lef')).read_text();parts=text.split('  OBS\n')
    if len(parts)!=2:raise ValueError('Single OBS required')
    sections=re.findall(r'    LAYER (\w+) ;\n((?:      RECT [^\n]+\n)+)',parts[1])
    if [m for m,_ in sections]!=list(LAYERS):raise ValueError('Exact seven blockage layers required')
    for m,body in sections:
        actual=pya.Region()
        for line in body.splitlines():actual.insert(pya.DBox(*map(float,line.split()[1:5])).to_itype(l.dbu))
        expected=pya.Region(pya.DBox(0,0,WIDTH,HEIGHT).to_itype(l.dbu))
        for row in rec['ports'].values():
            if row['layer']==m:expected-=pya.Region(pya.DBox(*row['rect_um']).to_itype(l.dbu))
        if not(actual^expected).is_empty():raise ValueError('Exact obstruction union differs')
    db=pya.LayoutVsSchematic();db.read(str(dbpath));c=db.netlist().circuit_by_name(TOP)
    if {p.name() for p in c.each_pin()}!=set(PORTS):raise ValueError('Exact56native terminals required')
    rows=[]
    for d in c.each_device():
        cls=d.device_class();rows.append(dict(model=cls.name,nets={t.name:d.net_for_terminal(t.id()).name for t in cls.terminal_definitions()},parameters={p.name:d.parameter(p.name) for p in cls.parameter_definitions()}))
    checked=validate_device_rows(rows);checked['actual_driver_pairs']=list(checked['actual_driver_pairs'])
    result=dict(status='PASS_ACTUAL_SHARED_BODY_108_FINITE_TAPS_32_ESD_16_SERIAL_NINE_UNCHANGED_PARENTS_56_PORTS',device_rows=rows,checked=checked,placements=found,exact_seven_layer_obstructions=True,main_chip_integrated=False,esd_qualified=False,qualified_pex=False)
    out.write_text(json.dumps(result,indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--native-inspect",type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out, layout, pdk = args.out.resolve(), args.layout.resolve(), args.pdk.resolve()
    if args.native_inspect:
        return inspect_native(layout,args.native_inspect,out)
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-padded-clocked-")):
        parser.error("Fresh project or /dev/shm/nssoc-padded-clocked- directory required")
    generated = json.loads((layout / "result.json").read_text())
    if len(generated['serial_connections'])!=16 or set(generated['ports'])!=set(PORTS):
        raise ValueError('Complete wrapper graph required')
    app=root/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
    if digest(app)!=APP_SHA:raise ValueError('Native runtime changed')
    sources=[Path(p) for p in generated['input_sha256'] if Path(p).name=='schematic.cir' and digest(Path(p))==PARENTS['bank']['schematic']]
    if len(sources)!=1 or (layout/'schematic.cir').read_text()!=physical_reference(sources[0].read_text()):raise ValueError('New literal shared-body reference not reproduced')
    gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
    pins = {Path(k): v for k, v in generated["input_sha256"].items()}
    for name, expected in generated["output_sha256"].items():
        if digest(layout / name) != expected:
            raise ValueError("Generated physical view changed")
        pins[layout / name] = expected
    methods=['check_pcie_padded_clocked_bank.py','make_pcie_padded_clocked_bank.py','make_pcie_clocked_bank_v4.py','make_pcie_pad_boundary.py','make_pcie_sampler_cell.py','check_pcie_rx_cell.py','check_pcie_analog_bank.py','make_pcie_analog_bank.py','check_ihp_drc.py','prepare_ihp_drc.py','audit_klayout_lvs.py']
    for path in [app, layout / "result.json", pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
                 *(root / "hw/soc/flow" / name for name in methods)]:
        pins[path] = digest(path)
    for typ in ("drc", "lvs"):
        path = root / f"hw/soc/pnr/ihp-{typ}.lock.json"
        lock = json.loads(path.read_text())
        validate_lock(lock)
        if lock["commit"] != "5e6d592e4002946a4616f798c357f0f3c06cf3b6":
            raise ValueError("Native deck revision changed")
        pins[path] = digest(path)
        for row in lock["files"]:
            path = root / f"hw/soc/tools/ihp-{typ}-5e6d592" / row["path"]
            verify(path.read_bytes(), row)
            pins[path] = row["sha256"]
    if any(not p.is_file() or digest(p) != h for p, h in pins.items()):
        raise ValueError("Physical source changed before validation")
    out.mkdir(parents=True)
    record = dict(status="RUNNING", inputs={str(p): h for p, h in pins.items()}, steps=[],
                  phy_complete=False, qualified_pex=False, manufacturing_approval=False,
                  clock_fanout_qualified=False, post_layout_8ghz_qualified=False, main_chip_integrated=False,
                  esd_qualified=False, scope="Frozen padded clocked bank plus16 real bondpads/32ESD devices. Explicit shared ESD_RETURN substrate adds real paths; no unchanged body impedance, independent ground isolation, ESDstress/RF/PEX or main-chip acceptance.")

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    try:
        save()
        for name in ("drc", "offgrid", "lvs", "lvs_flat", *REFERENCE_FAULTS, *PHYSICAL_FAULTS):
            directory = out / name
            directory.mkdir()
            step = dict(name=name)
            record["steps"].append(step)
            save()
            physical, reference = gds, schematic
            if name == "offgrid" or name in PHYSICAL_FAULTS:
                physical = directory / "wrong.gds"
                script = directory / "mutate.py"
                script.write_text(mutation_source(gds, physical, generated, name))
                step["mutation_execution"] = execute([app, "python", script], directory, "mutation")
                if step["mutation_execution"]["returncode"] != 0 or digest(physical) == digest(gds):
                    raise ValueError("Physical fault did not bind")
            if name in REFERENCE_FAULTS:
                reference = directory / "wrong.cir"
                reference.write_text(fault_reference(schematic.read_text(), name))
            drc = name in ("drc", "offgrid")
            entry = root / ("hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc" if drc else
                            "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs")
            options = ["input=" + str(physical), "topcell=" + TOP, "log=" + str(directory / "deck.log"), "run_mode=flat" if name == "lvs_flat" else "run_mode=deep"]
            options += ["report=" + str(directory / "drc.lyrdb"), "threads=2", "no_recommended=False", "precheck_drc=False"] if drc else [
                "schematic=" + str(reference), "report=" + str(directory / "result.lvsdb"),
                "target_netlist=" + str(directory / "extracted.cir"), "thr=2"]
            command = [app, "klayout", "-b", "-zz", "-r", entry]
            for option in options:
                command += ["-rd", option]
            step["execution"] = execute(command, directory, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                measurement = record_result(directory, TOP, 0, pins)
                step["measurement"], step["status"] = measurement, measurement["status"]
                if measurement["category_count"] != 560 or "KLayout DRC run for tables 'main' completed" not in (directory / "run.log").read_text():
                    raise ValueError("Native main rule census incomplete")
                if name == "drc" and measurement["status"] != "PASS":
                    raise ValueError("Padded padded clocked bank main DRC failed")
                if name == "offgrid" and (measurement["status"] != "FAIL" or measurement["categories"].get("metal1_drw_Offgrid", 0) < 1):
                    raise ValueError("Physical DRC fault was accepted")
            else:
                step["audit_execution"] = execute([app, "python", root / "hw/soc/flow/audit_klayout_lvs.py",
                                                    directory / "result.lvsdb", "--top", TOP,
                                                    "--deck-log", directory / "deck.log", "--output", directory / "audit.json"], directory, "audit")
                step["audit"] = json.loads((directory / "audit.json").read_text())
                step["status"] = step["audit"]["status"]
                validate_lvs(step, (directory / "extracted.cir").read_text(), name in ("lvs", "lvs_flat"))
            save()
            print(name, step["status"], flush=True)
        for label in ('lvs','lvs_flat'):
            d=out/label
            ex=execute([app,'python',Path(__file__).resolve(),'--layout',layout,'--pdk',pdk,'--out',d/'native-geometry.json','--native-inspect',d/'result.lvsdb'],d,'geometry')
            if ex['returncode']!=0:raise ValueError('Native full device/port/geometry bridge failed')
            record.setdefault('native_geometry',{})[label]=dict(execution=ex,record=json.loads((d/'native-geometry.json').read_text()))
            save()
        for negative in (None, "missing_pin", "blocked_pin"):
            directory = out / ("lef_" + negative if negative else "lef")
            directory.mkdir()
            view = layout / (TOP + ".lef")
            if negative == "missing_pin":
                text, count = re.subn(r"  PIN VCTRL\n.*?  END VCTRL\n", "", view.read_text(), flags=re.S)
                if count != 1:
                    raise ValueError("LEF fault did not bind")
                view = directory / "wrong.lef"
                view.write_text(text)
            if negative == "blocked_pin":
                pin = generated["ports"]["VCTRL"]["rect_um"]
                obstruction = "      RECT " + " ".join(f"{value:.3f}" for value in pin) + " ;\n"
                text = view.read_text()
                if text.count("  OBS\n") != 1:
                    raise ValueError("LEF obstruction insertion did not bind")
                text = text.replace("  OBS\n", "  OBS\n    LAYER TopMetal1 ;\n" + obstruction, 1)
                view = directory / "wrong.lef"
                view.write_text(text)
            script = directory / "inspect.tcl"
            script.write_text(lef_script(pdk, view, generated))
            execution = execute([app, "openroad", "-exit", script], directory, "native")
            log = (directory / "native.log").read_text()
            if negative == "blocked_pin":
                if execution["returncode"] == 0 or "PASS_NATIVE_ANALOG_BANK_LEF_ONLY" in log or len(re.findall(r"^Error: inspect\.tcl, \d+ Padded padded clocked bank pin obstruction overlap$", log, re.M)) != 1:
                    raise ValueError("Blocked control-pin LEF negative failed incorrectly")
            else:
                validate_lef(execution["returncode"], log, bool(negative))
            record["steps"].append(dict(name=directory.name, execution=execution,
                                         status="EXPECTED_REJECTION" if negative else "PASS"))
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Physical inputs changed during native validation")
        record["status"] = "PASS_PADDED_CLOCKED_BANK_MAIN_DRC_DEEP_FLAT_LVS_AND_TWENTY_NINE_NEGATIVE_CONTROLS_ONLY"
        record["outputs"] = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*"))
                               if p.is_file() and p != out / "result.json"}
        save()
    except BaseException as error:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(error))
        save()
        raise


if __name__ == "__main__":
    main()
