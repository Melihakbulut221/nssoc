read_db {/home/runner/work/nssoc/nssoc/cloud-mainchip-two-signal-repair/work/repaired.odb}
set_thread_count 2
write_def {/home/runner/work/nssoc/nssoc/cloud-mainchip-two-signal-repair/work/drc-before.def}
drt::check_drc -output_file {/home/runner/work/nssoc/nssoc/cloud-mainchip-two-signal-repair/work/initial-drc.rpt} -marker_name NSSOC_INITIAL_ORIGINAL_CLOCK_RESTORE_DRC
write_def {/home/runner/work/nssoc/nssoc/cloud-mainchip-two-signal-repair/work/drc-after.def}
write_db {/home/runner/work/nssoc/nssoc/cloud-mainchip-two-signal-repair/work/drc-observed.odb}
