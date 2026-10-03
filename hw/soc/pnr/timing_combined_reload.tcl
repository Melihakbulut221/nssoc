# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# A separate native process reads the exported candidate, never repair caches.
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
source [file join $::env(NSSOC_TARGETED_METHOD_ROOT) hw/soc/pnr/timing_combined_repair_helpers.tcl]
# io.tcl re-sources the producer's _TCL_ENV_IN, which names the original C10
# views. Preserve ONLY the intended child view/output bindings across that
# reset; all library, PDK and timing configuration still comes from its pinned
# original environment. Check the restored views' hashes before loading them.
set child_views {}
foreach key {CURRENT_ODB _SDC_IN STEP_DIR} {dict set child_views $key $::env($key)}
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
dict for {key value} $child_views {set ::env($key) $value}
set root $::env(NSSOC_COMBINED_ROOT)
set name $::env(NSSOC_COMBINED_RELOAD_STAGE)
if {$name ni {reload_first reload_repeat startup_control}} {error "Invalid independent reload stage"}
if {[nssoc_hold_sha $::env(CURRENT_ODB)] ne $::env(NSSOC_COMBINED_ODB_SHA)} {error "Reload ODB pin differs"}
if {[nssoc_hold_sha $::env(_SDC_IN)] ne $::env(NSSOC_COMBINED_SDC_SHA)} {error "Reload SDC pin differs"}
if {[nssoc_hold_sha [file readlink /proc/[pid]/exe]] ne $::env(NSSOC_TARGETED_ACTUAL_ELF_SHA256)} {
    error "Reload native ELF differs"
}
if {$name eq "startup_control"} {
    # Existing tiny fixture intentionally has an ideal clock and no explicit
    # propagation directive. Preserve it only in this short-lived child.
    set ::env(OPENLANE_SDC_IDEAL_CLOCKS) 1
}
read_current_odb
if {$name eq "startup_control"} {
    if {[[ord::get_db_block] getName] ne "tiny"} {error "Startup control did not read tiny ODB"}
    write_sdc -no_timestamp [file join $root startup-control.sdc]
    if {[nssoc_hold_sha [file join $root startup-control.sdc]] ne $::env(NSSOC_COMBINED_SDC_SHA)} {
        error "Tiny independent reload changed SDC"
    }
    nssoc_hold_write_json [file join $root startup-control.json] [nssoc_hold_jobject [dict create \
        pid [pid] parent_pid $::env(NSSOC_COMBINED_PARENT_PID) status [nssoc_hold_jstr PASS_TINY_INDEPENDENT_RELOAD] \
        executable_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file readlink /proc/[pid]/exe]]] \
        odb_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(CURRENT_ODB)]] \
        sdc_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(_SDC_IN)]]]]
    puts NSSOC_COMBINED_STARTUP_CONTROL_PASS
    exit
}
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set macros [nssoc_combined_macros]
nssoc_combined_prepare $root $name
if {[nssoc_combined_macros] ne $macros} {error "Reload changed SRAM placement"}
nssoc_combined_record $root $name true
nssoc_hold_write_json [file join $root "$name-process.json"] [nssoc_hold_jobject [dict create \
    pid [pid] parent_pid $::env(NSSOC_COMBINED_PARENT_PID) \
    executable_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file readlink /proc/[pid]/exe]]] \
    odb_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(CURRENT_ODB)]] \
    sdc_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(_SDC_IN)]] repair_invocations 0]]
puts "NSSOC_COMBINED_INDEPENDENT_RELOAD_COMPLETE $name"
