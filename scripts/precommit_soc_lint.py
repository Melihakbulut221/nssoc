#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Give each manual lint hook a new evidence directory without fetching tools."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8]
    raise SystemExit(subprocess.call([
        sys.executable, str(ROOT/'scripts/check_soc_lint.py'),
        '--output', str(ROOT/'hw/soc/out'/('precommit-lint-'+name)),
    ], cwd=ROOT))
