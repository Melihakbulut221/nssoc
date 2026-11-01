"""Use the existing exact clear, restoration and physical audit lifecycle."""
import sys
sys.path.insert(0, "/work/tail-source/scripts")
import mainchip_targeted_counterpart_routing_inner as prior
import mainchip_stale_wire_routing as inherited
import mainchip_bounded_route_stage as stage

def run_route_cycle(report, runner, preserver):
    def bounded_runner(report, label, argv, seconds):
        if label == "bulk-postdrt-route":
            return stage.execute_stage(report, runner, argv, seconds, prior.original.WORK, prior.DATA)
        return runner(report, label, argv, seconds)
    return prior.run_route_cycle(report, bounded_runner, preserver)

def main():
    return inherited.clone(prior.main, run_route_cycle=run_route_cycle)()

if __name__ == "__main__":
    sys.exit(main())
