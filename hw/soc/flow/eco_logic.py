# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restricted local-function proof for a Yosys-elaborated physical ECO.

Compare every retained cell's input equations after contracting verified
positive buffers. State and SRAM boundaries remain explicit. This is not an
SRAM-interior, analog, initialization, delay, CDC or extracted-layout proof.
The caller must pin the netlists, elaboration commands, libraries and outputs.
"""
import functools
import itertools
import re


def group_body(text, start):
    depth, quote, escaped = 1, False, False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError('Unterminated Liberty group')


def standard_models(text):
    result = {}
    for match in re.finditer(r'\bcell\s*\(\s*(\w+)\s*\)\s*\{', text):
        body = group_body(text, match.end())
        if re.search(r'\b(?:ff_bank|latch_bank|statetable|three_state|bus)\s*[:(]', body):
            # An unsupported cell may only remain the exact same master with
            # identical input equations. Never resize, permute or contract it.
            continue
        states = []
        for state in re.finditer(r'\b(ff|latch)\s*\(([^)]*)\)\s*\{', body):
            states.append(re.sub(r'\s+', '', state[0] + group_body(body, state.end()) + '}'))
        functions = {}
        for pin in re.finditer(r'\bpin\s*\(\s*(\w+)\s*\)\s*\{', body):
            contents = group_body(body, pin.end())
            function = re.search(r'\bfunction\s*:\s*"([^"]+)"', contents)
            direction = re.search(r'\bdirection\s*:\s*"?(\w+)"?\s*;', contents)
            if direction is None:
                raise ValueError('Missing pin direction')
            functions[pin[1]] = (direction[1], re.sub(r'\s+', '', function[1]) if function else None)
        result[match[1]] = (functions, tuple(sorted(states)))
    return result


@functools.lru_cache(None)
def expression(text):
    tokens = re.findall(r'[A-Za-z_]\w*|[01!()*+^]', text)
    if ''.join(tokens) != re.sub(r'\s+', '', text):
        raise ValueError('Unsupported Liberty expression: ' + text)
    position = 0

    def atom():
        nonlocal position
        if position >= len(tokens):
            raise ValueError('Truncated expression')
        token = tokens[position]
        position += 1
        if token == '!':
            return ('!', atom())
        if token == '(':
            node = binary(0)
            if position >= len(tokens) or tokens[position] != ')':
                raise ValueError('Unbalanced expression')
            position += 1
            return node
        if not re.fullmatch(r'[A-Za-z_]\w*|[01]', token):
            raise ValueError('Unexpected expression token')
        return token

    def binary(level):
        nonlocal position
        operators = ['+', '^', '*']
        if level == len(operators):
            return atom()
        node = binary(level + 1)
        while position < len(tokens) and tokens[position] == operators[level]:
            position += 1
            node = (operators[level], node, binary(level + 1))
        return node

    ast = binary(0)
    if position != len(tokens):
        raise ValueError('Trailing expression tokens')
    return ast


def evaluate(node, values):
    if isinstance(node, str):
        return bool(int(node)) if node in ('0', '1') else values[node]
    if node[0] == '!':
        return not evaluate(node[1], values)
    a, b = evaluate(node[1], values), evaluate(node[2], values)
    return {'+': a or b, '*': a and b, '^': a != b}[node[0]]


def positive_buffer(cell, models):
    master = cell['type']
    return (re.fullmatch(r'sg13g2_(?:buf_(?:1|2|4|8|16)|dlygate4sd[123]_1)', master)
            and models.get(master) == ({'A': ('input', None), 'X': ('output', 'A')}, ())
            and set(cell['connections']) == {'A', 'X'})


def canonical_design(module, libraries, models):
    drivers, buffers, retained = {}, {}, {}

    def drive(bit, driver):
        if type(bit) is not int or bit in drivers:
            raise ValueError('Constant output or multiple drivers: ' + str(bit))
        drivers[bit] = driver

    for port, info in module['ports'].items():
        if info['direction'] not in ('input', 'output'):
            raise ValueError('Bidirectional top port unsupported')
        if info['direction'] == 'input':
            for index, bit in enumerate(info['bits']):
                drive(bit, ('port', port, index))
    for name, cell in module['cells'].items():
        master, pins = cell['type'], cell['connections']
        if cell.get('parameters') or master not in libraries:
            raise ValueError('Unmodelled or parameterized cell: ' + name)
        lib = libraries[master]['ports']
        if set(pins) - set(lib):
            raise ValueError('Unknown cell port: ' + name)
        for pin, info in lib.items():
            if info['direction'] not in ('input', 'output'):
                raise ValueError('Bidirectional cell port unsupported')
            if pin not in pins:
                if info['direction'] != 'output':
                    raise ValueError('Missing input pin: ' + name + '/' + pin)
                continue
            if len(pins[pin]) != len(info['bits']):
                raise ValueError('Pin width mismatch')
            if info['direction'] == 'output':
                for index, bit in enumerate(pins[pin]):
                    drive(bit, ('cell', name, pin, index))
        if positive_buffer(cell, models):
            if len(pins['A']) != 1 or len(pins['X']) != 1:
                raise ValueError('Invalid buffer width')
            buffers[pins['X'][0]] = pins['A'][0]
        elif re.fullmatch(r'sg13g2_(?:fill|decap)_\d+', master) and not pins and not lib:
            pass
        else:
            retained[name] = cell

    cache = {}

    def root(bit):
        path, seen = [], set()
        while bit in buffers and bit not in cache:
            if bit in seen:
                raise ValueError('Buffer cycle')
            seen.add(bit)
            path.append(bit)
            bit = buffers[bit]
        if bit in cache:
            value = cache[bit]
        elif bit in ('0', '1'):
            value = ('constant', bit)
        elif bit not in drivers:
            raise ValueError('Undriven signal: ' + str(bit))
        else:
            value = drivers[bit]
        for node in path:
            cache[node] = value
        return value

    for bit in buffers:
        root(bit)
    return retained, root, len(buffers)


@functools.lru_cache(None)
def functions_equal(old, new, a_items, b_items):
    a, b = dict(a_items), dict(b_items)
    sources = sorted(set(a.values()) | set(b.values()))
    if len(sources) > 12:
        raise ValueError('Unbounded local function')
    first, second = expression(old), expression(new)
    for bits in itertools.product((False, True), repeat=len(sources)):
        values = dict(zip(sources, bits))
        if evaluate(first, {p: values[v] for p, v in a.items()}) != evaluate(second, {p: values[v] for p, v in b.items()}):
            return False
    return True


def compare(before, after, libraries, models):
    a, ar, acount = canonical_design(before, libraries, models)
    b, br, bcount = canonical_design(after, libraries, models)
    if set(a) != set(b):
        raise ValueError('Non-buffer instance added or removed')
    if set(before['ports']) != set(after['ports']):
        raise ValueError('Top ports changed')
    for pin, original in before['ports'].items():
        target = after['ports'][pin]
        if ({k: v for k, v in original.items() if k != 'bits'} !=
                {k: v for k, v in target.items() if k != 'bits'} or
                [ar(x) for x in original['bits']] != [br(x) for x in target['bits']]):
            raise ValueError('Top port semantics changed: ' + pin)
    swapped = sized = 0
    for name, old in a.items():
        new = b[name]
        if set(old['connections']) != set(new['connections']):
            raise ValueError('Connected cell pins changed: ' + name)
        am, bm = old['type'], new['type']
        if am != bm:
            if am not in models or bm not in models or models[am] != models[bm]:
                raise ValueError('Cell function/state changed: ' + name)
            sized += 1
        if {p: (v['direction'], len(v['bits'])) for p, v in libraries[am]['ports'].items()} != {
                p: (v['direction'], len(v['bits'])) for p, v in libraries[bm]['ports'].items()}:
            raise ValueError('Cell interface changed')
        ap, bp = {}, {}
        for pin, bits in old['connections'].items():
            if libraries[am]['ports'][pin]['direction'] == 'input':
                ap[pin] = tuple(ar(x) for x in bits)
                bp[pin] = tuple(br(x) for x in new['connections'][pin])
        if ap == bp:
            continue
        if am not in models or models[am][1] or any(len(v) != 1 for v in ap.values()):
            raise ValueError('State/macro input changed: ' + name)
        # Exhaustively prove the actual Boolean equation under the proposed
        # input permutation; cell family names alone are insufficient.
        outputs = [p for p, d in libraries[am]['ports'].items() if d['direction'] == 'output']
        if not outputs:
            raise ValueError('Physical load connection changed: ' + name)
        for pin in outputs:
            fa, fb = models[am][0][pin][1], models[bm][0][pin][1]
            if fa is None or fb is None or not functions_equal(fa, fb,
                    tuple(sorted((p, v[0]) for p, v in ap.items())),
                    tuple(sorted((p, v[0]) for p, v in bp.items()))):
                raise ValueError('Boolean input equation changed: ' + name)
        swapped += 1
    return {'retained_cells': len(a), 'positive_buffers_before': acount,
            'positive_buffers_after': bcount, 'equivalent_sizes': sized,
            'equivalent_input_permutations': swapped}
