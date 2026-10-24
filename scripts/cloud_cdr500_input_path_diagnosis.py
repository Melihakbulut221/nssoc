#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Existing cleaned input R graph and native geometry diagnosis, no simulation."""
import copy,json,os,shlex,subprocess,sys,traceback
from collections import Counter
from decimal import Decimal
from pathlib import Path
import numpy as np
import analyze_cdr_wire_resistance as solver
import build_pcie_local_vco_hybrid_v6 as parser
import compare_cloud_routed_endpoints as reports
from cloud_cdr500_loaded_rejection_readback import publish
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
GROUP='cdr500-input-path-diagnosis'
OUT=ROOT/('cloud-'+GROUP)
INPUTS=ROOT/('cloud-inputs-'+GROUP)

def check():
    pin=json.loads((ROOT/'scripts/cdr500-input-path-diagnosis-methods.json').read_text())
    for p,d in pin['protected'].items():assert sha(ROOT/p)==d,p

def edge_gate(exported,raw):
    def norm(a,b,v):return tuple(sorted((a,b)))+(Decimal(v).normalize(),)
    assert Counter(norm(a,b,str(v))for _,a,b,v in exported)==Counter(norm(a,b,v)for a,b,v in raw),'Full native R edge/value multiset differs'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1';check();OUT.mkdir(exist_ok=False);INPUTS.mkdir(exist_ok=False);reports.OUT=INPUTS
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_simulation_started=False,geometry_modified=False,original_waveform_rejections_preserved=True,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr500-cleaned-mim-precision-pass-20261024.json').read_text());selected=['composition/pd500-mim-wire.spice','composition/composition.json','precise/wire/anchors08.json','precise/wire/rc03/wires.spice','precise/wire/rc03/pump_wires.res.ext','precise/wire/rc03/pump_wires.ext','precise/wire/rc03/pump_wires.mag']
        prior,proof=reports.restore_report('cdr500-cleaned-mim-precision',pin['run'],pin['summary_sha256'],pin['parts_sha256'],INPUTS/'precision',selected);assert prior==pin['report']and prior['sources_unchanged']and prior['native_rc_and_device_records_equal_in_both_orders'];r['precision_source']=proof
        ppin=json.loads((ROOT/'docs/evidence/cdr500-floating-wire-cleanup-pass-20261024.json').read_text());ps=['parent/layout/nssoc_cdr_pd500_active_input_v57.gds','parent/layout/result.json','parent/physical/lvs_flat/result.lvsdb','wire/native05/wires.gds','wire/native05/wires.l2n','wire/native05/result.json']
        physical,pproof=reports.restore_report('cdr500-floating-wire-cleanup',ppin['run'],ppin['summary_sha256'],ppin['parts_sha256'],INPUTS/'physical',ps);assert physical==ppin['report']and physical['sources_unchanged'];r['physical_source']=pproof
        precision=INPUTS/'precision';contract=json.loads((precision/'composition/composition.json').read_text());assert contract==prior['composition']['contract']and contract['counts']==dict(devices=500,R=24550,C=15678)
        anchors=json.loads((precision/'precise/wire/anchors08.json').read_text());points={a['label']:a for a in anchors['anchors']};assert len(points)==978
        exported=[]
        for row in parser.statements((precision/'precise/wire/rc03/wires.spice').read_text()):
            if row[0].startswith('R'):assert len(row)==4;exported.append((row[0],row[1],row[2],str(parser.number(row[3]))))
        assert len(exported)==24550
        raw=[];coords={};raw_records={}
        for line in(precision/'precise/wire/rc03/pump_wires.res.ext').read_text().splitlines():
            row=shlex.split(line)
            if not row:continue
            if row[0]=='resist':assert len(row)==4;raw.append((row[1],row[2],row[3]))
            elif row[0]=='rnode':assert len(row)==7 and row[1]not in coords;coords[row[1]]=[int(row[4]),int(row[5])];raw_records[row[1]]=row
        edge_gate(exported,raw);bad=list(exported);name,a,b,value=bad[0];bad[0]=(name,a,b,str(Decimal(value)*Decimal('1.01')))
        try:edge_gate(bad,raw)
        except AssertionError:r['changed_native_resistor_rejected']=True
        else:raise AssertionError('Changed native resistor accepted')
        ports={}
        for line in(precision/'precise/wire/rc03/pump_wires.ext').read_text().splitlines():
            row=shlex.split(line)
            if row and row[0]=='port':assert row[1]not in ports;ports[row[1]]=[int(row[3]),int(row[4])]
        assert set(ports)==set(points)
        def coordinate_gate(ps):
            assert set(ps)==set(points)
            deltas=[tuple(5*x-y for x,y in zip(ps[name],points[name]['point_dbu'],strict=True))for name in ps]
            assert set(deltas)<={(0,0),(0,-2)},Counter(deltas)
            assert Counter(deltas)==Counter({(0,0):846,(0,-2):132}),Counter(deltas)
            return {str(k):v for k,v in Counter(deltas).items()}
        r['native_anchor_grid_deltas_dbu']=coordinate_gate(ports);bad=copy.deepcopy(ports);name=next(iter(bad));bad[name][0]+=10
        try:coordinate_gate(bad)
        except AssertionError:r['shifted_native_anchor_rejected']=True
        else:raise AssertionError('Shifted raw coordinate accepted')
        mapped=[(tuple(sorted((contract['wire_node_map'][a],contract['wire_node_map'][b]))),Decimal(v).normalize())for _,a,b,v in exported]
        actual=[]
        for row in parser.statements((precision/'composition/pd500-mim-wire.spice').read_text()):
            if row[0].startswith('R'):actual.append((tuple(sorted(row[1:3])),parser.number(row[3]).normalize()))
        assert Counter(mapped)==Counter(actual),'Composed resistor graph differs from full audited raw graph'
        r['all24550_raw_and_composed_resistor_edges_verified']=True;r['linear_solver_controls']=solver.controls()
        devices={d['native_id']:d for d in contract['device_records']};groups=[];evaluations=[];float_edges=[(n,a,b,float(v))for n,a,b,v in exported]
        readback=json.loads((ROOT/'docs/evidence/cdr500-loaded-rejection-readback-pass-20261024.json').read_text());assert readback['run']==40084668388
        def terminal(d,name):return next(t for t in d['terminals']if t['terminal']==name)
        def owns(d,name,t):return any(a['terminal']==name and(a['native_cluster'],a['native_net'])==(t['native_cluster'],t['native_net'])for a in d['terminals'])
        for did in [59,60,111,112]:
            gain=devices[did];gb=terminal(gain,'B');drivers=[d for d in devices.values()if d['model']=='npn13g2'and owns(d,'E',gb)];loads=[d for d in devices.values()if d['model']=='rppd'and any((t['native_cluster'],t['native_net'])==(gb['native_cluster'],gb['native_net'])for t in d['terminals'])]
            assert len(drivers)==len(loads)==1;driver=drivers[0];termination=loads[0];lt=next(t for t in termination['terminals']if(t['native_cluster'],t['native_net'])==(gb['native_cluster'],gb['native_net']));assert any(t['native_net']=='avss'for t in termination['terminals'])
            roles={'driver':terminal(driver,'E'),'gain':gb,'termination':lt};bound={role:points[t['anchor']]for role,t in roles.items()};assert len({a['wire_component']for a in bound.values()})==1 and len({a['native_cluster']for a in bound.values()})==1
            proof=dict(gain_native_id=did,gain=gain,driver=driver,termination=termination,role_terminals=roles)
            dominant={}
            for first,last in [('driver','gain'),('driver','termination'),('gain','termination')]:
                sol=solver.solve(float_edges,roles[first]['anchor'],roles[last]['anchor']);evaluation=dict(gain_native_id=did,roles=[first,last],solution=sol);evaluations.append(evaluation)
                for edge in sol['dominant_edges']:
                    original=next(e for e in exported if e[0]==edge['resistor']);assert edge['from_node']==original[1]and edge['to_node']==original[2]and edge['resistance_ohm']==float(original[3])
                    enriched=dict(edge,raw_endpoints=[dict(name=node,raw_record=raw_records[node],point_dbu=[5*x for x in coords[node]])for node in [edge['from_node'],edge['to_node']]])
                    dominant[edge['resistor']]=enriched
            groups.append(dict(role_binding=proof,anchors=bound,dominant_edges=list(dominant.values()),existing_peak_waveform_evidence={case:x['report']['diagnosis']['hbt_stress']['xpd.xd'+str(did).zfill(4)]for case,x in readback['cases'].items()}))
        assert len(groups)==4 and len(evaluations)==12;r['linear_wire_evaluations']=evaluations
        (INPUTS/'request.json').write_text(json.dumps(dict(groups=groups),indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with(OUT/'native-geometry.log').open('w')as log:code=subprocess.call([str(app),'python',str(ROOT/'scripts/cdr500_input_path_geometry.py'),str(INPUTS)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'native-geometry.log').read_text()[-18000:],flush=True)
        assert code==0,('Native geometry readback failed',code)
        native=json.loads((INPUTS/'native-geometry.json').read_text());assert native['selected_native_and_wire_owners_verified']and native['original_geometry_unchanged']and len(native['groups'])==4;r['native_geometry']=native
        r['source_path_request']=groups;r['raw_component_scope']='Only original metal resistors in source-bound native connected components. All intrinsic devices and capacitors excluded from unit-current DC solve; they remain unchanged in authoritative circuit model. No bias edit, artificial R scaling, or circuit simulation.'
        assert all(sha(precision/p)==prior['outputs'][p]for p in selected)and all(sha(INPUTS/'physical'/p)==physical['outputs'][p]for p in ps);check()
        r.update(status='PASS_EXISTING_CDR_INPUT_R_GRAPH_AND_NATIVE_OWNED_PATH_DIAGNOSIS_NOT_CIRCUIT_ACCEPTANCE',sources_unchanged=True,scope='Effective DC wire R and R*i^2 sensitivities, native endpoint coordinate/paint ownership and actual polygon/via paths. Reduced resistor edges are not asserted to be straight or assigned a unique material. Transient C/current sharing still matters; original failed gates remain.')
    except BaseException as error:r.update(status='FAIL_INPUT_PATH_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
    finally:save();publish(OUT,GROUP);print(r['status'],flush=True)
if __name__=='__main__':main()
