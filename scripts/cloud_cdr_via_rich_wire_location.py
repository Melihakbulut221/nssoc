#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Map proven CDR wire bottlenecks to original native raw-node/anchor evidence."""
import json,os,re,shlex
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-via-rich-wire-location'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False)
    try:
        p=json.loads((ROOT/'docs/evidence/cdr-via-rich-wire-comparison-pass-20261019.json').read_text())
        diagnosis,dproof=reports.restore_report('cdr-via-rich-wire-comparison',p['run'],p['summary_sha256'],p['parts_sha256'],OUT/'diagnosis',['via-rich-v7/pd484-mim-wire.spice'])
        assert diagnosis==p['report']and diagnosis['sources_unchanged']
        assert len(diagnosis['evaluations'])==64 and not diagnosis['electrical_waveform_acceptance']
        cap=json.loads((ROOT/'docs/evidence/cdr-via-rich-v7-mim-parent-capture-pass-20261018.json').read_text())
        selected=['wire/rc03/pump_wires.ext','wire/rc03/pump_wires.res.ext','wire/rc03/wires.spice','wire/anchors08.json','ngspice-mim-tech/ihp-sg13g2-extract.tech','source/wire/native05/result.json']
        capture,cproof=reports.restore_report('cdr-via-rich-v7-mim-parent-rc',cap['run'],cap['summary_sha256'],cap['parts_sha256'],OUT/'capture',selected)
        assert capture==cap['report']and capture['sources_unchanged']
        r['sources']=dict(diagnosis=dproof,capture=cproof)
        wanted={}
        for ev in diagnosis['evaluations']:
            for e in ev['models']['via-rich-v7']['solution']['dominant_edges'][:3]:
                key=e['resistor'];row=dict(resistor=key,nodes=e['raw_wire_nodes'],resistance_ohm=e['resistance_ohm'])
                assert wanted.setdefault(key,row)==row
        lines=(OUT/'capture/wire/rc03/wires.spice').read_text().splitlines();spice={}
        for number,line in enumerate(lines,1):
            if line.startswith('R'):
                fields=shlex.split(line);assert len(fields)==4 and fields[0]not in spice
                spice[fields[0]]=dict(line=number,text=line,nodes=fields[1:3],resistance_ohm=float(fields[3]))
        assert len(spice)==13186
        r['wire_resistors']=[];nodes=set()
        for name,expected in wanted.items():
            actual=spice[name];assert actual['nodes']==expected['nodes']and actual['resistance_ohm']==expected['resistance_ohm']
            r['wire_resistors'].append(dict(**expected,original_spice=actual));nodes.update(expected['nodes'])
        raw={}
        for name in ('pump_wires.ext','pump_wires.res.ext'):
            lines=(OUT/'capture/wire/rc03'/name).read_text().splitlines();parsed=[(i,line,shlex.split(line))for i,line in enumerate(lines,1)if line.strip()and not line.lstrip().startswith('#')]
            raw[name]=dict(header=lines[:12],node_records={n:[dict(line=i,text=line)for i,line,tokens in parsed if n in tokens]for n in sorted(nodes)})
        r['native_raw_records']=raw
        anchors=json.loads((OUT/'capture/wire/anchors08.json').read_text());prefixes={n.split('.')[0]for n in nodes};r['terminal_anchors']=[a for a in anchors['anchors']if a['label']in prefixes]
        assert r['terminal_anchors']
        # Raw records are evidence, not guessed coordinates: preserve every line
        # for matching exact tokens, plus original files for format interpretation.
        r['unmatched_raw_node_names']=[n for n in sorted(nodes)if not any(raw[k]['node_records'][n]for k in raw)]
        tech=(OUT/'capture/ngspice-mim-tech/ihp-sg13g2-extract.tech').read_text().splitlines()
        r['native_resistance_technology_lines']=[dict(line=i,text=line)for i,line in enumerate(tech,1)if re.match(r'^\s*(resist|contact|units|scale|tech|style|lambda)\b',line)]
        geo=json.loads((OUT/'capture/source/wire/native05/result.json').read_text());r['native_geometry_keys']=list(geo)
        r['geometry_structure']={k:dict(type=type(v).__name__,count=len(v)if isinstance(v,(list,dict))else None,first=(v[0]if isinstance(v,list)and v else None))for k,v in geo.items()}
        assert all(sha(OUT/'capture'/n)==capture['outputs'][n]for n in selected)
        r.update(status='COMPLETE_NATIVE_WIRE_RESISTOR_RAW_LOCATION_REVIEW_NOT_ACCEPTANCE',sources_unchanged=True,scope='Exact raw resistor records, matching node records and physical anchor evidence only. No change to geometry, R/C, circuit, solver, waveform or gates. Original CDR electrical rejection remains.')
    except BaseException as e:r.update(status='FAIL_NATIVE_WIRE_LOCATION_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
