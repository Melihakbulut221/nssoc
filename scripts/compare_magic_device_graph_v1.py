#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact labeled-graph bijection; refinement is only a search accelerator."""
import networkx as nx


def exact_bijection(left, right):
    """Return an independently checked total mapping, or None.

    Each node must have a hashable ``color``. Numeric color values retain
    numeric equality (Decimal('7e-8') equals Decimal('7.0e-8')). No vertex,
    terminal, edge, or parallel-device representation is removed or merged.
    """
    if left.is_multigraph() or right.is_multigraph() or left.is_directed() or right.is_directed():
        raise ValueError('Simple undirected incidence graphs required')
    a, b = left.copy(), right.copy()
    colors = {data['color'] for graph in (a, b) for _, data in graph.nodes(data=True)}
    codes = {color: index for index, color in enumerate(sorted(colors, key=repr))}
    for graph in (a, b):
        for node in graph:
            graph.nodes[node]['refined'] = codes[graph.nodes[node]['color']]
    while True:
        signatures = [{node: (graph.nodes[node]['refined'], tuple(sorted(
            graph.nodes[neighbor]['refined'] for neighbor in graph[node])))
            for node in graph} for graph in (a, b)]
        unique = sorted(set(signatures[0].values()) | set(signatures[1].values()))
        lookup = {value: index for index, value in enumerate(unique)}
        prior_count = len({graph.nodes[node]['refined'] for graph in (a, b) for node in graph})
        for graph, signature in zip((a, b), signatures):
            for node in graph:
                graph.nodes[node]['refined'] = lookup[signature[node]]
        if len(unique) == prior_count:
            break
    mapping = nx.vf2pp_isomorphism(a, b, node_label='refined')
    if mapping is None:
        return None
    if (set(mapping) != set(left) or set(mapping.values()) != set(right)
            or len(mapping) != len(set(mapping.values()))
            or any(left.nodes[node]['color'] != right.nodes[target]['color']
                   for node, target in mapping.items())
            or {frozenset((mapping[x], mapping[y])) for x, y in left.edges}
            != {frozenset((x, y)) for x, y in right.edges}):
        raise ValueError('Native graph search returned an invalid complete bijection')
    return mapping
