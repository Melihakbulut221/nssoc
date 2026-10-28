#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned cloud build admission. Compilation alone never qualifies chip routing."""
import hashlib
import json
import os
import re
from pathlib import Path

METHOD = "scripts/mainchip-internal-witness-engine-build-methods.json"
REPOSITORY = "Melihakbulut221/nssoc"
UPSTREAM = "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"
IMAGE = "openroad/ubuntu24.04-dev@sha256:468fcd7f156dd350a648b0a3038ea16a5a25fde2e1b527f03d052108fea5ff3a"
IMAGE_ID = "sha256:a958d3bee9c5261b26e221e1c1461c92f830f14293bc5050848653bd7ec8d185"
MEMORY = 12 * 1024**3
CPUS = 2_000_000_000
PIDS = 4096
GROUP = "mainchip-internal-witness-engine-build"
GITLINKS = {
    "src/sta": ("https://github.com/The-OpenROAD-Project/OpenSTA.git", "857316ff001b2a8dbbdc5996944d08a6d38c87ab"),
    "third-party/abc": ("https://github.com/The-OpenROAD-Project/abc.git", "4c756ffb8dff7c583e80c7970d117abd3dfddb5c"),
}

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def pairs(items):
    value = {}
    for k, v in items:
        require(k not in value, "duplicate JSON key")
        value[k] = v
    return value

def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs)

def secure_file(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and relative and ".." not in p.parts, "path escape")
    current = Path(root)
    require(current.is_absolute() and not current.is_symlink(), "root identity")
    for part in p.parts:
        current = current / part
        require(not current.is_symlink(), "path symlink")
    require(current.is_file(), "missing regular file")
    return current

def method(root):
    m = decode(secure_file(root, METHOD).read_bytes())
    require(m["schema"] == "mainchip-internal-witness-engine-build-v1", "method schema")
    require(m["source_unit_complete"] is True, "incomplete source unit")
    require(type(m["source_controls_authorized"]) is bool and type(m["engine_build_authorized"]) is bool, "authorization type")
    for k in ("native_routing_authorized", "rc_sta_execution_authorized", "physical_acceptance", "qualified_engine"):
        require(m[k] is False if k != "qualified_engine" else m[k] is None, "unqualified build scope")
    require(m["upstream"] == UPSTREAM and m["image"] == IMAGE and m["image_id"] == IMAGE_ID, "engine identity")
    require(m["limits"] == dict(memory_bytes=MEMORY, nano_cpus=CPUS, pids=PIDS, build_seconds=10800, min_free_disk_bytes=32*1024**3), "resource limits")
    for path, expected in m["protected"].items():
        require(re.fullmatch("[0-9a-f]{64}", expected) and digest(secure_file(root, path).read_bytes()) == expected, "protected source: " + path)
    return m

def context(env):
    require(env.get("GITHUB_ACTIONS") == "true" and env.get("RUNNER_OS") == "Linux", "hosted Linux only")
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY, "repository identity")
    for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        require(re.fullmatch("[1-9][0-9]*", env.get(k, "")) is not None, "run identity")
    require(env["GITHUB_RUN_ATTEMPT"] == "1", "no automatic retry")
    require(re.fullmatch("[0-9a-f]{40}", env.get("GITHUB_SHA", "")) is not None, "immutable tested source")
    require(env.get("GITHUB_REF") == "refs/heads/codex/mainchip-internal-witness-engine-build", "build branch")
    token = env["GITHUB_RUN_ID"] + "-" + env["GITHUB_RUN_ATTEMPT"]
    return dict(name="nssoc-witness-build-" + token, source=env["GITHUB_SHA"], token=token)

def validate_image(info):
    require(info["Id"] == IMAGE_ID and info["Architecture"] == "amd64" and info["Os"] == "linux", "image configuration")
    require(IMAGE in info["RepoDigests"], "immutable image digest")
    return True

