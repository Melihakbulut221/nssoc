#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud actual-parent conductor path probe with immutable source reconciliation."""
import argparse
import json
import os
from pathlib import Path
import sys

import run_io_parent_lvs as native
import run_io_tap_mask_probe as mask
from extract_gds_hierarchy import extract
from fetch_evidence_assets import fetch, verify
from run_chip_native_shard import restore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import io_parent_path_probe as helper  # noqa: E402

MANIFEST = ROOT/'docs/evidence/chip-offset-filled-native-input-assets-20260929.json'
GDS_SHA = 'a5c79c3920154af5a523e3a1224402d6e863b9f7dd91c367ac6256d9045ad8ff'
COHERENT_SHA = '92ee5cf87bfa7a08216a5d1fb9bc2e477d4fb732511b2fa6be6b03fe351f35f3'
HELPER = ROOT/'hw/soc/flow/io_parent_path_probe.py'
METHODS = ('scripts/run_io_parent_path_probe.py','hw/soc/flow/io_parent_path_probe.py',
 'sw/tests/test_io_parent_path_probe.py','.github/workflows/io-parent-path-probe.yml',
 'scripts/run_io_tap_mask_probe.py','scripts/run_io_parent_lvs.py','scripts/extract_gds_hierarchy.py',
 'scripts/run_chip_native_shard.py','scripts/fetch_evidence_assets.py','scripts/bootstrap_flow.py',
 'hw/soc/flow/prepare_ihp_lvs.py','hw/soc/flow/prepare_ihp_drc.py',
 'docs/evidence/io-vss-parent-boundary-next-action-20261002.json')


def program(deck):
    base = deck/mask.BASE
    order = mask.derivation_order((base/'sg13g2.lvs').read_text())
    # Check exact native physical metal/via edges before using that same graph in Python.
    connections = (base/'rule_decks/general_connections.lvs').read_text()
    for a,b in helper.EDGES:
        native_line = f'connect({a}, {b})'
        mask.require(native_line in connections, 'Native conductor connection changed: '+native_line)
    files = [base/'rule_decks/custom_classes.lvs']+[base/f'rule_decks/{name}.lvs' for name in order]
    prelude = "require 'json'\nrequire 'logger'\nlogger = Logger.new($stdout)\nsource($input, 'ACTUAL_IO_ADJACENCY')\nraise 'unexpected dbu' unless dbu == 0.001\nflat\nPARALLEL_RES = true\nSERIES_RES = true\n"
    includes = ''.join('# %include '+str(p.resolve())+'\n' for p in files)
    exports = 'probe_layers = {\n'+''.join(f"  '{name}' => {name},\n" for name in helper.LAYERS)+'}\n'
    return prelude+includes+exports+mask.RUBY_EXPORT


def validate_controls(path):
    row=json.loads(path.read_text())
    mask.require(row['status']=='PASS_NATIVE_PARENT_PATH_CONTROLS' and row['cases']==helper.CASES
                 and row['klayout_version']=='0.30.7' and row['dbu_um']==.001, 'Incomplete native controls')
    return row


def run(output):
    output=output.resolve()
    mask.require(output.is_relative_to(native.OUTPUT_ROOT.resolve()), 'Output escapes project')
    output.mkdir(parents=True,exist_ok=False)
    result=dict(schema=1,status='PREPARING',source_sha=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
        cell_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False)
    path=output/'result.json'
    def execute(args,name):
        row=native.execute(args,output/(name+'.log'));result[name]=row;native.write_json(path,result)
        mask.require(row['returncode']==0,'Native phase failed: '+name)
    try:
        native.verify_runtime(native.APP,'x86_64');_,pins=native.verify_deck()
        pins[str(native.APP)]=native.APP_SHA256
        pins.update({str(ROOT/name):native.sha(ROOT/name) for name in METHODS})
        pins[str(MANIFEST)]=native.sha(MANIFEST)
        result['input_sha256']=pins
        for name in pins:
            source=Path(name)
            if source==native.APP: continue
            target=output/'sources'/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source.read_bytes())
        execute([str(native.APP),'python',str(HELPER),'controls',str(output/'controls.json')],'controls')
        result['controls']=validate_controls(output/'controls.json')
        cache=output/'archive';cache.mkdir()
        asset=json.loads(MANIFEST.read_text())['assets'][0]
        mask.require(asset['sha256']=='eaaf4a0ad3afcdef5fb0b0baa02c22f1b605ecb3cffbfbdde7d028af57ae52d1','Unexpected parent asset')
        fetch(asset,cache); verify(cache/asset['name'],asset)
        result['parent_bundle_inventory']=restore(cache/asset['name'],output/'parent-bundle')
        gds=output/'parent-bundle/input/chip.gds'
        mask.require(native.sha(gds)==GDS_SHA,'Wrong actual parent GDS')
        roots=list(dict.fromkeys(row['master'] for row in helper.CHAIN))
        result['actual_master_subset']=extract(gds,roots,output/'actual-masters',GDS_SHA)
        fetch(mask.ASSET,cache)
        # Reuse the fully verified native-failure ZIP reader with a selected full source.
        old=mask.SELECTED
        try:
            mask.SELECTED={'comparison/inputs/unpadded-source.gds':('coherent.gds',COHERENT_SHA)}
            result['coherent_archive_inventory']=mask.unpack(cache/mask.ASSET['name'],output/'coherent')
        finally:
            mask.SELECTED=old
        execute([str(native.APP),'python',str(HELPER),'prepare',str(gds),str(output/'actual-masters/subset.gds'),
                 str(output/'coherent/coherent.gds'),str(output)],'prepare')
        result['source_reconciliation']=json.loads((output/'source-reconciliation.json').read_text())
        generated=output/'conductors.drc';generated.write_text(program(native.DECK))
        args=[str(native.APP),'klayout','-b','-zz','-r',str(generated)]
        for k,v in dict(input=output/'actual-adjacency.gds',run_mode='flat',masks=output/'conductors.json').items():
            args.extend(['-rd',f'{k}={v}'])
        execute(args,'derivation')
        execute([str(native.APP),'python',str(HELPER),'analyze',str(output)],'analysis')
        result['analysis']=json.loads((output/'analysis.json').read_text())
        native.check_pins(pins)
        mask.require(native.sha(gds)==GDS_SHA and native.sha(output/'coherent/coherent.gds')==COHERENT_SHA,'Original inputs changed')
        result['status']='COMPLETED_PARENT_PATH_DIAGNOSTIC'
    except BaseException as exc:
        result.update(status='FAILED_DIAGNOSTIC',error=str(exc));raise
    finally:
        result['output_sha256']={str(p.relative_to(output)):native.sha(p) for p in sorted(output.rglob('*'))
             if p.is_file() and p != path and 'archive' not in p.relative_to(output).parts and 'parent-bundle' not in p.relative_to(output).parts}
        native.write_json(path,result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)


if __name__=='__main__': main()
