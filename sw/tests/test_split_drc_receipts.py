# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("fault", ["clean", "missing", "worker", "digest", "identity", "marker", "top", "xml", "category", "gds", "deck"])
def test_worker_gate(tmp_path, fault):
    script = Path(__file__).resolve().parents[2] / "scripts/check_split_drc_receipts.py"
    identity = dict(top="fixture", gds_sha256="a"*64, deck_sha256="b"*64, switches=["tiling"])
    for key in ("gds", "deck"):
        (tmp_path / key).write_text(key)
        identity[key + "_sha256"] = hashlib.sha256(key.encode()).hexdigest()
    tables = {"offgrid": ["offgrid"], "angle": ["angle"]}
    rows = []
    for table in tables:
        top = "other" if fault == "top" else "fixture"
        items = "<item><category>angle</category></item>" if fault == "marker" else ""
        category = "wrong" if fault == "category" else table
        xml = (f"<report-database><top-cell>{top}</top-cell><categories><category><name>{category}</name></category>"
               f"</categories><items>{items}</items></report-database>")
        p = tmp_path / table
        p.write_text(xml[:-3] if fault == "xml" else xml)
        rows.append(dict(table=table, report=p.name, identity=identity, exit=0,
                         sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    if fault == "missing":
        rows.pop()
    elif fault == "worker":
        rows[0]["exit"] = 137
    elif fault == "digest":
        rows[0]["sha256"] = "0"*64
    elif fault == "identity":
        rows[0]["identity"] = dict(identity, switches=["flat"])
    if fault in ("gds", "deck"):
        (tmp_path / fault).write_text("different input")
    for name, data in [("manifest", dict(tables=tables, identity=identity, gds="gds", deck="deck")), ("receipts", rows)]:
        (tmp_path / name).write_text(json.dumps(data))
    result = subprocess.run([sys.executable, script, tmp_path/"manifest", tmp_path/"receipts"],
                            capture_output=True)
    assert (result.returncode == 0) == (fault == "clean")
