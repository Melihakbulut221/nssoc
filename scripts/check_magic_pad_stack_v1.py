#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact native pad-stack conductor partition and real GDS fault controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys
import check_magic_hbt_multiplicity_v3 as h

FAULTS=('missing_via_m7','missing_via_m6','wire_open','wrong_layer','pair_short')


def validate_fixture(r):
    wanted={f'{prefix}{i:02d}' for prefix in ('PAD','CORE') for i in range(16)}
    if r.get('top')!='nssoc_pad_stack_fixture' or set(r.get('ports',{}))!=wanted or len(r.get('chains',[]))!=16:
        raise ValueError('Exact16-chain/32-port fixture required')
    for i,c in enumerate(r['chains']):
        if c!=dict(index=i,orientation=i%8,route_layer=134 if i<8 else 126,ports=[f'PAD{i:02d}',f'CORE{i:02d}']):
            raise ValueError('Route/orientation contract differs')
    for name,p in r['ports'].items():
        if p['layer']!=(134 if name.startswith('PAD') else 126) or len(p['box'])!=4:
            raise ValueError('Wrong physical terminal layer')


def expected_partition(case):
    groups=[{f'PAD{i:02d}',f'CORE{i:02d}'} for i in range(16)]
    if case in ('missing_via_m7','wire_open','wrong_layer','missing_via_m6'):
        i=8 if case=='missing_via_m6' else 0;groups.pop(i);groups += [{f'PAD{i:02d}'},{f'CORE{i:02d}'}]
    elif case=='pair_short':groups=[groups[0]|groups[1],*groups[2:]]
    elif case=='unfixed':groups=[{p} for g in groups for p in g]
    elif case!='nominal':raise ValueError('Unknown physical control')
    return sorted(sorted(g) for g in groups)


def assess(ext,log,record):
    validate_fixture(record)
    if log.count('NSSOC_PAD_STACK_COMPLETE')!=1 or re.search(
            r'(^|\n)(Error|ERROR)|Unrecognized|compatible substrate|Unknown command|No matching device',log):
        raise ValueError('Native process/technology failed')
    rows=[shlex.split(s) for s in ext.splitlines()]
    ports=[r[1] for r in rows if r and r[0]=='port']
    if len(ports)!=32 or set(ports)!=set(record['ports']):raise ValueError('Exact native32port inventory differs')
    if any(r and r[0]=='device' for r in rows):raise ValueError('Unexpected physical device in wire fixture')
    nodes=[r[1] for r in rows if r and r[0]=='node']
    if len(nodes)!=len(set(nodes)):raise ValueError('Duplicate native conductor')
    parent={n:n for n in nodes}
    def find(n):
        while parent[n]!=n:n=parent[n]
        return n
    for row in rows:
        if not row or row[0]!='equiv':continue
        if len(row)!=3:raise ValueError('Malformed raw native equivalence')
        a,b=row[1:];parent.setdefault(a,a);parent.setdefault(b,b)
        parent[find(b)]=find(a)
    if any(n not in parent for n in ports):raise ValueError('Physical port has no extracted node')
    groups={}
    for n in ports:groups.setdefault(find(n),[]).append(n)
    return dict(partition=sorted(sorted(v) for v in groups.values()),node_count=len(nodes),
                source='Only explicit native EXT node/equiv records; no reference-driven union')


def native_tcl(gds,record,out):
    validate_fixture(record)
    if any(x in str(gds)+str(out) for x in '{}\n\r'):raise ValueError('Unsafe native path')
    lines=['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"',f'cd {{{out}}}','drc off',
           f'gds read {{{gds}}}','load nssoc_pad_stack_fixture','flatten pad_stack_flat','load pad_stack_flat','select top cell']
    for i,(name,p) in enumerate(record['ports'].items(),1):
        lines+=['box values '+' '.join(str(x)+'um' for x in p['box']),
                f'label {name} center '+{126:'metal6',134:'metal7'}[p['layer']],
                f'port {name} make {i}',f'port {name} class inout',f'port {name} use signal']
    lines+=['save pad_stack_flat','extract style ngspice()','extract all','puts NSSOC_PAD_STACK_COMPLETE','quit -noprompt']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fixture','runtime','before-tech','after-tech','appimage','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'hw/soc/flow'))
    from check_pcie_rx_cell import execute
    record=json.loads((a.fixture/'result.json').read_text());validate_fixture(record)
    for path,sha in record['inputs'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha:raise ValueError('Fixture source changed')
    for name,sha in record['outputs'].items():
        if hashlib.sha256((a.fixture/name).read_bytes()).hexdigest()!=sha:raise ValueError('Fixture GDS changed')
    inputs=[Path(__file__),root/'scripts/audit_magic_pad_stack_geometry_v1.py',
            root/'scripts/check_magic_hbt_multiplicity_v3.py',root/'hw/soc/flow/check_pcie_rx_cell.py',
            a.runtime/'magic/tcl/tclmagic.so',a.fixture/'result.json',a.appimage,
            *a.before_tech.iterdir(),*a.after_tech.iterdir()]
    pins={str(x):h.pin(x) for x in inputs if x.is_file()};a.out.mkdir();cases={}
    for name in ('unfixed','nominal',*FAULTS):
        d=a.out/name;d.mkdir();gds=a.fixture/('fixture.gds' if name in ('unfixed','nominal') else name+'.gds')
        script=d/'native.tcl';script.write_text(native_tcl(gds,record,d));rt=a.runtime
        tech=a.before_tech if name=='unfixed' else a.after_tech
        x=execute(['/usr/bin/env','CAD_ROOT='+str(rt),'/usr/bin/tclsh8.6',rt/'magic/tcl/magic.tcl',
                   '-dnull','-noconsole','-rcfile',tech/'ihp-sg13g2.magicrc',script],d,'native')
        if x['returncode']!=0:raise ValueError('Native error is not a physical negative')
        y=assess((d/'pad_stack_flat.ext').read_text(),(d/'native.log').read_text(),record)
        if y['partition']!=expected_partition(name):raise ValueError('Observed native physical control differs')
        z=execute([a.appimage,'python',root/'scripts/audit_magic_pad_stack_geometry_v1.py','--gds',gds,
                   '--fixture',a.fixture/'result.json','--out',d/'geometry.json'],d,'geometry')
        if z['returncode']!=0:raise ValueError('Independent native geometry audit failed')
        ref=json.loads((d/'geometry.json').read_text())
        if ref['partition']!=expected_partition('nominal' if name=='unfixed' else name):
            raise ValueError('Independent native conductor partition differs')
        if name=='nominal' and (ref['node_count']!=16 or y['node_count']!=16):
            raise ValueError('Unexpected unprobed conductor')
        cases[name]=dict(execution=x,geometry_execution=z,native=y,reference=ref,
                        status='PRESERVED_NATIVE_IMPORT_FAILURE' if name=='unfixed' else 'PASS_EXACT_PHYSICAL_CONTROL',
                        outputs={x.name:h.pin(x) for x in d.iterdir() if x.is_file()})
    if any(h.pin(Path(x))!=v for x,v in pins.items()) or any(
            hashlib.sha256(Path(x).read_bytes()).hexdigest()!=v for x,v in record['inputs'].items()):
        raise ValueError('Source/runtime changed during native controls')
    (a.out/'result.json').write_text(json.dumps(dict(status='PASS_NATIVE_PAD_STACK_IMPORT_REPAIR',cases=cases,inputs=pins,
        qualified_pex=False,full_bank_qualified=False,esd_stress_qualified=False),indent=2)+'\n')


if __name__=='__main__':main()
