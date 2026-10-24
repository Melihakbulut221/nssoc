#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Locate actual PD484 power-grid resistance and native coordinates, without resimulation."""
import json,os,shlex
from collections import Counter
from pathlib import Path
import numpy as np
import networkx as nx
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-parallel-v3-power-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,simulation_rerun=False,scope='Unchanged full-parent source-bound DC unit-current resistance and native coordinate diagnosis. Measured rail losses come from the original failed waveform. DC analysis does not estimate actual current, replace distributed R/C, or establish transient acceptance.')
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-parallel-v3-mim-composition-pass-20261018.json').read_text());selected=['pd484-mim-wire.spice','composition.json']
        prior,proof=reports.restore_report('cdr-parallel-v3-mim-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'model',selected)
        assert prior==pin['report']and prior['sources_unchanged'];r['composition_source']=proof
        cap=json.loads((ROOT/'docs/evidence/cdr-parallel-v3-mim-parent-capture-pass-20261018.json').read_text());rawfiles=['wire/rc03/pump_wires.ext','wire/rc03/pump_wires.res.ext']
        capture,cproof=reports.restore_report('cdr-parallel-v3-mim-parent-rc',cap['run'],cap['summary_sha256'],cap['parts_sha256'],OUT/'native',rawfiles)
        assert capture==cap['report']and capture['sources_unchanged'];r['raw_source']=cproof
        wave=json.loads((ROOT/'docs/evidence/cdr-parallel-v3-native-path-review-20261018.json').read_text())['cases']['nominal_early']
        observed=wave['report_excerpt'];assert observed['status'].startswith('COMPLETE_NATIVE_CDR')
        r['measured_source']=dict(run=wave['run'],summary_sha256=wave['summary_sha256'],parts_sha256=wave['parts_sha256'])
        contract=json.loads((OUT/'model/composition.json').read_text());assert contract==prior['composition']and contract['counts']==dict(devices=484,R=3538,C=4038)
        rows=parser.statements((OUT/'model/pd484-mim-wire.spice').read_text());assert Counter(x[0][0].upper()for x in rows[1:-1])==dict(X=484,R=3538,C=4038)
        inverse={v.lower():k for k,v in contract['wire_node_map'].items()};assert len(inverse)==len(contract['wire_node_map'])
        bydevice={d['instance'].lower():d for d in contract['device_records']};graph=nx.Graph();resistors=[]
        for row in rows[1:-1]:
            if row[0][0]!='R':continue
            assert len(row)==4;name,a,b,value=row;a=a.lower();b=b.lower();ohm=float(parser.number(value));assert np.isfinite(ohm)and ohm>0 and a!=b
            resistors.append((name,a,b,ohm));graph.add_edge(a,b)
        assert len(resistors)==3538
        r['rails']={};needed=set()
        for rail in ('avdd','avss'):
            component=nx.node_connected_component(graph,rail);assert not(set(('avdd','avss','wire_cref'))-{rail})&component
            nodes=sorted(component-{rail});index={n:i for i,n in enumerate(nodes)};edges=[e for e in resistors if e[1]in component];assert all(e[2]in component for e in edges)
            ii=[];jj=[];vv=[]
            for _,a,b,ohm in edges:
                conductance=1/ohm
                for n in (a,b):
                    if n!=rail:ii.append(index[n]);jj.append(index[n]);vv.append(conductance)
                if a!=rail and b!=rail:ii.extend([index[a],index[b]]);jj.extend([index[b],index[a]]);vv.extend([-conductance,-conductance])
            matrix=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc();factor=splu(matrix)
            targets=sorted([x for x in observed['supply_terminal_review']if x['rail']==rail],key=lambda x:x['voltage_from_external']['rms_v'],reverse=True)[:20]
            assert targets;results=[];solutions=[]
            for target in targets:
                dev=bydevice[target['device']];term=next(z for z in dev['terminals']if z['terminal']==target['terminal']);point=term['node'].lower()
                assert term['native_net']==rail and term['anchor']is not None and point==target['node']and point in component
                current=np.zeros(len(nodes));current[index[point]]=1;volts=factor.solve(current);assert np.isfinite(volts).all()
                residual=float(np.max(np.abs(matrix@volts-current)));assert residual<1e-7
                effective=float(volts[index[point]]);assert effective>0
                def v(n):return 0. if n==rail else float(volts[index[n]])
                loss=[]
                for name,a,b,ohm in edges:
                    drop=v(a)-v(b);loss.append(dict(name=name,nodes=[a,b],raw_nodes=[inverse[a],inverse[b]],resistance_ohm=ohm,unit_current_a=drop/ohm,unit_current_loss_w=drop*drop/ohm))
                energy=sum(x['unit_current_loss_w']for x in loss);assert abs(energy-effective)<1e-7*max(1,effective)
                top=sorted(loss,key=lambda x:x['unit_current_loss_w'],reverse=True)[:15];needed.update(n for e in top for n in e['raw_nodes'])
                results.append(dict(native_id=dev['native_id'],instance=dev['instance'],model=dev['model'],terminal=target['terminal'],wire_point=point,actual_wave_voltage=target['voltage'],actual_wave_difference_from_external=target['voltage_from_external'],effective_resistance_ohm=effective,kcl_residual_a=residual,unit_current_total_loss_w=energy,top15_loss_branches=top));solutions.append((point,volts.copy()))
            a,va=solutions[0];b,vb=solutions[-1];ab=float(va[index[b]]);ba=float(vb[index[a]]);assert abs(ab-ba)<1e-8*max(1,abs(ab))
            r['rails'][rail]=dict(nodes=len(component),resistors=len(edges),targets=results,reciprocity=dict(forward_ohm=ab,reverse_ohm=ba))
        records={};headers={}
        for name in rawfiles:
            lines=(OUT/'native'/name).read_text().splitlines();headers[name]=lines[:8]
            for line in lines:
                fields=shlex.split(line)
                if len(fields)>1 and fields[0]in ('node','rnode','port')and fields[1]in needed:records.setdefault(fields[1],[]).append(dict(file=name,raw=line,fields=fields))
        assert set(records)==needed,dict(missing=sorted(needed-set(records)))
        r['native_coordinate_records']=records;r['native_headers']=headers
        assert all(sha(OUT/'model'/n)==prior['outputs'][n]for n in selected)and all(sha(OUT/'native'/n)==capture['outputs'][n]for n in rawfiles)
        r.update(status='COMPLETE_PD484_NATIVE_POWER_RESISTANCE_COORDINATES_NOT_TRANSIENT_ACCEPTANCE',sources_unchanged=True)
        print(json.dumps(dict(status=r['status'],rails={k:dict(nodes=v['nodes'],R=v['resistors'],worst=v['targets'][0])for k,v in r['rails'].items()}),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
