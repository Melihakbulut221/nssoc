# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Guarded scalar replacement arithmetic, not a waveform identity proof."""
import math,re

def replacement_current(loaded,forced,matched_idle):
    for row,kind in [(loaded,'570_idle'),(forced,'13_forced'),(matched_idle,'13_matched_idle')]:
        assert row['kind']==kind,'Exact loaded/state/matched-idle roles'
        assert row['sign_control_passed'] is True,'Actual sign convention prerequisite'
        assert math.isfinite(row['mean_a']),'Finite measured mean current'
        assert re.fullmatch('[0-9a-f]{64}',row['port_waveform_sha256']),'Exact boundary waveform identity pin'
        assert row['interval_s'][1]>row['interval_s'][0],'Ordered current window'
    assert loaded['vctrl_v']==forced['vctrl_v']==matched_idle['vctrl_v'],'Equal actual clamped voltage'
    assert loaded['interval_s']==forced['interval_s']==matched_idle['interval_s'],'Equal integration interval'
    assert loaded['port_waveform_sha256']==matched_idle['port_waveform_sha256'],'Actual loaded and subtraction-idle port waveforms must match'
    assert forced['noncommand_boundary_sha256']==matched_idle['noncommand_boundary_sha256'],'State replacement preserves all noncommand boundaries'
    # Caller must independently establish both waveform identities and every
    # native safety/current prerequisite. This function cannot confer them.
    return dict(mean_a=forced['mean_a']-matched_idle['mean_a'],
                arithmetic_only=True,physical_reachability_qualified=False)
