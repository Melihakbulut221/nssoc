# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Make this directory importable, so tests can share one helper.

`sw/tests/evidence.py` resolves a run's recorded evidence, and more
than one test file needs it. pytest adds a test file's directory to
sys.path under rootdir-based import modes but not reliably under all of
them, and the suite is run three ways here: from the repository root,
from scripts/ci_local.sh, and from the checks workflow. This removes
the question.
"""

import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


@pytest.fixture(scope='session')
def historical_snapshot(tmp_path_factory):
    """Hash-verified original F6 files restored outside all live/frozen trees."""
    from evidence import ROOT, recorded_bundle
    return recorded_bundle(ROOT / 'docs/evidence/historical-recovery-20260920.json',
                           tmp_path_factory.mktemp('recorded-historical'))


@pytest.fixture(scope='session')
def prepared_sources(tmp_path_factory):
    """Pinned replayed dependencies, plus the current explicit fault-port patch."""
    import hashlib
    import importlib.util
    import json
    import re
    from evidence import ROOT, recorded_bundle
    metadata = ROOT / 'docs/evidence/prepared-sources-20260920.json'
    record = json.loads(metadata.read_text())
    pin = re.search(r'^IBEX_COMMIT\s*\?=\s*(\w+)',
                    (ROOT / 'hw/soc/tools.soc.mk').read_text(), re.M).group(1)
    assert pin == record['ibex_commit'], 'Ibex source snapshot needs regeneration'
    for name, digest in record['transform_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (
            'Dependency transform changed; regenerate source snapshot: ' + name)
    restored = recorded_bundle(metadata, tmp_path_factory.mktemp('prepared-sources'))
    soc = restored / 'hw/soc'
    spec = importlib.util.spec_from_file_location('recorded_ibex_patch',
                                                 ROOT / 'hw/soc/flow/ibex_fault_port.py')
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    (soc / 'genp').mkdir()
    (soc / 'genp/ibex_top.v').write_text(patcher.patch((soc / 'gen/ibex_top.v').read_text(), 'secded'))
    return soc
