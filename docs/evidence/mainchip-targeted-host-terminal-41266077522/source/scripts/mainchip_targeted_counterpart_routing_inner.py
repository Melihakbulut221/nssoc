"""One scoped clear and route, retaining original restoration/preservation cycle."""
import os
import sys
import json
sys.path.insert(0, "/work/tail-source/scripts")
import mainchip_saved_diode_routing_inner as original
import mainchip_stale_wire_routing as inherited
from mainchip_bulk_postdrt_antenna_inner import p, c, DATA, ENGINE

SCRIPT = "/work/tail-source/scripts/mainchip_targeted_counterpart_routing_native.py"

def run_route_cycle(report, runner, preserver):
    cleared = False
    def scoped_runner(report, label, argv, seconds):
        nonlocal cleared
        if label == "bulk-postdrt-route":
            p.require(not cleared, "one clear before one route")
            p.require(argv == [ENGINE, "-no_init", "-exit", str(original.WORK / "route.tcl")]
                      and seconds == 14400, "original route invocation and budget")
            os.environ["NSSOC_TARGETED_ROUTE_PHASE"] = "clear"
            runner(report, "bulk-postdrt-stale-wire-clear",
                   [ENGINE, "-no_init", "-exit", "-python", SCRIPT], 1200)
            terminal = c.decode(c.secure_file(DATA, "stale-wire-clear-terminal.json").read_bytes())
            p.require(terminal["phase"] == "stale-wire-clear" and terminal["complete"] is True
                      and terminal["error"] is None and terminal["terminal_errors"] == [],
                      "actual complete native clear")
            p.require(all(terminal[k] is False for k in p.FLAGS), "no premature acceptance")
            cleared = True
            report["stale_wire_clear"] = terminal
        if label in ("bulk-postdrt-restored-audit", "bulk-postdrt-cleanup-class-audit"):
            p.require(argv == [ENGINE, "-no_init", "-exit", "-python", original.base.SCRIPT],
                      "exact original physical audit invocation")
            os.environ["NSSOC_TARGETED_ROUTE_PHASE"] = "audit"
            argv = [*argv[:-1], SCRIPT]
        return runner(report, label, argv, seconds)
    result = original.run_route_cycle(report, scoped_runner, preserver)
    p.require(cleared, "actual clear executed")
    return result

def main():
    # Refuse before any inherited acquisition, container or preparation phase.
    manifest = json.loads((p.ROOT / "scripts/mainchip-targeted-counterpart-routing-inputs.json").read_bytes())
    p.require(manifest["native_execution_authorized"] is True, "target routing not activated")
    inherited.source_gate()
    return inherited.clone(original.main, run_route_cycle=run_route_cycle)()

if __name__ == "__main__":
    sys.exit(main())
