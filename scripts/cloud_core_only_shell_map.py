#!/usr/bin/env python3
"""Map real chip-shell logic; keep core/pads as explicit physical boundaries.

Cloud-only synthesis and native gate simulation. Core stub is simulation-only;
no complete-chip routing, timing, CDC, LVS or manufacturing pass is claimed.
"""
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from cloud_core_only_postgrt import restore_mapping
ROOT=Path.cwd().resolve()
OUT=ROOT/'hw/soc/out/core-only-shell-map'
REV='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fetch(relative,digest):
    api='repos/IHP-GmbH/IHP-Open-PDK/'
    row=json.loads(subprocess.check_output(['gh','api',api+'contents/ihp-sg13g2/'+relative+'?ref='+REV]))
    if row.get('encoding')!='base64':
        row=json.loads(subprocess.check_output(['gh','api',api+'git/blobs/'+row['sha']]))
    data=base64.b64decode(row['content']);assert hashlib.sha256(data).hexdigest()==digest
    path=OUT/Path(relative).name;path.write_bytes(data);return path

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,
           actual_core_boot=False,physical_timing_complete=False,full_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        mapping,artifacts=restore_mapping()
        r['mapping_artifacts']=artifacts
        core_json=ROOT/'hw/soc/out/core-only-mainchip/synthesis/soc_top.mapped.json'
        generated=OUT/'generated'
        subprocess.run([sys.executable,'scripts/generate_chip_io.py','--profile','core-only',
                        '--core-json',str(core_json),'--output',str(generated)],check=True)
        contract=json.loads((ROOT/'hw/soc/core-only-chip-io-contract.json').read_text())
        ports=contract['core_ports']
        declarations=[]
        for name,p in ports.items():
            bus='' if p['width']==1 else f"[{p['width']-1}:0] "
            declarations.append(f"{p['direction']} wire {bus}{name}")
        boundary=OUT/'core_blackbox.v'
        boundary.write_text('(* blackbox *) module soc_top('+','.join(declarations)+'); endmodule\n')
        # The boundary has no behavioral substitute; it remains one soc_top cell.
        io=fetch('libs.ref/sg13g2_io/verilog/sg13g2_io.v',
                 '0195945188ec15560ad2cc9c000e3ff70255d65da717099b87b6b726a6e53429')
        lib=fetch('libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib',
                  '968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4')
        model=fetch('libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v',
                    '28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4')
        rtl=ROOT/'hw/soc/rtl/chip/soc_status_serial.v'
        netlist=OUT/'nssoc_chip.mapped.v';mapped=OUT/'nssoc_chip.mapped.json'
        recipe=OUT/'map.ys'
        recipe.write_text(f"""read_liberty -lib {lib}
read_verilog -lib {io}
read_verilog -lib {boundary}
read_verilog {rtl} {generated/'nssoc_chip.v'}
hierarchy -check -top nssoc_chip
synth -top nssoc_chip -flatten
dfflibmap -liberty {lib}
abc -liberty {lib}
clean
write_json {OUT/'with-scopeinfo.json'}
delete t:$scopeinfo
check -assert
write_verilog -noattr {netlist}
write_json {mapped}
stat -liberty {lib}
""")
        protected={str(p):sha(p) for p in [Path(__file__),core_json,boundary,io,lib,model,rtl,
            recipe,generated/'nssoc_chip.v',ROOT/'scripts/generate_chip_io.py',
            ROOT/'scripts/qualify_core_only_native_io.py',ROOT/'hw/soc/core-only-chip-io-contract.json']}
        r['protected_inputs']=protected
        version=subprocess.check_output(['yosys','-V'],text=True);r['yosys_version']=version.strip()
        r['status']='MAPPING_SHELL';save()
        with (OUT/'mapping.log').open('w') as log:
            subprocess.run(['yosys','-s',str(recipe)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        module=json.loads(mapped.read_text())['modules']['nssoc_chip']
        before_scope=json.loads((OUT/'with-scopeinfo.json').read_text())['modules']['nssoc_chip']
        metadata={n:c for n,c in before_scope['cells'].items() if c['type']=='$scopeinfo'}
        assert len(metadata)==1 and all(not c['connections'] for c in metadata.values())
        assert module['cells']=={n:c for n,c in before_scope['cells'].items() if n not in metadata}
        assert module['ports']==before_scope['ports'] and module['netnames']==before_scope['netnames']
        r['metadata_removal']=dict(type='$scopeinfo',removed=len(metadata),all_cells_and_connections_unchanged=True)
        cells=module['cells'];counts=Counter(c['type'] for c in cells.values())
        assert counts['soc_top']==1 and cells['u_core']['type']=='soc_top'
        assert set(cells['u_core']['connections'])==set(ports)
        assert all(len(cells['u_core']['connections'][n])==p['width'] for n,p in ports.items())
        pads=json.loads((generated/'pads.json').read_text())
        assert len(pads)==80
        for pad in pads:assert cells[pad['instance']]['type']==pad['master']
        expected=Counter(p['master'] for p in pads)
        assert all(counts[k]==v for k,v in expected.items())
        assert all(c['type']=='soc_top' or c['type'].startswith('sg13g2_') for c in cells.values())
        assert any(k.startswith('sg13g2_df') for k in counts),'Missing mapped mailbox flops'
        r['mapped_cells']=dict(counts);r['mapped_netlist_sha256']=sha(netlist)
        # Reuse the already qualified native-pad fixture, including its negative control.
        subprocess.run([sys.executable,'scripts/qualify_core_only_native_io.py'],check=True)
        fixture=ROOT/'hw/soc/out/core-only-native-io'
        original=json.loads((fixture/'result.json').read_text())
        assert original['status']=='PASS_NATIVE_FUNCTIONAL_PADS_WITH_CORE_STUB_NOT_SIGNOFF'
        assert sha(fixture/'chip.v')==sha(generated/'nssoc_chip.v')
        r['fixture_result']=original
        cases={}
        for label,pad_model in [('native','native_io.v'),('negative_enable','negative_enable_io.v')]:
            binary=OUT/(label+'.vvp')
            cmd=['iverilog','-g2012','-DFUNCTIONAL','-s','tb','-o',str(binary),str(netlist),
                 str(fixture/'core_stub.v'),str(fixture/pad_model),str(model),str(fixture/'tb.v')]
            with (OUT/(label+'-compile.log')).open('w') as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
            result=subprocess.run(['vvp',str(binary)],capture_output=True,text=True,timeout=120)
            log=result.stdout+result.stderr;(OUT/(label+'-run.log')).write_text(log)
            cases[label]=dict(returncode=result.returncode)
            if label=='native':
                assert result.returncode==0 and 'NATIVE_PAD_FUNCTIONAL_PASS' in log,log
                frames=[line for line in log.splitlines() if line.startswith('FRAME ')]
                baseline=[line for line in (fixture/'native-run.log').read_text().splitlines() if line.startswith('FRAME ')]
                assert len(frames)==1 and frames==baseline
                cases[label]['frame']=frames[0]
            else:
                assert result.returncode!=0 and 'Native pad input/release failed' in log,log
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='MAPPED_SHELL_NATIVE_SIMULATION_PASS_REQUIRES_CORE_AND_PHYSICAL_INTEGRATION',
                 sources_unchanged=True,cases=cases,core_boundary='explicit soc_top blackbox in synthesis; behavioral stub only in simulation',
                 scope='Mapped real status mailbox and native pad instances. Functional zero-delay only; no routed core attached, no SDF/CDC timing, padframe route, LVS or ESD acceptance.')
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*')
                      if p.is_file() and p!=OUT/'result.json' and p.suffix!='.vvp'};save()
if __name__=='__main__':main()
