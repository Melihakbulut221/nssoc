# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Opt-in experiments; sourcing this file does not change a loaded design.
# See docs/106-timing-repair-research.md. These are NOT validated chip results.
# The caller must load the same isolated post-CTS checkpoint, propagated clocks,
# all corners, global-route parasitics and macro/dont-touch constraints in each
# experiment, then legalize, update routing/parasitics and measure every result.
# Never source this into the already running, hash-pinned repair controller.
proc nssoc_timing_experiment {profile} {
    switch -- $profile {
        setup_baseline { set repairs 1 }
        setup_batch4 { set repairs 4 }
        hold_guarded {
            # Deliberately omit -allow_setup_violations. Existing setup failures
            # still require before/after comparison; this is not an STA waiver.
            repair_timing -hold -setup_margin 0.1 -hold_margin 0.15 \
                -max_iterations 100 -max_buffer_percent 40 -verbose
            return
        }
        default { error "Unknown NSSOC timing experiment: $profile" }
    }
    # Change only repairs-per-pass between A and B. The native engine treats it
    # as an upper bound and may perform fewer moves or revert unsuccessful ones.
    repair_timing -setup -setup_margin 0.1 -max_iterations 100 \
        -max_repairs_per_pass $repairs -repair_tns 100 \
        -max_buffer_percent 40 -skip_buffer_removal -skip_size_down -verbose
}
