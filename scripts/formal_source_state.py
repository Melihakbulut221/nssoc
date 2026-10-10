# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare SBY's copied sources with the files it actually read.

Relative [files] paths resolve against the invocation directory, not the
output directory. SBY records absolute source and destination paths in
logfile.txt even when -d puts results elsewhere. Never guess by basename.
"""

from pathlib import Path
import re
import shlex
import sys


def code(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def source_state(work):
    work = Path(work)
    try:
        config = (work / "config.sby").read_text()
        log = (work / "logfile.txt").read_text()
    except OSError:
        return "unchecked"
    copied = {}
    for source, destination in re.findall(r"Copy '(.*?)' to '(.*?)'\.", log):
        dest = Path(destination)
        # Absolute paths may name an older checkout location. Only the
        # suffix within src/ is used for the saved copy, not for origin.
        if "src" in dest.parts:
            index = max(i for i, part in enumerate(dest.parts) if part == "src")
            copied[Path(*dest.parts[index + 1:]).as_posix()] = Path(source)
    state = "clean"
    in_files = False
    checked = 0
    for line in config.splitlines():
        if line.startswith("["):
            in_files = line.strip() == "[files]"
            continue
        if not in_files:
            continue
        try:
            fields = shlex.split(line, comments=True)
        except ValueError:
            return "unchecked"
        if not fields:
            continue
        if len(fields) not in (1, 2):
            return "unchecked"
        source = Path(fields[-1])
        dest = fields[0] if len(fields) == 2 else source.name
        origin = copied.get(dest)
        if origin is None:
            # Absolute [files] entries are unambiguous even in old logs.
            origin = source if source.is_absolute() else None
        try:
            if origin is None:
                raise OSError("no source provenance")
            current = origin.read_text()
            saved = (work / "src" / dest).read_text()
        except (OSError, UnicodeError):
            state = "unchecked"
            continue
        checked += 1
        if current != saved:
            if code(current) != code(saved):
                return "stale"
            if state == "clean":
                state = "comment"
    return state if checked else "unchecked"


if __name__ == "__main__":
    print(source_state(sys.argv[1]))
