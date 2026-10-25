#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native six-pin LEF from the exact full-driver physical proof, not timing."""
import argparse,json,math,os,re,sys
from pathlib import Path
import cloud_tx_input_driver_shortspines as physical
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-shortspines-lef';TOP=physical.TOP;PORTS=physical.PORTS
SOURCE={'run': 38917470904, 'group': 'tx-input-driver-shortspines', 'root': 'cloud-tx-input-driver-shortspines', 'bytes': 1288683, 'sha': '3108c6338771efddbcf988f1fcd4b25dcbf05ff9d60b2541037f24e59fee7cea', 'summary': '23262f695f5156a39842ad6458e0b9808d052a10723f77d4d7c95de312ddd500'}

def direction(name):
    if name in ('avdd','dvdd'):return 'POWER','INOUT'
    if name in ('avss','sub'):return 'GROUND','INOUT'
    return 'SIGNAL','INPUT' if name=='din' else 'OUTPUT'

def generate():
    import pya
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_pump_filter13_v1 as producer
    source=OUT/'inputs/tx-input-driver-shortspines/cloud-tx-input-driver-shortspines'
    report=json.loads((source/'result.json').read_text());geometry=report['geometry'];gds=source/'base/layout.gds'
    assert sha(gds)==report['outputs']['base/layout.gds']
    layout=pya.Layout();layout.read(str(gds));top=layout.cell(TOP);assert top is not None
    labels=[s.dtext for s in top.each_shape(layout.layer(67,25)) if s.is_text()]
    pins=[s.dbbox() for s in top.each_shape(layout.layer(67,2)) if s.is_box()]
    assert len(labels)==len(pins)==6 and {s.string for s in labels}==set(PORTS)
    ports={}
    for label in labels:
        matches=[p for p in pins if p.contains(label.trans.disp)]
        assert len(matches)==1
        box=matches[0];expected=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',geometry['ports'][label.string])))
        actual=[box.left,box.bottom,box.right,box.top]
        assert len(expected)==4 and all(abs(a-b)<1e-9 for a,b in zip(actual,expected))
        ports[label.string]=('Metal5',box)
    assert len({str(p) for layer,p in ports.values()})==6
    bbox=top.dbbox();assert bbox.left>=0 and bbox.bottom>=0
    outline=pya.DBox(0.,0.,math.ceil(bbox.right/.005)*.005,math.ceil(bbox.top/.005)*.005)
    producer.TOP=TOP;producer.PORTS=PORTS;producer.use_direction=direction
    out=OUT/'layout';out.mkdir()
    lef=out/(TOP+'.lef');lef.write_text(producer.lef(pya,layout.dbu,outline,ports))
    record=dict(status='GENERATED_FULL_DRIVER_LEF_NOT_NATIVE_VALIDATION',source_run=SOURCE['run'],gds_sha256=sha(gds),
        actual_gds_bbox_um=str(bbox),bbox_um=str(outline),ports={n:str(b) for n,(layer,b) in ports.items()},
        outputs={lef.name:sha(lef)},mainchip_integrated=False,qualified_timing=False)
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')

