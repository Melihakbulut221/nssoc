#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only read-only Vss tap mask attribution; never an LVS acceptance."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile

import run_io_parent_lvs as native
from fetch_evidence_assets import fetch, verify

ROOT = Path(__file__).resolve().parents[1]
TOP = 'sg13g2_IOPadVss'
BASE = 'ihp-sg13g2/libs.tech/klayout/tech/lvs/'
ASSET = dict(name='coherent-vss-native-failure-20261002.zip', bytes=27596825,
    sha256='b0527ae1fb9019181b97880581e33feb170aa9a8765cb3a1839607b965b78b2a',
    url='https://github.com/Melihakbulut221/nssoc/releases/download/'
        'evidence-20260927-chip-io/coherent-vss-native-failure-20261002.zip')
ARCHIVE_MEMBERS, ARCHIVE_EXPANDED = 65, 149259318
SELECTED = {
 'comparison/inputs/subset/subset.gds': ('subset.gds', '66bc5abfdb4863c4998e241ae54eb00f7a6372c1a435af43492be1b984fd7d17'),
 'comparison/inputs/subset/receipt.json': ('subset-receipt.json', '076663cab5da0dc8906830d358f792c1ff138facd0467dea9c4d9be518dbaa30'),
 'comparison/deep/lvs.lvsdb.gz': ('deep.lvsdb.gz', 'e7015181489a8c1d5a519b8113b79cd051d0ffe83b18145e2593614f02dc42a3'),
 'comparison/flat/lvs.lvsdb.gz': ('flat.lvsdb.gz', '6f19314235d0cbb473c31f09539d34e60e94ea4f3f6638b1dcf432755f50945f'),
}
ORDER = ('layers_definitions', 'general_derivations', 'mos_derivations', 'rfmos_derivations',
         'bjt_derivations', 'diode_derivations', 'res_derivations', 'cap_derivations',
         'cap_cmomi_derivations', 'cap_cmomf_derivations', 'esd_derivations',
         'ind_derivations', 'tap_derivations')
MASKS = ('activ_drw', 'activ_filler', 'pactiv', 'substrate_drw', 'pwell', 'ptap1_mk',
         'taps_exclude', 'ptap1_exc', 'ptap1_tie', 'ptap1_sub')
METHODS = ('scripts/run_io_tap_mask_probe.py', 'hw/soc/flow/io_tap_mask_probe.py',
 'sw/tests/test_io_tap_mask_probe.py', '.github/workflows/io-tap-mask-probe.yml',
 'scripts/run_io_parent_lvs.py', 'scripts/fetch_evidence_assets.py', 'scripts/bootstrap_flow.py',
 'hw/soc/flow/prepare_ihp_drc.py', 'hw/soc/flow/prepare_ihp_lvs.py')
HELPER = ROOT/'hw/soc/flow/io_tap_mask_probe.py'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unpack(archive, destination):
    verify(archive, ASSET)
    selected = {}
    inventory = {}
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        require(len(infos) == ARCHIVE_MEMBERS and sum(i.file_size for i in infos) == ARCHIVE_EXPANDED,
                'Original archive member/expanded size differs')
        require(len({i.filename for i in infos}) == len(infos), 'Duplicate ZIP member')
        for info in infos:
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename
                    and str(path) == info.filename and not info.is_dir()
                    and not (info.external_attr >> 16) & 0o170000 == 0o120000, 'Unsafe ZIP member')
            digest = hashlib.sha256()
            data = bytearray()
            with source.open(info) as stream:
                while chunk := stream.read(1024**2):
                    digest.update(chunk)
                    if info.filename in SELECTED:
                        data.extend(chunk)
            inventory[info.filename] = dict(bytes=info.file_size, sha256=digest.hexdigest())
            if info.filename in SELECTED:
                name, expected = SELECTED[info.filename]
                require(digest.hexdigest() == expected, 'Selected native input differs')
                selected[name] = data
    require(set(selected) == {v[0] for v in SELECTED.values()}, 'Missing selected input')
    destination.mkdir(exist_ok=False)
    for name, data in selected.items():
        (destination/name).write_bytes(data)
    return inventory


