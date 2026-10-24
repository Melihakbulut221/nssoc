# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
p=Path('hw/soc/flow/check_pcie_clock_div4_v7.py'); s=p.read_text()
s=s.replace('import argparse\n','import argparse\nimport ast\nimport os\nimport resource\nimport shutil\nimport signal\nimport subprocess\nimport threading\nimport time\n')
marker='APP_SHA = '
a=s.index(marker)
block='''LIFECYCLE_SOURCE = "scripts/characterize_pcie_clock_trim_stream_v2.py"
LIFECYCLE_SHA = "39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886"
SCRATCH_LIMIT = 80 * 1024**2
SHARED_FLOOR = 512 * 1024**2
ENTRY_FREE = 1024**3
LAUNCH_RESERVATION = 24 * 1024**2
SCRATCH_ROOTS = ()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def atomic(path, record):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def lifecycle():
    # Import only the four exact tested lifecycle definitions, not simulation
    # producers and not their mutable shared module globals.
    root = Path(__file__).resolve().parents[3]
    source = root / LIFECYCLE_SOURCE
    require(digest(source) == LIFECYCLE_SHA, "Frozen process lifecycle")
    names = {"Cancelled", "process_identity", "group_members", "ProcessOwner"}
    selected = [node for node in ast.parse(source.read_text()).body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    require(len(selected) == 4, "Exact lifecycle definitions")
    namespace = dict(os=os, Path=Path, threading=threading, signal=signal,
                     subprocess=subprocess, time=time, atomic=atomic,
                     require=require, FAILURE_GRACE_SECONDS=5.0)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
    return namespace


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    os.sched_setaffinity(0, {10})


def scratch_bytes():
    return sum(p.stat().st_size for root in SCRATCH_ROOTS
               if Path(root).exists() for p in Path(root).rglob("*") if p.is_file())


def execute(command, directory, label):
    require(sorted(os.sched_getaffinity(0)) == [10], "Owned physical work CPU10")
    require(shutil.disk_usage("/dev/shm").free >= ENTRY_FREE, "1GiB shared entry floor")
    require(scratch_bytes() + LAUNCH_RESERVATION <= SCRATCH_LIMIT, "80MiB own scratch with24MiB launch reserve")
    environment = {k: v for k, v in os.environ.items()
                   if k not in ("GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "PYTHONHOME")}
    start = time.monotonic()
    ns = lifecycle()
    owner_path = directory / (label + ".owned.json")
    require(not owner_path.exists(), "Fresh owned process receipt")
    with ns["ProcessOwner"](owner_path) as owner:
        with (directory / (label + ".log")).open("x") as log:
            process = owner.launch("native", list(map(str, command)), stdout=log,
                                   stderr=subprocess.STDOUT, env=environment, preexec_fn=limits)
            while process.poll() is None:
                owner.check()
                require(shutil.disk_usage("/dev/shm").free >= SHARED_FLOOR,
                        "512MiB continuous shared scratch floor")
                require(scratch_bytes() <= SCRATCH_LIMIT, "80MiB own scratch ceiling")
                owner.cancelled.wait(0.25)
            owner.check()
            code = owner.complete(process)
    return dict(command=list(map(str, command)), returncode=code,
                seconds=time.monotonic()-start, memory_limit_bytes=2*1024**3,
                elapsed_watchdog=None, log_sha256=digest(directory/(label+".log")),
                lifecycle_source_sha256=LIFECYCLE_SHA, process_owner_sha256=digest(owner_path))


'''
s=s[:a]+block+s[a:]
s=s.replace('    args = parser.parse_args()\n','    parser.add_argument("--generate", action="store_true", help="Generate a fresh standalone layout in an owned native process first")\n    args = parser.parse_args()\n')
s=s.replace('    generated = json.loads((layout / "result.json").read_text())\n    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"\n','''    require(not (layout == out or out.is_relative_to(layout) or layout.is_relative_to(out)), "Separate non-overlapping physical directories")
    global SCRATCH_ROOTS
    SCRATCH_ROOTS = (out, layout)
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
''')
s=s.replace('        raise ValueError("Divider circuit or native runtime changed")\n','''        raise ValueError("Divider circuit or native runtime changed")
    require(digest(root / LIFECYCLE_SOURCE) == LIFECYCLE_SHA, "Frozen lifecycle source")
    generation = None
    if args.generate:
        require(not layout.exists(), "Fresh standalone generation directory")
        # The generator independently restricts --out, pins all native PCell
        # and source inputs, and keeps prior geometry unchanged.
        out.mkdir(parents=True)
        generation = execute([app, "python", root / "hw/soc/flow/make_pcie_clock_div4_v7.py",
                              "--pdk", pdk, "--out", layout], out, "generation")
        require(generation["returncode"] == 0, "Native generation completed")
    generated = json.loads((layout / "result.json").read_text())
''')
s=s.replace('        "check_pcie_rx_cell.py",\n','')
s=s.replace('        app,\n        layout / "result.json",','        app,\n        root / LIFECYCLE_SOURCE,\n        layout / "result.json",')
s=s.replace('    out.mkdir(parents=True)\n    record = dict(','    out.mkdir(parents=True, exist_ok=args.generate)\n    record = dict(')
s=s.replace('        inputs={str(p): h for p, h in pins.items()},','''        inputs={str(p): h for p, h in pins.items()},
        generation_execution=generation,
        resource_contract=dict(cpu=10, child_address_space=2*1024**3,
                               own_scratch=SCRATCH_LIMIT, shared_floor=SHARED_FLOOR,
                               entry_free=ENTRY_FREE, launch_reservation=LAUNCH_RESERVATION,
                               healthy_elapsed_watchdog=None, failure_grace_seconds=5.0),''')
p.write_text(s)
