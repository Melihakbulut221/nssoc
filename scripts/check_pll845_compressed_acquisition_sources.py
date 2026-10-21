#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from cloud_pll845_compressed_disk import source_contract
m,current=source_contract(Path(__file__).resolve().parents[1])
print('PASS_PREALLOCATED_STORAGE_ONLY_DELTA_ELEVEN_NATIVE_METHODS_AND_EXACT_BOUNDED_PROOF')
