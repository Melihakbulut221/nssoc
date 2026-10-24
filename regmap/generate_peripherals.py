#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# REUSE-IgnoreStart
"""Generate peripheral offsets for RTL, firmware and host tests from YAML.

These files own offsets within a block. memmap.yaml continues to own bases,
and regmap.yaml continues to own the frozen pilot's independent register ABI.
"""
import argparse
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[A-Z][A-Z0-9_]*$')


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    pairs = loader.construct_pairs(node, deep=deep)
    result = {}
    for key, value in pairs:
        if not isinstance(key, str): raise ValueError('YAML mapping keys must be strings')
        if key in result: raise ValueError(f'Duplicate YAML key: {key}')
        result[key] = value
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_registers(registers, block, bits):
    if not isinstance(registers, dict) or not registers:
        raise ValueError(f'Empty register map: {block}')
    offsets, rtl_names = set(), set()
    for name, reg in registers.items():
        if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(reg, dict) or set(reg) != {'offset', 'rtl'}:
            raise ValueError(f'Invalid register: {block}/{name}')
        offset, rtl = reg['offset'], reg['rtl']
        if type(offset) is not int or offset < 0 or offset >= 1 << bits or offset % 4:
            raise ValueError(f'Invalid word register offset: {block}/{name}')
        if not isinstance(rtl, str) or not NAME.fullmatch(rtl):
            raise ValueError(f'Invalid RTL name: {block}/{name}')
        if offset in offsets or rtl in rtl_names:
            raise ValueError(f'Duplicate register: {block}/{name}')
        offsets.add(offset)
        rtl_names.add(rtl)


