# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Shared access to generated peripheral offsets for direct cocotb runs."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'sw'))
from golden.peripheral_regs_gen import BOOT, BUSSTAT, CLINT, ETH, GPIO, GPTIMER, GPTIMER_TIMER, GPTIMER_TIMER_STRIDE, I2C, NPUCFG, QSPI, SCRUB, SPI, SPW, UART
