# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIRECTORY='hw/soc/out/cloud-onehot-load-prepare'
PROFILE='onehot_round4_measured50'
r=json.loads((ROOT/DIRECTORY/'targets.json').read_text())
assert r['source_run']==39117700521 and len(r['targets'])==50
TARGETS=[(x['instance'],x['master'],x['pin'],x['reported_fanout']+1)for x in r['targets']]
assert len({x[0]for x in TARGETS})==50
COUNT=50
