#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict actual seven-instance I/O parent against its original c4 CDL contract.

Only reversible native CDL syntax is adapted. The original explicit substrate
GLOBAL is retained; no inferred globals, pin corrections, A/P fitting or layout
changes are permitted. A completed FAIL is evidence, never acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import run_io_parent_lvs as native
from fetch_evidence_assets import fetch, verify
from run_chip_native_shard import restore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
from io_parent_path_probe import CHAIN, TOP, require  # noqa: E402
from io_cell_schematic import parse_io_cdl, read_io_cdl_text, select_io_cdl  # noqa: E402
from normalize_io_cdl import normalize  # noqa: E402

PARENT_RUN = 36989535029
PARENT_SOURCE = '9e70e2b98376a849720d02241ee762ec5d3db3a9'
PARENT_INPUTS = {
 'actual-adjacency.gds':'c3a4e412d4d0ad52f4aef19a6452f251d399e8074ce012673cb87700484fa5c6',
 'result.json':'c86bd3c5541e200f85e635b49df13c5e700e274e1cd2c5f60402bf49c63df41a',
 'source-reconciliation.json':'e47dd329d2d5ed2ccf571374a98da80876b00a734fc9f3d1d90f7500cf90433c',
 'actual-masters/receipt.json':'50c07d59386e455ce37d0a8107a6344e5ea54628ca0cd4a67c09406ad2d15294',
}
CDL_SHA = '33217c1d8efc201d7183c1179f58dca4217cf9ab4630f1ddff80d6c4a6e89752'
ORIGINAL_GDS_SHA = 'aafb713ba3cd547ca48e919ec68eb6a8ed0f09051fed0fad813d3fdb043a4fa5'
MANIFEST = ROOT/'docs/evidence/io-tap-and-supply-contract-assets-20260929.json'
METHODS = ('scripts/run_io_strict_parent_lvs.py','sw/tests/test_io_strict_parent_lvs.py',
 '.github/workflows/io-strict-parent-lvs.yml','scripts/run_io_parent_lvs.py',
 'scripts/run_chip_native_shard.py','scripts/fetch_evidence_assets.py','scripts/bootstrap_flow.py',
 'hw/soc/flow/io_parent_path_probe.py','hw/soc/flow/io_cell_schematic.py',
 'hw/soc/flow/normalize_io_cdl.py','hw/soc/flow/transistor_schematic.py',
 'hw/soc/flow/repair_io_resistor_markers.py','hw/soc/flow/audit_klayout_lvs.py',
 'hw/soc/flow/prepare_ihp_drc.py','hw/soc/flow/prepare_ihp_lvs.py','sw/tests/io_parent_lvs_native.py',
 'docs/evidence/chip-ring-offset-route-verification-20260929.json')


def validate_parent(directory):
    for name,digest in PARENT_INPUTS.items():
        p=directory/name
        require(p.is_file() and not p.is_symlink() and native.sha(p)==digest,'Wrong immutable parent input: '+name)
    result=json.loads((directory/'result.json').read_text())
    proof=json.loads((directory/'source-reconciliation.json').read_text())
    require(result['status']=='COMPLETED_PARENT_PATH_DIAGNOSTIC' and result['source_sha']==PARENT_SOURCE
            and result['run_id']==str(PARENT_RUN),'Wrong parent source/run/result')
    require(result['analysis']['status']=='PARENT_SUBGRAPH_JOIN_PROVEN','Missing physical parent join')
    require(result['output_sha256']['actual-adjacency.gds']==PARENT_INPUTS['actual-adjacency.gds'], 'Parent GDS pin differs')
    require(proof['status']=='ACTUAL_PARENT_TRANSFORMS_VERIFIED' and not proof['source_cells_changed'],'Actual geometry provenance differs')
    require([{k:row[k] for k in CHAIN[0]} for row in proof['actual_parent_instances']]==list(CHAIN),'Wrong real parent placements')
    return result,proof


