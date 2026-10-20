#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin the unchanged native MIM semantics and explicit new parent provenance."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'docs/evidence/cdr-selector-small-v24-extraction-pass-20261020.json': 'd9f9155a5e827c795358e1d73d6f010fc014402cc02f149159530c3bd9bb01b3', 'scripts/cloud_cdr_selector_small_v24_mim_parent_rc.py': 'b15663829dec12af6a275196222fce34d8574d4901d6ac3a1e45ab297e7c0144', 'scripts/cloud_cdr_selector_small_v24_mim_capture_stage.py': '220f538ab23238b98101990e5e9584d752e17dc202f574cdc551050cf87e4956', 'docs/evidence/cdr-selector-small-v24-mim-capture-input-20261020.json': '8fc32bcfe05b6b85858c434b0708bb0e7fc37a99046e266cc9ad3329fe8e5ce7', 'scripts/cdr-selector-small-v24-mim-capture-methods.json': '820a7e3b85358cde52960aff4dad291fcbbc3ed90cb9a8563da97026d27bc1ae', '.github/workflows/cdr-selector-small-v24-mim-parent-rc-cloud.yml': '465421ad86a9a18ad32494ffa6b18da9838eb405ebfcf203edeb4ef47e090144'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    print('PASS_FROZEN_PD476_MIM_CAPTURE_INPUTS_NOT_RAW_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
