# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route the separately selectable post-CTS QSPI hold candidate."""
from pathlib import Path

from librelane.flows import Flow
from librelane.steps import OpenROAD
from librelane.state import DesignFormat

from interface_flow import Interfaces


class RouteWithQspiDelay(OpenROAD.GlobalRouting):
    # A native routing step ordinarily inherits the preceding netlists. This
    # variant inserts cells, so both exported views must describe the new ODB.
    outputs = [*OpenROAD.GlobalRouting.outputs, DesignFormat.NETLIST, DesignFormat.POWERED_NETLIST]

    def get_script_path(self):
        native = Path(super().get_script_path())
        script = native.read_text()
        anchor = "read_current_odb\n"
        if script.count(anchor) != 1:
            raise RuntimeError(f"Unexpected OpenROAD global routing script {native}")
        helper = Path(__file__).resolve().parents[1] / "flow/qspi_sck_hold_eco.tcl"
        guard = Path(__file__).resolve().parents[1] / "flow/check_timing_derate.tcl"
        source = guard.read_text() + "\n" + anchor + helper.read_text()
        source += "\ninsert_qspi_sck_hold_delay 14\ndetailed_placement\n"
        generated = Path(self.step_dir) / "qspi_hold_global_route.tcl"
        generated.write_text(script.replace(anchor, source))
        return str(generated)


@Flow.factory.register()
class QspiHoldInterfaces(Interfaces):
    Steps = [RouteWithQspiDelay if step is OpenROAD.GlobalRouting else step
             for step in Interfaces.Steps]


if __name__ == "__main__":
    from librelane.__main__ import cli

    cli()
