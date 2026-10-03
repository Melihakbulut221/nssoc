# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A cloud move may relocate files, never alter the physical recipe."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_chip_ring_route import relocate


def inputs(tmp_path):
    p = tmp_path / "workspace/source/input.odb"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"odb")
    q = tmp_path / "pdk/ihp-sg13g2/std.lef"
    q.parent.mkdir(parents=True)
    q.write_bytes(b"lef")
    return {"workspace": "/original/repo", "pdk": "/original/pdk"}


def test_nested_paths_move_but_recipe_stays_identical(tmp_path):
    meta = inputs(tmp_path)
    old = dict(HSPACING=5, inputs=["/original/repo/source/input.odb", "/original/pdk/std.lef"])
    template = dict(HSPACING=5, inputs=["@BUNDLE@/workspace/source/input.odb", "@BUNDLE@/pdk/ihp-sg13g2/std.lef"])
    new = relocate(template, old, tmp_path, meta)
    assert new == dict(HSPACING=5, inputs=[str(tmp_path / "workspace/source/input.odb"), str(tmp_path / "pdk/ihp-sg13g2/std.lef")])
    assert old["inputs"][0] == "/original/repo/source/input.odb"


@pytest.mark.parametrize("bad", ["@BUNDLE@/../outside", "@BUNDLE@//outside",
                                "@BUNDLE@/workspace/missing", "@BUNDLE@/unknown/input",
                                "@BUNDLE@/workspace/source\\input.odb", "/original/repo/source/input.odb"])
def test_escaping_missing_and_unrelocated_paths_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        relocate(bad, "/original/repo/source/input.odb", tmp_path, inputs(tmp_path))


@pytest.mark.parametrize("template,old", [({"width": 4}, {"width": 5}),
                                         ({"new": 5}, {"old": 5}), ([1], [1, 2]),
                                         ("soc_other", "nssoc_chip"), (True, 1)])
def test_nonpath_changes_rejected(tmp_path, template, old):
    with pytest.raises(ValueError):
        relocate(template, old, tmp_path, {})


def test_path_cannot_silently_select_different_original_file(tmp_path):
    meta = inputs(tmp_path)
    with pytest.raises(ValueError):
        relocate("@BUNDLE@/workspace/source/input.odb", "/original/repo/other.odb", tmp_path, meta)


def test_symlink_escape_rejected(tmp_path):
    meta = inputs(tmp_path)
    p = tmp_path / "workspace/source/input.odb"
    p.unlink()
    p.symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        relocate("@BUNDLE@/workspace/source/input.odb", "/original/repo/source/input.odb", tmp_path, meta)
