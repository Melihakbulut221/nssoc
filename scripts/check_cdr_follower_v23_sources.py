#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin new native candidate implementation before and after its cloud run."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'hw/soc/analog/pcie/cdr_retime_follower_v23.spice': '82e880bbba3660af3064f6eda688d4ae78c7a110fda460f6f930beb695ff128d', 'hw/soc/flow/make_pcie_cdr_retime_follower_v23.py': '86ecb6a2a3c3608877b3c943de0e4f58eab2df616fd4b23faf67345f87005dc0', 'hw/soc/flow/check_pcie_cdr_retime_follower_v23.py': '1c0042eb3b546252f18fed1adb9622d24727b1f0765e120bc1b0a6f3ee6a7857', 'scripts/cloud_cdr_follower_v23_physical.py': '6a439140d29af260565a6928705d718d396374b5c116ddcfe47a8cb635037863'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    print('PASS_FROZEN_FOLLOWER_V23_SOURCES_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
