#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use all original PD394 native physical gates for the new physical top."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'hw/soc/flow'))
sys.path.insert(0,str(Path.cwd()/'scripts'))
import check_pcie_cdr_retimed_parent_v3 as original
import cdr_retimed_compact_parent_plan as plan
original.TOP='nssoc_cdr_retimed_pd394_compact_supply_v1'
assert original.PORTS==plan.build()['ports']
if __name__=='__main__':original.main()
