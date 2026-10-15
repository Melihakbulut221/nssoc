# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit original-route load repairs, never auto-adopted or threshold relaxed."""
import os
PROFILE=os.environ.get('NSSOC_CRITICAL_LOAD_PROFILE','two_buffer')
assert PROFILE in ('two_buffer','control_three_buffer'),PROFILE
# Name, original master, output terminal, original signal terminal count.
TARGETS=[
    ('$abc$1705011$auto$blifparse.cc:397:parse_blif$1749936','sg13g2_a22oi_1','Y',2),
    ('$abc$1705011$auto$blifparse.cc:397:parse_blif$1749937','sg13g2_nand4_1','Y',2),
]
if PROFILE=='control_three_buffer':
    # Native slow paths of68/91hold targets begin at retrain_done and cross
    # input37806/X: buf2 drives3loads,0.424164891pF,1.093724251ns output slew.
    # Separate measured candidate; not a promise of setup or hold improvement.
    TARGETS.append(('input37806','sg13g2_buf_2','X',4))
COUNT=len(TARGETS)
DIRECTORY='cloud-critical-load-eco' if PROFILE=='two_buffer' else 'cloud-control-load-eco'
COMPLETE_STATUS='COMPLETE_TWO_BUFFER_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF' if PROFILE=='two_buffer' else 'COMPLETE_THREE_BUFFER_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'

# Native Opendp.tcl displacement units are microns, not routing rules.
# Three-buffer predecessor failed only the added input-root buffer within100x20um.
MAX_DISPLACEMENT_UM=(100,20) if PROFILE=='two_buffer' else (1000,200)
