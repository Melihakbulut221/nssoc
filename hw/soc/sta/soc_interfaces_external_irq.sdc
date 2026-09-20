# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: CERN-OHL-W-2.0
# Explicit IRQ-enabled profile. Earlier native measurements retain their SDC.
source [file join [file dirname [info script]] soc_interfaces.sdc]
set external_irq_port [get_ports -quiet irq_external_i]
if {[llength $external_irq_port] != 1} {
    error "External IRQ timing profile requires exactly one irq_external_i port"
}
# The external level is asynchronous to clk_i. This exception starts at the
# port and ends at its first synchronizer stage; the stage-0 Q -> stage-1 D
# path still has clk_i setup/hold checks. It is not a clock-domain blanket.
set_false_path -from $external_irq_port
