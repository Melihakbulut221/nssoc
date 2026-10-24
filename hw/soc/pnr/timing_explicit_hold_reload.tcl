# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
source $::env(NSSOC_HOLD_DIAGNOSTIC_HELPER)
set methods $::env(NSSOC_TARGETED_METHOD_ROOT)
source [file join $methods hw/soc/pnr/timing_combined_repair_helpers.tcl]
source [file join $methods hw/soc/pnr/timing_explicit_hold_helpers.tcl]
set child_views {}
foreach key {CURRENT_ODB _SDC_IN STEP_DIR} {dict set child_views $key $::env($key)}
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
dict for {key value} $child_views {set ::env($key) $value}
set root $::env(NSSOC_COMBINED_ROOT);set name $::env(NSSOC_COMBINED_RELOAD_STAGE)
if {$name ni {reload_first reload_repeat}} {error "Invalid explicit independent reload stage"}
foreach key {ODB SDC} var {CURRENT_ODB _SDC_IN} {if {[nssoc_hold_sha $::env($var)] ne $::env(NSSOC_COMBINED_${key}_SHA)} {error "Explicit reload $key pin differs"}}
if {[nssoc_hold_sha [file readlink /proc/[pid]/exe]] ne $::env(NSSOC_TARGETED_ACTUAL_ELF_SHA256)} {error "Explicit reload native ELF differs"}
if {[nssoc_hold_sha $::env(NSSOC_EXPLICIT_INSERTION_FILE)] ne $::env(NSSOC_EXPLICIT_INSERTION_SHA)} {error "Insertion contract changed"}
set insertion [nssoc_combined_read $::env(NSSOC_EXPLICIT_INSERTION_FILE)]
read_current_odb
set_thread_count 2
set_propagated_clock [all_clocks]
set_dont_touch_objects
set macros [nssoc_combined_macros]
nssoc_explicit_verify $insertion
nssoc_explicit_route $root $name [dict get $insertion buffer]
nssoc_explicit_verify $insertion
nssoc_explicit_graph [file join $root "$name-graph-contracted.tsv"] $insertion
if {[nssoc_hold_sha [file join $root "$name-graph-contracted.tsv"]] ne $::env(NSSOC_EXPLICIT_ORIGINAL_GRAPH_SHA) ||
    [nssoc_hold_sha [file join $root "$name-original-objects.tsv"]] ne $::env(NSSOC_EXPLICIT_ORIGINAL_OBJECT_SHA)} {error "Fresh reload changed an original object or graph"}
if {[nssoc_combined_macros] ne $macros} {error "Fresh explicit reload changed SRAM placement"}
nssoc_combined_record $root $name true
nssoc_explicit_observe $root $name _135214_ _135215_
nssoc_hold_write_json [file join $root "$name-process.json"] [nssoc_hold_jobject [dict create \
    pid [pid] parent_pid $::env(NSSOC_COMBINED_PARENT_PID) repair_invocations 0 detailed_placement_invocations 0 \
    executable_sha256 [nssoc_hold_jstr [nssoc_hold_sha [file readlink /proc/[pid]/exe]]] \
    odb_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(CURRENT_ODB)]] \
    sdc_sha256 [nssoc_hold_jstr [nssoc_hold_sha $::env(_SDC_IN)]]]]
puts "NSSOC_EXPLICIT_INDEPENDENT_RELOAD_COMPLETE $name"