def reference(raw):
    require(hashlib.sha256(raw.encode()).hexdigest()==CDL_SHA,
            'Unsupported original c4 CDL')
    adapted,changes=normalize(raw)
    definitions,globals_=parse_io_cdl(adapted)
    require(globals_==['sub!'] and '*.GLOBAL sub!' in raw.splitlines(), 'Explicit original substrate declaration missing')
    order=['iovdd','iovss','vdd','vss']
    for row in CHAIN:
        header=definitions[row['master']].splitlines()[0].split()
        require(header[2:]==order,'Original macro formal order differs: '+row['master'])
    wrapper='.SUBCKT '+TOP+' '+' '.join(order)+'\n'
    wrapper+=''.join('X'+row['instance']+' '+' '.join(order)+' / '+row['master']+'\n' for row in CHAIN)
    wrapper+='.ENDS '+TOP+'\n'
    selected,cells,actual_globals=select_io_cdl(adapted+'\n'+wrapper,TOP)
    require(len(cells)==11 and actual_globals==globals_,'Unexpected parent reference closure')
    # Selection must preserve every adapted vendor body byte-for-byte.
    require(all(body==definitions[name] for name,body in cells.items() if name!=TOP),'Selected body changed')
    return selected,dict(top=TOP,wrapper=wrapper,formal_order=order,explicit_globals=globals_,
         selected_subcircuits=list(cells),dialect_changes=changes,globals_inferred=False,
         vendor_node_tokens_changed=False,tap_parameters_changed=False,terminal_candidate_applied=False)


def command(deck,inputs,case,mode):
    require(mode in ('deep','flat'),'Unsupported native mode')
    result=[str(native.APP),'klayout','-b','-zz','-r',str(deck)]
    for k,v in dict(input=inputs/'actual-adjacency.gds',schematic=inputs/'schematic.cir',topcell=TOP,
        report=case/'lvs.lvsdb.gz',log=case/'deck.log',target_netlist=case/'extracted.cir',run_mode=mode,thr=1,
        disable_tap_extraction='false',ignore_top_ports_mismatch='false').items():result.extend(['-rd',f'{k}={v}'])
    return result


def verdict(case,execution,audit_process):
    require(execution['returncode']==0,'Native parent extraction/comparison did not complete')
    for name in ('lvs.lvsdb.gz','deck.log','extracted.cir','audit.json'):
        require((case/name).is_file() and (case/name).stat().st_size>0,'Missing strict output: '+name)
    audit=json.loads((case/'audit.json').read_text())
    require(audit.get('top')==TOP and audit.get('circuits'),'Missing native parent/circuits')
    replay=native.assess(audit['circuits'],TOP,(case/'deck.log').read_text(),audit.get('extraction_diagnostics',[]))
    require(all(audit.get(k)==v for k,v in replay.items()),'Strict audit replay differs')
    require((audit['status']=='PASS within comparison scope' and audit_process['returncode']==0 and not audit['reasons'])
            or (audit['status']=='FAIL' and audit_process['returncode']==1 and audit['reasons']), 'Inconsistent strict audit')
    for name in ('lvs.lvsdb.gz','deck.log'):
        p=case/name
        require(audit['inputs'][str(p)]==dict(bytes=p.stat().st_size,sha256=native.sha(p)),'Audit report pin differs')
    return audit


