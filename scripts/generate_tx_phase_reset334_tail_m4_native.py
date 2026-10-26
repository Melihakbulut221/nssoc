#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate native entry; exact reviewed builder/material functions stay unchanged."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import make_pcie_tx_phase_reset334_tail_m4_v1 as candidate
candidate.METHOD='scripts/tx-phase-reset334-tail-m4-physical-methods.json'
def main():
    if '--material' in sys.argv:
        sys.argv.remove('--material')
        import tx_phase_reset334_tail_m4_native_material as material
        assert material.candidate is candidate
        material.main()
    else:candidate.main()
if __name__=='__main__':main()