def tcl(pdk,lef,generated):
    def quote(p):
        s=str(p);assert not any(c in s for c in '{}\n\r');return '{'+s+'}'
    def coords(s):return [round(float(x)*1000) for x in re.findall(r'-?\d+(?:\.\d+)?',s)]
    box=coords(generated['bbox_um']);assert len(box)==4 and box[:2]==[0,0]
    lines=['read_lef '+quote(pdk/'libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef'),'read_lef '+quote(lef),
        'set master [[ord::get_db] findMaster '+TOP+']','if {$master eq "NULL"} {error "Driver master missing"}',
        f'if {{[$master getWidth] != {box[2]} || [$master getHeight] != {box[3]}}} {{error "Driver outline changed"}}',
        'if {[llength [$master getMTerms]] != 6} {error "Driver terminal census changed"}']
    for name in PORTS:
        x1,y1,x2,y2=coords(generated['ports'][name]);use,io=direction(name)
        lines += ['set term [$master findMTerm '+name+']','if {$term eq "NULL"} {error "Driver terminal missing"}',
            f'if {{[$term getIoType] ne "{io}" || [$term getSigType] ne "{use}"}} {{error "Driver pin type changed"}}',
            'set boxes {}; foreach pin [$term getMPins] {foreach b [$pin getGeometry] {lappend boxes [list [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]]}}',
            'if {$boxes ne {{Metal5 %d %d %d %d}}} {error "Driver pin geometry changed"}'%(x1,y1,x2,y2),
            f'foreach b [$master getObstructions] {{if {{[[$b getTechLayer] getName] eq "Metal5" && [$b xMin] < {x2} && [$b xMax] > {x1} && [$b yMin] < {y2} && [$b yMax] > {y1}}} {{error "Driver pin is obstructed"}}}}']
    lines += ['set layers {}; foreach b [$master getObstructions] {lappend layers [[$b getTechLayer] getName]}',
        'if {[lsort -unique $layers] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Driver obstruction layer census changed"}',
        'puts PASS_NATIVE_FULL_DRIVER_SIX_PIN_LEF']
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args=parser.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,steps={},mainchip_integrated=False,qualified_pex=False,qualified_timing=False,serial_phy_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert all(v['expected_verdict_observed'] for v in prior['steps'].values() if 'expected_verdict_observed' in v)
        assert prior['steps']['drc']['measurement']['markers']==0 and prior['steps']['drc']['measurement']['category_count']==560
        from run_cloud_pll_filter_lef import restore_technology
        technology=restore_technology();app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        r['generation']=execute([app,'python',Path(__file__).resolve(),'--generate'],OUT,'generate');save()
        if r['generation']['returncode']:
            print((OUT/'generate.log').read_text(errors='replace')[-12000:]);raise RuntimeError('Native LEF generation failed')
        generated=json.loads((OUT/'layout/result.json').read_text());r['layout']=generated;save();lef=OUT/'layout'/(TOP+'.lef');pins={str(technology):sha(technology),str(lef):sha(lef),str(source/'base/layout.gds'):sha(source/'base/layout.gds')}
        for name in ('positive','missing_pin','blocked_pin'):
            d=OUT/name;d.mkdir();selected=lef
            if name!='positive':
                text=lef.read_text()
                if name=='missing_pin':text,count=re.subn(r'  PIN din\n.*?  END din\n','',text,flags=re.S);assert count==1
                else:
                    values=re.findall(r'-?\d+(?:\.\d+)?',generated['ports']['din']);assert len(values)==4 and text.count('  OBS\n')==1
                    text=text.replace('  OBS\n','  OBS\n    LAYER Metal5 ;\n      RECT '+' '.join(values)+' ;\n')
                selected=d/'fault.lef';selected.write_text(text)
            script=d/'inspect.tcl';script.write_text(tcl(ROOT/'pdk',selected,generated))
            run=execute([app,'openroad','-exit',script],d,'run');text=(d/'run.log').read_text();banner='PASS_NATIVE_FULL_DRIVER_SIX_PIN_LEF'
            if name=='positive':passed=run['returncode']==0 and text.count(banner)==1 and not re.search(r'^Error:|\[ERROR',text,re.M)
            else:
                reason='Driver terminal census changed' if name=='missing_pin' else 'Driver pin is obstructed'
                passed=run['returncode']!=0 and banner not in text and len(re.findall(r'^Error: inspect\.tcl, \d+ '+reason+'$',text,re.M))==1
            r['steps'][name]=dict(execution=run,passed=bool(passed));save();assert passed,('Native LEF check',name)
        assert all(sha(Path(p))==v for p,v in pins.items()) and all(sha(source/p)==v for p,v in prior['outputs'].items())
        r['status']='PASS_FULL_DRIVER_NATIVE_SIX_PIN_LEF_AND_TWO_FAULTS_NOT_ELECTRICAL_OR_MAINCHIP_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