def definitions(spec):
    """Public name, RTL name, RTL width, RTL value for every binding.

    Window selectors are word indices in RTL, byte offsets in the C/Python
    interfaces. The stride remains a byte count in all three outputs.
    """
    result = [(name, reg['rtl'], spec['address_bits'], reg['offset'])
              for name, reg in spec['registers'].items()]
    if 'window' in spec:
        window = spec['window']
        result.append((window['name']+'_STRIDE', window['rtl_stride'],
                       spec['address_bits'], window['stride']))
        width = (window['stride']//4 - 1).bit_length()
        result += [(window['name']+'_'+name, reg['rtl'], width, reg['offset']//4)
                   for name, reg in window['registers'].items()]
    return result


def load(directory):
    result = {}
    for path in sorted(directory.glob('*.yaml')):
        spec = yaml.load(path.read_text(), Loader=UniqueLoader)
        required = {'schema','block','base','address_bits','registers'}
        if not isinstance(spec,dict) or not required <= set(spec) or set(spec)-required-{'window'}:
            raise ValueError(f'Invalid peripheral schema: {path.name}')
        block = spec['block']
        if type(spec['schema']) is not int or spec['schema'] != 1 or not isinstance(block, str) or block != path.stem or not re.fullmatch('[a-z][a-z0-9_]*',block):
            raise ValueError(f'Invalid block identity: {path.name}')
        if not isinstance(spec['base'],str) or not re.fullmatch(r'SOC_[A-Z0-9_]+_BASE',spec['base']):
            raise ValueError(f'Invalid base reference: {block}')
        bits = spec['address_bits']
        if type(bits) is not int or not 2 <= bits <= 32: raise ValueError(f'Invalid address width: {block}')
        validate_registers(spec['registers'], block, bits)
        if 'window' in spec:
            window = spec['window']
            if not isinstance(window, dict) or set(window) != {'name','stride','rtl_stride','registers'}:
                raise ValueError(f'Invalid window schema: {block}')
            for key in ('name','rtl_stride'):
                if not isinstance(window[key], str) or not NAME.fullmatch(window[key]):
                    raise ValueError(f'Invalid window {key}: {block}')
            stride = window['stride']
            if type(stride) is not int or stride < 8 or stride >= 1 << bits or stride & (stride-1):
                raise ValueError(f'Invalid power-of-two window stride: {block}')
            validate_registers(window['registers'], block+'/'+window['name'], stride.bit_length()-1)
            if any(reg['offset'] >= stride for reg in spec['registers'].values()):
                raise ValueError(f'Global register overlaps indexed window: {block}')
        bindings = definitions(spec)
        if len({row[0] for row in bindings}) != len(bindings) or len({row[1] for row in bindings}) != len(bindings):
            raise ValueError(f'Conflicting window/global names: {block}')
        result[block] = spec
    if not result: raise ValueError('No peripheral specifications')
    return result


def rtl_output(spec, root):
    block = spec['block']
    source = {'npucfg': 'npu'}.get(block, block)
    path = root/'hw/soc/rtl'/('soc_'+source+'.v')
    text = path.read_text()
    bindings = definitions(spec)
    for name, rtl, bits, value in bindings:
        pattern = re.compile(r"(?m)^(\s*localparam \["+str(bits-1)+r":0\]\s+"+re.escape(rtl)+r"\s*=\s*)\d+'h[0-9a-fA-F]+(\s*;[^\n]*)$")
        if len(pattern.findall(text)) != 1: raise ValueError(f'Missing/duplicate RTL binding: {block}/{name}')
        marker = f' // regmap:{block}:{name}'
        def replacement(match):
            tail = match.group(2)
            if tail.endswith(marker): tail=tail[:-len(marker)]
            return match.group(1)+f"{bits}'h{value:0{(bits+3)//4}X}"+tail+marker
        text = pattern.sub(replacement,text)
    markers = re.findall(r'// regmap:'+re.escape(block)+r':([A-Z0-9_]+)', text)
    if sorted(markers) != sorted(row[0] for row in bindings):
        raise ValueError(f'Orphan/duplicate RTL register marker: {block}')
    return str(path.relative_to(root)), text


def outputs(specs, root=ROOT):
    cr = 'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut'
    note = 'Generated by regmap/generate_peripherals.py; edit the YAML files in regmap/peripherals.'
    c = [f'// {cr}', '// SPDX-License-Identifier: Apache-2.0', '', f'/* {note} */',
         '#ifndef SOC_REG_OFFSETS_H', '#define SOC_REG_OFFSETS_H', '']
    py = [f'# {cr}', '# SPDX-License-Identifier: Apache-2.0', '', f'# {note}', '']
    result = {}
    for block, spec in specs.items():
        bits = spec['address_bits']; upper = block.upper()
        values = {}
        for name, reg in spec['registers'].items():
            offset = reg['offset']; values[name] = offset
            c.append(f'#define SOC_{upper}_{name}_OFF 0x{offset:0{(bits+3)//4}X}u')
        c.append('')
        py.append(upper+' = '+repr(values));py.append('')
        if 'window' in spec:
            window = spec['window']
            prefix = upper+'_'+window['name']
            c.append(f'#define SOC_{prefix}_STRIDE 0x{window["stride"]:X}u')
            for name, reg in window['registers'].items():
                c.append(f'#define SOC_{prefix}_{name}_OFF 0x{reg["offset"]:X}u')
            c.append('')
            py.append(prefix+'_STRIDE = '+str(window['stride']))
            py.append(prefix+' = '+repr({name: reg['offset'] for name, reg in window['registers'].items()}))
            py.append('')
        rtl_path, rtl_text = rtl_output(spec, root)
        result[rtl_path] = rtl_text
    c.append('#endif /* SOC_REG_OFFSETS_H */')
    result['hw/soc/tb/sw/soc_reg_offsets.h'] = '\n'.join(c)+'\n'
    result['sw/golden/peripheral_regs_gen.py'] = '\n'.join(py)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    specs = load(ROOT/'regmap/peripherals')
    changed = []
    for relative, text in outputs(specs).items():
        path = ROOT/relative
        if not path.exists() or path.read_text() != text:
            changed.append(relative)
            if not args.check: path.write_text(text)
    if args.check and changed: parser.exit(1,'Stale peripheral registers: '+', '.join(changed)+'\n')
    print(f'{len(specs)} register blocks synchronized')


if __name__ == '__main__':
    main()
# REUSE-IgnoreEnd
