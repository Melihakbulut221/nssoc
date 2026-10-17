# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only electrically inert straight-resistor spacing may be canonicalized."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
from repair_io_resistor_markers import canonicalize_straight_spacing


LINE = 'RR0 pad core 586.899 $SUB=sub! $[rppd] m=1 l=2u w=1u ps=180n trise=0 b=0'


def test_straight_resistor_keeps_all_nodes_and_other_parameters():
    output, changes = canonicalize_straight_spacing(LINE)
    assert output == LINE.replace('ps=180n', 'ps=0') + '\n'
    assert changes == [{'before': LINE, 'after': output.strip()}]


def test_bent_resistor_is_not_canonicalized():
    bent = LINE.replace('b=0', 'b=1')
    assert canonicalize_straight_spacing(bent) == (bent + '\n', [])


def test_model_equation_is_independent_only_at_zero_bends():
    def leff(b, ps):
        return (b+1)*2e-6 + (2/1.85*1.006e-6+ps)*b
    assert leff(0, 0) == leff(0, 180e-9) == 2e-6
    assert leff(1, 0) != leff(1, 180e-9)


@pytest.mark.parametrize('replacement', ['b=0 b=0', 'b=0.0', 'b={bends}', '', 'b=-1'])
def test_unknown_or_ambiguous_bends_are_rejected(replacement):
    with pytest.raises(ValueError):
        canonicalize_straight_spacing(LINE.replace('b=0', replacement))


@pytest.mark.parametrize('replacement', ['ps=180n ps=180n', 'ps={spacing}', 'ps=nan', ''])
def test_unknown_or_ambiguous_spacing_is_rejected(replacement):
    with pytest.raises(ValueError):
        canonicalize_straight_spacing(LINE.replace('ps=180n', replacement))


def test_continuation_is_parsed_before_bend_guard():
    wrapped = LINE.replace(' trise=0 b=0', '\n+ trise=0 b=0')
    assert canonicalize_straight_spacing(wrapped)[0] == LINE.replace('ps=180n', 'ps=0') + '\n'


def test_taps_comments_and_other_models_unchanged():
    source = '* ' + LINE + '\nXR0 tie sub! / ptap1 A=9p Perim=12u\n'
    assert canonicalize_straight_spacing(source) == (source, [])
