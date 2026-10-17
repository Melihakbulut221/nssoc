#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind an experimental Yosys recipe to its intended, proved RTL inputs.

Checks explicit, single-line read_verilog commands used by the local PCIe
experiments. This is source provenance, not an RTL equivalence or STA proof.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shlex


FLAGS = {"-sv", "-defer", "-formal", "-lib", "-nolatches", "-noautowire"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(recipe, candidate_dir, required, proofs=()):
    recipe, candidate_dir = Path(recipe).resolve(), Path(candidate_dir).resolve()
    if not candidate_dir.is_dir() or not required:
        raise ValueError("Candidate directory and required RTL names are mandatory")
    sources = []
    includes = []
    defines = []
    for line in recipe.read_text().splitlines():
        words = shlex.split(line, comments=True)
        if not words or words[0] != "read_verilog":
            continue
        for word in words[1:]:
            if word in FLAGS:
                continue
            if word.startswith("-I") and len(word) > 2:
                include = Path(word[2:])
                if not include.is_absolute() or not include.is_dir():
                    raise ValueError("Invalid absolute include directory: " + word)
                includes.append(str(include.resolve()))
                continue
            if re.fullmatch(r"-D[A-Za-z_]\w*(?:=[A-Za-z0-9_.]+)?", word):
                defines.append(word[2:])
                continue
            source = Path(word)
            if not source.is_absolute() or not source.is_file() or source.suffix not in {".v", ".sv", ".vh", ".svh"}:
                raise ValueError("Unsupported or missing explicit RTL input: " + word)
            sources.append(source.resolve())
    if not sources or len(sources) != len(set(sources)):
        raise ValueError("Missing or duplicate read_verilog sources")
    for name in required:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("Required input must be a file basename")
        expected = candidate_dir / name
        actual = [p for p in sources if p.name == name]
        if actual != [expected] or not expected.is_file():
            raise ValueError("Required candidate source not selected exactly once: " + name)
    for source in sources:
        candidate = candidate_dir / source.name
        if candidate.is_file() and source != candidate:
            raise ValueError("Canonical/other source shadows available candidate: " + source.name)
    pins = {str(p): digest(p) for p in [recipe, *sources]}
    proof_paths = []
    for path in proofs:
        path = Path(path).resolve()
        report = json.loads(path.read_text())
        if not str(report.get("status", "")).startswith("PASS") or not report.get("inputs"):
            raise ValueError("Proof lacks passing status or pinned inputs: " + str(path))
        covered = set()
        for name, expected in report["inputs"].items():
            original = Path(name).resolve()
            actual = digest(original)
            wanted = expected if isinstance(expected, str) else expected["sha256"]
            if actual != wanted:
                raise ValueError("Proof input changed: " + name)
            pins[str(original)] = actual
            covered.add(original)
        if not any(candidate_dir / name in covered for name in required):
            raise ValueError("Proof does not bind a required candidate input")
        pins[str(path)] = digest(path)
        proof_paths.append(str(path))
    return {
        "status": "PASS_EXPLICIT_CANDIDATE_SYNTHESIS_SOURCE_BINDING",
        "required": required,
        "sources": [str(p) for p in sources],
        "include_directories": includes,
        "preprocessor_defines": defines,
        "proof_reports": proof_paths,
        "inputs": pins,
        "timing_accepted": False,
        "equivalence_accepted_by_this_check": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--require", action="append", required=True)
    parser.add_argument("--proof", action="append", type=Path, default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.recipe, args.candidate_dir, args.require, args.proof)
    result["inputs"][str(Path(__file__).resolve())] = digest(Path(__file__))
    with args.out.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