def derivation_order(entry):
    begin = entry.index('  # %include rule_decks/layers_definitions.lvs\n')
    end = entry.index('  # %include rule_decks/devices_connections.lvs\n', begin)
    includes = re.findall(r'^  # %include rule_decks/(\w+)\.lvs$', entry[begin:end], re.M)
    require(tuple(includes) == ORDER, 'Native derivation ordering changed')
    return includes


# This is an independent diagnostic program, not a modified vendor runset.
# Exact includes retain all derivation code and order. No connectivity, extractor,
# comparison, schematic, join-by-name or output-native-netlist call is present.
RUBY_PRELUDE = '''require 'json'
require 'logger'
logger = Logger.new($stdout)
# Tiny native geometry controls must complete BEFORE source($input, ...) is called.
r = RBA::Region.new(RBA::Box.new(0, 0, 80000, 300))
raise 'rectangle control' unless r.area == 24000000 && r.perimeter == 160600
outer = RBA::Region.new(RBA::Box.new(0, 0, 10000, 10000))
hole = outer - RBA::Region.new(RBA::Box.new(2000, 2000, 4000, 4000))
raise 'hole control' unless hole.area == 96000000 && hole.perimeter == 48000
a = RBA::Region.new(RBA::Box.new(0, 0, 10000, 10000))
b = RBA::Region.new(RBA::Box.new(5000, 0, 15000, 10000))
raise 'overlap control' unless (a & b).area == 50000000 && (a | b).area == 150000000
raise 'xor control' unless ((a | b) ^ (a + b).merged).is_empty?
# Captured Q contours encode holes with retraced cut edges.
bridge_points = [[0,0],[10000,0],[10000,10000],[0,10000],[0,0],[2000,0],
  [2000,2000],[2000,4000],[4000,4000],[4000,2000],[2000,2000],[2000,0],[0,0]]
bridged = RBA::Region.new(RBA::Polygon.new(bridge_points.map { |xy| RBA::Point.new(*xy) })).merged
raise 'bridged Q-hole control' unless bridged.area == 96000000 && bridged.perimeter == 48000 && (bridged ^ hole).is_empty?
# Exercise deep iterator flattening with a nonzero rotation and translation.
control_layout = RBA::Layout.new
control_layout.dbu = 0.001
control_top = control_layout.create_cell('CONTROL_TOP')
control_child = control_layout.create_cell('CONTROL_CHILD')
control_layer = control_layout.layer(1, 0)
control_child.shapes(control_layer).insert(RBA::Box.new(0, 0, 1000, 2000))
control_top.insert(RBA::CellInstArray.new(control_child.cell_index, RBA::Trans.new(1, false, 10000, 20000)))
control_store = RBA::DeepShapeStore.new
control_region = RBA::Region.new(RBA::RecursiveShapeIterator.new(control_layout, control_top, [control_layer]), control_store)
raise 'deep hierarchy setup control' unless control_region.is_deep?
control_flattened = RBA::Region.new
control_region.each_merged { |polygon| control_flattened.insert(polygon) }
control_expected = RBA::Region.new(RBA::Box.new(8000, 20000, 10000, 21000))
raise 'deep transformed export control' unless (control_flattened ^ control_expected).is_empty?
File.write($controls, JSON.pretty_generate({status: 'PASS_NATIVE_MASK_CONTROLS', cases: ['rectangle', 'hole', 'overlap', 'xor', 'bridged_q_hole', 'transformed_deep_export'], dbu_um: 0.001}))
raise 'invalid mode' unless ['deep', 'flat'].include?($run_mode)
source($input, 'sg13g2_IOPadVss')
raise 'unexpected dbu' unless dbu == 0.001
$run_mode == 'deep' ? deep : flat
PARALLEL_RES = true
SERIES_RES = true
'''
RUBY_EXPORT = '''
# Export only duplicate flattened polygon values; never modify source regions.
out = {status: 'DERIVED_MASKS_ONLY', mode: $run_mode, dbu_um: dbu, masks: {}}
probe_layers.each do |name, layer|
  region = RBA::Region.new
  layer.data.each_merged { |polygon| region.insert(polygon) }
  region.merge
  out[:masks][name] = {area_dbu2: region.area, perimeter_dbu: region.perimeter,
    polygons: region.each_merged.map { |polygon| polygon.to_s }.sort}
end
File.write($masks, JSON.pretty_generate(out))
'''


