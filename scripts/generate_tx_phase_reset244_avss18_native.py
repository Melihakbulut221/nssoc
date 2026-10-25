#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the source-reviewed candidate to its separately authorized native contract."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import make_pcie_tx_phase_reset244_avss18_v1 as candidate
if __name__=='__main__':
    candidate.host()
    assert candidate.METHOD=='scripts/tx-phase-reset244-avss18-source-methods.json'
    candidate.METHOD='scripts/tx-phase-reset244-avss18-native-methods.json'
    candidate.main()
