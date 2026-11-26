"""Report elapsed wall time at cocotb case transitions for the 4118-byte miter."""
import argparse
from pathlib import Path
import re
import subprocess
import time

NODE = "sw/tests/test_pcie_gen3_integrity_v23_miter.py::test_v22_v23_cycle_exact_all_public_outputs[4118]"


def run(command, base):
    start = time.monotonic()
    offset = 0
    with subprocess.Popen(command) as child:
        while True:
            status = child.poll()
            for log in base.glob("test*/capture/simulation.log"):
                with log.open(errors="replace") as stream:
                    stream.seek(offset)
                    while True:
                        line = stream.readline()
                        if not line.endswith("\n"):
                            break
                        offset = stream.tell()
                        if re.search(r"cocotb.regression\s+(running |\S+ (passed|failed))", line):
                            print(f"{time.monotonic()-start:.2f}s {line.strip()}", flush=True)
                break
            if status is not None:
                return status
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    base = args.directory.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", str(base)):
        parser.error("Use a path containing only letters, digits, slash, dot, underscore or hyphen")
    base.mkdir(parents=True, exist_ok=False)
    base = base / "pytest"
    raise SystemExit(run(["make", "test", f"PYTEST_ARGS=--basetemp={base} {NODE}"], base))