def program(deck_root):
    entry = (deck_root/BASE/'sg13g2.lvs').read_text()
    order = derivation_order(entry)
    paths = [deck_root/BASE/'rule_decks/custom_classes.lvs'] + [
        deck_root/BASE/f'rule_decks/{name}.lvs' for name in order]
    require(all(p.is_file() and not p.is_symlink() for p in paths), 'Missing exact include')
    includes = ''.join('# %include '+str(p.resolve())+'\n' for p in paths)
    export = 'probe_layers = {\n'+''.join(f"  '{name}' => {name},\n" for name in MASKS)+'}\n'
    return RUBY_PRELUDE + includes + export + RUBY_EXPORT


def captured_geometry(path, mode):
    text = gzip.decompress(path.read_bytes()).decode()
    require(' U(0.001)\n' in text, 'Unexpected native DBU')
    templates = {}
    pattern = r'D\((D\$ptap1(?:\$\d+)?) ptap1\n  T\(TIE\n   ([RQ])\(l\d+ ((?:\(-?\d+ -?\d+\) ?)+)\)\n'
    for m in re.finditer(pattern, text):
        pairs = [tuple(map(int, p)) for p in re.findall(r'\((-?\d+) (-?\d+)\)', m[3])]
        if m[2] == 'R':
            (x, y), (w, h) = pairs
            points = [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
        else:
            points = [pairs[0]]
            for dx, dy in pairs[1:]:
                points.append((points[-1][0]+dx, points[-1][1]+dy))
        require(m[1] not in templates, 'Duplicate native device template')
        templates[m[1]] = points
    circuits = dict(re.findall(r'^ X\((\w+)\n(.*?)^ \)\n', text.split('\nH(', 1)[0], re.M|re.S))
    require(set(circuits) == ({TOP} if mode == 'flat' else {TOP,'sg13g2_DCNDiode','sg13g2_DCPDiode'}),
            'Native captured circuit inventory differs')
    transforms = {TOP:(0,0,0)}
    for m in re.finditer(r'^  X\(\d+ (\w+) O\((\d+)\) Y\((-?\d+) (-?\d+)\)', circuits[TOP], re.M):
        require(m[1] not in transforms and int(m[2]) in (0,90,180,270), 'Unknown native child transform')
        transforms[m[1]] = tuple(map(int, m.group(2,3,4)))
    rows = []
    for cell, body in circuits.items():
        require(cell in transforms, 'Unmapped native circuit transform')
        angle, tx, ty = transforms[cell]
        for m in re.finditer(r'^  D\((\d+) (D\$ptap1(?:\$\d+)?)\n   Y\((-?\d+) (-?\d+)\)\n   E\(A ([\d.]+)\)\n   E\(P ([\d.]+)\)', body, re.M):
            dx, dy = int(m[3]), int(m[4]); points = []
            for x, y in templates[m[2]]:
                x,y = x+dx,y+dy
                x,y = {0:(x,y),90:(-y,x),180:(-x,-y),270:(y,-x)}[angle]
                points.append([x+tx,y+ty])
            rows.append(dict(cell=cell,device=m[1],template=m[2],area_um2=m[5],perimeter_um=m[6],
                             cell_transform=[angle,tx,ty],device_translation=[dx,dy],points_dbu=points))
    require(len(rows) == (3 if mode == 'flat' else 4) and len(templates) == len(rows), 'Native tap inventory differs')
    return rows


def check_controls(path):
    row = json.loads(path.read_text())
    require(row.get('status') == 'PASS_NATIVE_MASK_CONTROLS'
            and row.get('cases') == ['rectangle','hole','overlap','xor','bridged_q_hole','transformed_deep_export']
            and row.get('dbu_um') == 0.001, 'Tiny native controls incomplete')
    return row


def run(output):
    output = output.resolve()
    require(output.is_relative_to(native.OUTPUT_ROOT.resolve()), 'Output escapes project')
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema=1,status='PREPARING',source_sha=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
        scope='Read-only Vss stripe and parent/DCP tap overlap attribution only; no LVS comparison or connectivity diagnosis',
        cell_lvs_accepted=False,full_chip_lvs_accepted=False,manufacturing_approval=False,cases={})
    path = output/'result.json'
    native.write_json(path,result)
    try:
        native.verify_runtime(native.APP, 'x86_64')
        _, pins = native.verify_deck()
        pins[str(native.APP)] = native.APP_SHA256
        pins.update({str(ROOT/name):native.sha(ROOT/name) for name in METHODS})
        result['input_sha256'] = pins
        # Preserve small exact methods and all 53 deck sources; the verified runtime
        # remains external and is identified by its full binary SHA256.
        for name in pins:
            source=Path(name)
            if source == native.APP:
                continue
            target=output/'sources'/source.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source.read_bytes())
        # A separate tiny native phase gates download/processing of actual cell inputs.
        proc = native.execute([str(native.APP),'python',str(HELPER),'controls',str(output/'controls.json')], output/'controls.log')
        result['controls_process'] = proc
        require(proc['returncode'] == 0, 'Native geometry controls failed')
        result['controls'] = check_controls(output/'controls.json')
        cache=output/'archive';cache.mkdir()
        fetch(ASSET, cache)
        archive=cache/ASSET['name']
        result['archive_inventory'] = unpack(archive, output/'inputs')
        captured = {mode:captured_geometry(output/'inputs'/f'{mode}.lvsdb.gz',mode) for mode in ('deep','flat')}
        native.write_json(output/'captured-geometry.json', captured)
        generated = output/'derivation.drc'
        generated.write_text(program(native.DECK))
        result['derivation_program_sha256'] = native.sha(generated)
        for mode in ('deep','flat'):
            case=output/mode;case.mkdir()
            args=[str(native.APP),'klayout','-b','-zz','-r',str(generated)]
            for key,value in dict(input=output/'inputs/subset.gds',run_mode=mode,
                                  controls=case/'controls.json',masks=case/'masks.json').items():
                args.extend(['-rd',f'{key}={value}'])
            result['cases'][mode] = native.execute(args,case/'native.log')
            require(result['cases'][mode]['returncode']==0,'Native mask derivation failed: '+mode)
            check_controls(case/'controls.json')
        result['analysis_process'] = native.execute([str(native.APP),'python',str(HELPER),'analyze',str(output)],output/'analysis.log')
        require(result['analysis_process']['returncode']==0,'Captured/native mask attribution failed')
        result['analysis'] = json.loads((output/'analysis.json').read_text())
        require(result['analysis']['status']=='PASS_MASK_ATTRIBUTION_ONLY','Incomplete native mask analysis')
        for name,digest in pins.items():
            require(native.sha(Path(name))==digest,'Input changed during probe: '+name)
        for source,(name,digest) in SELECTED.items():
            require(native.sha(output/'inputs'/name)==digest,'Captured input changed: '+source)
        result['status']='PASS_MASK_ATTRIBUTION_ONLY'
    except BaseException as exc:
        result['status']='FAILED_DIAGNOSTIC';result['error']=str(exc)
        raise
    finally:
        result['output_sha256']={str(p.relative_to(output)):native.sha(p) for p in sorted(output.rglob('*'))
                                 if p.is_file() and p != path and p.name != ASSET['name']}
        native.write_json(path,result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.output)


if __name__ == '__main__':
    main()
