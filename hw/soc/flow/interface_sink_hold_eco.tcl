# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Instance numbers and SRAM sinks were measured on this repaired global-route state.
set expected 80cb70590de3325dbe8b3c656eabecb867ea00791767c874255c3d75e2af8815
if {[lindex [exec sha256sum -- $::env(CURRENT_ODB)] 0] ne $expected} {
    error "Sink-specific hold repair requires the measured source ODB"
}
set block [ord::get_db_block]
foreach pin {
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[7]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[1]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[20]
    u_ram.g_ram_2048x64_ecc.u_b3/A_DIN[1]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[19]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[28]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[18]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[6]
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[58]
    _132175_/D
    u_ram.g_ram_2048x64_ecc.u_b0/A_DIN[7]
    _132074_/D
    _131121_/D
    u_ram.g_ram_2048x64_ecc.u_b1/A_DIN[4]
    _132042_/D
    u_ram.g_ram_2048x64_ecc.u_b3/A_DIN[6]
    _131120_/D
} {
    lassign [split $pin /] inst_name term_name
    set inst [$block findInst $inst_name]
    if {$inst eq "NULL"} {error "Missing sink instance $inst_name"}
    set term [$inst findITerm $term_name]
    if {$term eq "NULL" || [[$term getMTerm] getIoType] ne "INPUT"} {error "Wrong sink $pin"}
    lassign [$term getAvgXY] ok x y
    if {!$ok} {error "Missing geometry of $pin"}
    set loc [list [ord::dbu_to_microns $x] [ord::dbu_to_microns $y]]
    insert_buffer -buffer_cell sg13g2_dlygate4sd3_1 -load_pins [list $pin] -location $loc -buffer_name nssoc_local_hold -net_name nssoc_local_delay
}