def create_argv(ctx, work, uid, gid):
    work = Path(work)
    require(work.is_absolute() and str(work) != "/" and "," not in str(work), "owned work mount")
    require(type(uid) is int and uid > 0 and type(gid) is int and gid > 0, "unprivileged container uid")
    require(re.fullmatch("nssoc-witness-build-[1-9][0-9]*-1", ctx["name"]) is not None, "owned container name")
    return ["docker", "create", "--name", ctx["name"],
            "--label", "nssoc.build.source=" + ctx["source"], "--label", "nssoc.build.token=" + ctx["token"],
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", str(MEMORY),
            "--memory-swap", str(MEMORY), "--cpus", "2", "--pids-limit", str(PIDS),
            "--user", str(uid) + ":" + str(gid), "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456",
            "--mount", "type=bind,src=" + str(work) + ",dst=/work",
            "--workdir", "/work/source", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--entrypoint", "/usr/bin/python3", IMAGE, "/work/inner.py"]

def validate_container(info, ctx, work, require_stopped=False):
    require(info["Name"] == "/" + ctx["name"] and re.fullmatch("[0-9a-f]{64}", info["Id"]) is not None, "container identity")
    require(info["Image"] == IMAGE_ID and info["Config"]["Image"] == IMAGE, "container image identity")
    require(info["Config"]["Labels"].get("nssoc.build.source") == ctx["source"]
            and info["Config"]["Labels"].get("nssoc.build.token") == ctx["token"], "container ownership")
    require(info["Path"] == "/usr/bin/python3" and info["Args"] == ["/work/inner.py"], "container entrypoint")
    h = info["HostConfig"]
    require(h["NetworkMode"] == "none" and h["ReadonlyRootfs"] is True and h["Privileged"] is False, "container isolation")
    require((h["Memory"], h["MemorySwap"], h["NanoCpus"], h["PidsLimit"]) == (MEMORY, MEMORY, CPUS, PIDS), "container resource binding")
    require(h["CapDrop"] == ["ALL"] and set(h["SecurityOpt"]) in ({"no-new-privileges"}, {"no-new-privileges:true"}), "container privileges")
    require(re.fullmatch("[1-9][0-9]*:[1-9][0-9]*", info["Config"]["User"]) is not None
            and info["Config"]["WorkingDir"] == "/work/source", "container user/workdir")
    require(h["Tmpfs"] == {"/tmp": "rw,nosuid,nodev,size=268435456"}, "container temporary storage")
    require(not h.get("Binds") and not h.get("Devices") and not h.get("DeviceRequests"), "unexpected device or bind")
    require(h.get("PidMode", "") == "" and h.get("IpcMode") == "private", "container namespace")
    require("PYTHONDONTWRITEBYTECODE=1" in info["Config"]["Env"], "container bytecode policy")
    mounts = [x for x in info["Mounts"] if x["Type"] == "bind"]
    require(len(mounts) == 1 and mounts[0]["Source"] == str(Path(work))
            and mounts[0]["Destination"] == "/work" and mounts[0]["RW"] is True, "container mounts")
    if require_stopped:
        require(info["State"]["Running"] is False and info["State"]["Pid"] == 0, "container still running")
    return True

def validate_terminal(info, inner):
    require(info["State"]["Running"] is False and info["State"]["ExitCode"] == 0
            and info["State"]["OOMKilled"] is False and info["State"]["Error"] == "", "container terminal failure")
    require(inner["status"] == "PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY"
            and not inner["terminal_errors"], "inner build failure")
    require(inner["compiled_complete_project"] is True and inner["physical_acceptance"] is False
            and inner["observer_equivalence_qualified"] is False, "build scope")
    first, last = inner["cgroup_initial"], inner["cgroup_terminal"]
    require(first["memory.max"] == last["memory.max"] == str(MEMORY)
            and first["memory.swap.max"] == last["memory.swap.max"] == "0"
            and first["pids.max"] == last["pids.max"] == str(PIDS), "native cgroup limits")
    for key in ("oom", "oom_kill", "oom_group_kill"):
        require(last["memory.events"].get(key, 0) == first["memory.events"].get(key, 0), "native cgroup OOM")
    for sample in (first, last):
        quota, period = sample["cpu.max"].split()
        require(quota != "max" and int(quota) == 2 * int(period), "native CPU quota")
        require({"oom", "oom_kill"} <= set(sample["memory.events"]), "missing memory events")
    require(int(last["memory.peak"]) <= MEMORY, "native memory peak")
    return True
