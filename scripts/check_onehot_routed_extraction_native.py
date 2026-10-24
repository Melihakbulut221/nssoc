#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Validate guarded STA transform against the actual pinned native runtime."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/pnr'))
import replay_onehot_routed_extraction_flow as method
from librelane.common import get_script_dir
assert os.environ.get('GITHUB_ACTIONS')=='true'
native=Path(get_script_dir())/'openroad/sta/corner.tcl'
guard=ROOT/'hw/soc/flow/check_timing_derate.tcl'
text=native.read_text();adapted=method.guarded_sta(text,guard.read_text())
assert adapted.count('read_spefs\n')==1 and adapted.count('report_checks -sort_by_slack')==text.count('report_checks -sort_by_slack')
assert adapted.count('NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED')==1
assert 'requires standalone OpenSTA and actual SPEF'in adapted
rejected=[]
for label,changed in [('missing_spef_read',text.replace('read_spefs\n','')),('duplicate_spef_read',text+'read_spefs\n'),('missing_netlist_load',text.replace('    read_timing_info\n',''))]:
    try:method.guarded_sta(changed,guard.read_text())
    except AssertionError:rejected.append(label)
    else:raise AssertionError('Accepted '+label)
assert len(rejected)==3
print(json.dumps(dict(status='PASS_NATIVE_STA_TRANSFORM_PREFLIGHT_ONLY_NOT_EXTRACTION_OR_TIMING',native_sha256=method.sha(native),derate_guard_sha256=method.sha(guard),rejected=rejected,flow_steps=[x.id for x in method.ReplayOnehotRoutedExtraction.Steps])))