def run(output,parent):
    output=output.resolve();parent=parent.resolve()
    require(output.is_relative_to(native.OUTPUT_ROOT.resolve()) and parent.is_relative_to(native.OUTPUT_ROOT.resolve()),'Path escapes project output')
    output.mkdir(parents=True,exist_ok=False)
    result=dict(schema=1,status='PREPARING',top=TOP,source_sha=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
       baseline='Original c4 reference contract and unchanged actual seven-instance chip subgraph',
       original_library_gds_sha256=ORIGINAL_GDS_SHA,original_library_cdl_sha256=CDL_SHA,
       cases={},parent_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False)
    target=output/'result.json'
    try:
        native.verify_runtime(native.APP,'x86_64');deck,pins=native.verify_deck()
        pins[str(native.APP)]=native.APP_SHA256;pins[str(MANIFEST)]=native.sha(MANIFEST)
        pins.update({str(ROOT/n):native.sha(ROOT/n) for n in METHODS})
        _,proof=validate_parent(parent)
        result['parent_source']=dict(run_id=PARENT_RUN,source_sha=PARENT_SOURCE,selected_inputs=PARENT_INPUTS,
            actual_parent_transforms=proof['actual_parent_instances'],all_coherent_masters_equal=proof['all_selected_polygon_layers_equal'])
        inputs=output/'inputs';inputs.mkdir()
        for name,digest in PARENT_INPUTS.items():
            dest=inputs/'prior-parent'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((parent/name).read_bytes())
            pins[str(dest)]=digest
        (inputs/'actual-adjacency.gds').write_bytes((parent/'actual-adjacency.gds').read_bytes())
        pins[str(inputs/'actual-adjacency.gds')]=PARENT_INPUTS['actual-adjacency.gds']
        result['controls_process']=native.execute([str(native.APP),'python',str(native.CONTROL),str(output/'controls')],output/'controls.log')
        require(result['controls_process']['returncode']==0,'Native strict controls failed')
        result['controls']=native.validate_controls(output/'controls/result.json')
        pins.update(result['controls']['input_sha256']);pins.update(result['controls']['output_sha256'])
        cache=output/'cache';cache.mkdir()
        asset=json.loads(MANIFEST.read_text())['assets'][0]
        require(asset['sha256']=='73bcfa260bb3844985fb3772925db1c71c32c44ffb25a61cf434f6de9e25826e','Wrong original reference archive')
        fetch(asset,cache);verify(cache/asset['name'],asset)
        result['reference_inventory']=restore(cache/asset['name'],output/'original-reference')
        raw_path=output/'original-reference/inputs/sg13g2_io.cdl'
        require(native.sha(raw_path)==CDL_SHA,'Original reference digest differs')
        pins[str(raw_path)]=CDL_SHA
        schematic,receipt=reference(read_io_cdl_text(raw_path))
        (inputs/'schematic.cir').write_text(schematic);native.write_json(inputs/'reference-preparation.json',receipt)
        pins[str(inputs/'schematic.cir')]=native.sha(inputs/'schematic.cir')
        result['reference_preparation']=receipt;result['input_sha256']=pins
        for name in pins:
            source=Path(name)
            if source==native.APP or source.is_relative_to(output):continue
            dest=output/'sources'/source.relative_to(ROOT)
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
        for mode in ('deep','flat'):
            native.check_pins(pins)
            case=output/mode;case.mkdir();detail=dict(status='RUNNING');result['cases'][mode]=detail
            result['status']='RUNNING_'+mode.upper();native.write_json(target,result)
            detail['native']=native.execute(command(deck,inputs,case,mode),case/'run.log')
            args=[str(native.APP),'python',str(native.AUDIT),str(case/'lvs.lvsdb.gz'),'--top',TOP,
                  '--deck-log',str(case/'deck.log'),'--output',str(case/'audit.json')]
            detail['audit_process']=native.execute(args,case/'audit.log')
            detail['audit']=verdict(case,detail['native'],detail['audit_process']);detail['status']=detail['audit']['status']
            native.write_json(target,result)
        native.check_pins(pins)
        result['parent_lvs_accepted']=all(c['status']=='PASS within comparison scope' for c in result['cases'].values())
        result['status']='PASS_STRICT_SEVEN_INSTANCE_PARENT_ONLY' if result['parent_lvs_accepted'] else 'FAIL_STRICT_SEVEN_INSTANCE_PARENT'
    except BaseException as exc:
        result.update(status='ERROR_OR_INCOMPLETE_COMPARISON',error=str(exc));raise
    finally:
        result['output_sha256']={str(p.relative_to(output)):native.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p!=target}
        native.write_json(target,result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--parent-inputs',type=Path,required=True)
    a=p.parse_args();run(a.output,a.parent_inputs)


if __name__=='__main__':main()
