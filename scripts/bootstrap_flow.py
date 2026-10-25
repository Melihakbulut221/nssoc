#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Install a checksum-pinned LibreLane devshell inside this checkout.

No root, shell mutation, package installation, extraction or execution occurs.
Enter the installed AppImage explicitly, then run its smoke test and install
its pinned full PDK before using the physical flow. A verified download alone
is not physical-flow acceptance.
"""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.0.5'
ARTIFACTS = {
    'x86_64': (1398053408, 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'),
    'aarch64': (1346154144, '6e49311c30bdf1e2a1285a6971078d2db47c0e21038cff5e6bad833cc7a11870'),
}
HEADROOM = 64 * 1024**2


def verify(path, architecture):
    size, expected = ARTIFACTS[architecture]
    if path.stat().st_size != size:
        raise ValueError('LibreLane image size differs from pinned release')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError('LibreLane image SHA256 differs from pinned release')


def install(destination, architecture, archive=None):
    if architecture not in ARTIFACTS:
        raise ValueError('Supported Linux architectures: x86_64, aarch64')
    destination = Path(destination).absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f'Refusing to replace existing target: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.with_name(destination.name + '.install-lock')
    lock.mkdir()
    try:
        required = ARTIFACTS[architecture][0] + HEADROOM
        if shutil.disk_usage(destination.parent).free < required:
            raise OSError(f'LibreLane download/copy needs {required} free bytes; full PDK and run storage are additional')
        with tempfile.TemporaryDirectory(prefix='.flow-install-', dir=destination.parent) as tmp:
            image = Path(tmp) / 'devshell.AppImage'
            if archive is not None:
                archive = Path(archive)
                verify(archive, architecture)
                shutil.copyfile(archive, image)
            else:
                url = f'https://github.com/librelane/librelane/releases/download/{VERSION}/librelane-devshell-{architecture}.AppImage'
                with urllib.request.urlopen(url, timeout=60) as source, image.open('xb') as output:
                    size = 0
                    while chunk := source.read(1024**2):
                        size += len(chunk)
                        if size > ARTIFACTS[architecture][0]:
                            raise ValueError('Download exceeds pinned LibreLane image size')
                        output.write(chunk)
            verify(image, architecture)
            image.chmod(0o755)
            # Atomic no-clobber publication, including non-cooperating writers.
            os.link(image, destination)
    finally:
        lock.rmdir()
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--architecture', choices=tuple(ARTIFACTS), default=platform.machine())
    parser.add_argument('--archive', type=Path, help='Verify and copy an already downloaded AppImage')
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--check', action='store_true', help='Verify an existing installation without executing it')
    args = parser.parse_args()
    if platform.system() != 'Linux' or args.architecture not in ARTIFACTS:
        parser.exit(2, 'Pinned devshell supports Linux x86_64/aarch64 only\n')
    destination = args.destination or ROOT / 'hw/soc/tools/physical' / f'librelane-{VERSION}-{args.architecture}.AppImage'
    try:
        if args.check:
            verify(destination, args.architecture)
        else:
            install(destination, args.architecture, args.archive)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + '\n')
    print(f'Verified LibreLane {VERSION}: {destination}')
    print('Physical tool smoke test, full PDK and design acceptance are separate requirements.')


if __name__ == '__main__':
    main()
