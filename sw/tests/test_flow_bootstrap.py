# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Installer rollback and physical-tool selection without installing real tools."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bootstrap_flow', ROOT / 'scripts/bootstrap_flow.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


@pytest.fixture
def image(tmp_path, monkeypatch):
    payload = b'fixture devshell, never executed\n'
    source = tmp_path / 'fixture.AppImage'
    source.write_bytes(payload)
    monkeypatch.setitem(flow.ARTIFACTS, 'x86_64', (len(payload), hashlib.sha256(payload).hexdigest()))
    monkeypatch.setattr(flow.shutil, 'disk_usage', lambda _: SimpleNamespace(free=10**9))
    def no_network(*args, **kwargs):
        raise AssertionError('unexpected network request')
    monkeypatch.setattr(flow.urllib.request, 'urlopen', no_network)
    return source


def test_install_checked_image_preserves_source_and_existing_destination(tmp_path, image):
    destination = tmp_path / 'tools with spaces' / 'flow.AppImage'
    assert flow.install(destination, 'x86_64', image) == destination
    assert destination.read_bytes() == image.read_bytes()
    assert destination.stat().st_mode & 0o111
    with pytest.raises(FileExistsError):
        flow.install(destination, 'x86_64', image)
    assert destination.read_bytes() == image.read_bytes()
    assert not list(destination.parent.glob('.flow-install-*'))
    assert not destination.with_name(destination.name + '.install-lock').exists()


@pytest.mark.parametrize('kind', ['size', 'digest', 'no_space', 'lock', 'dangling_symlink'])
def test_install_failure_never_replaces_existing_state(tmp_path, image, monkeypatch, kind):
    destination = tmp_path / 'flow.AppImage'
    lock = tmp_path / 'flow.AppImage.install-lock'
    if kind == 'size': image.write_bytes(image.read_bytes() + b'x')
    elif kind == 'digest': image.write_bytes(b'x' * image.stat().st_size)
    elif kind == 'no_space': monkeypatch.setattr(flow.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    elif kind == 'lock': lock.mkdir()
    else: destination.symlink_to(tmp_path / 'missing')
    with pytest.raises((OSError, ValueError)):
        flow.install(destination, 'x86_64', image)
    assert not destination.exists()
    assert destination.is_symlink() == (kind == 'dangling_symlink')
    assert lock.exists() == (kind == 'lock')
    assert not list(tmp_path.glob('.flow-install-*'))


@pytest.mark.parametrize('change', ['exact', 'truncated', 'oversized', 'corrupt'])
def test_download_is_verified_before_publication(tmp_path, image, monkeypatch, change):
    payload = image.read_bytes()
    if change == 'truncated': payload = payload[:-1]
    elif change == 'oversized': payload += b'x'
    elif change == 'corrupt': payload = b'x' * len(payload)
    calls = []
    def download(url, **kwargs):
        calls.append(url)
        return io.BytesIO(payload)
    monkeypatch.setattr(flow.urllib.request, 'urlopen', download)
    destination = tmp_path / 'installed'
    if change == 'exact':
        flow.install(destination, 'x86_64')
        assert destination.read_bytes() == image.read_bytes()
    else:
        with pytest.raises(ValueError):
            flow.install(destination, 'x86_64')
        assert not destination.exists()
    assert calls == [f'https://github.com/librelane/librelane/releases/download/{flow.VERSION}/librelane-devshell-x86_64.AppImage']
    assert not list(tmp_path.glob('.flow-install-*'))


def test_non_cooperating_writer_cannot_be_overwritten(tmp_path, image, monkeypatch):
    link = os.link
    def race(source, target):
        Path(target).write_text('concurrent owner')
        return link(source, target)
    monkeypatch.setattr(flow.os, 'link', race)
    destination = tmp_path / 'image'
    with pytest.raises(FileExistsError):
        flow.install(destination, 'x86_64', image)
    assert destination.read_text() == 'concurrent owner'


def shell_environment(tmp_path, **overrides):
    env = dict(os.environ)
    for key in ('FLOW_TOOL_MODE', 'FLOW_PY', 'LIBRELANE', 'FLOW_OPENROAD', 'VENV', 'SHIMS', 'OSS_CAD', 'OSS_CAD_SUITE', 'PDK_ROOT'):
        env.pop(key, None)
    env.update(overrides)
    env['LD_LIBRARY_PATH'] = '/must/not/leak'
    command = ['bash', '-c', 'source "$1" || exit $?; printf "%s\\n" "$FLOW_PY" "$LIBRELANE" "$FLOW_OPENROAD" "$PDK_ROOT" "${LD_LIBRARY_PATH-unset}"; command -v openroad || true', 'flow', str(ROOT / 'hw/soc/flow/physical_env.sh')]
    return subprocess.run(command, cwd=tmp_path, env=env, text=True, capture_output=True)


def test_default_paths_are_project_local_from_other_directory(tmp_path):
    result = shell_environment(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[:5] == [str(ROOT / p) for p in (
        'hw/soc/tools/flow-venv/bin/python', 'hw/soc/tools/flow-venv/bin/librelane',
        'hw/soc/tools/physical/bin/openroad', 'hw/soc/tools/pdk')] + ['unset']


def test_explicit_tools_with_spaces_and_pdk_override(tmp_path):
    shims = tmp_path / 'custom tools';shims.mkdir()
    (shims / 'openroad').write_text('#!/bin/sh\nexit 0\n');(shims / 'openroad').chmod(0o755)
    venv = tmp_path / 'flow venv'
    result = shell_environment(tmp_path, SHIMS=str(shims), VENV=str(venv), PDK_ROOT=str(tmp_path/'kit'))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [str(venv/'bin/python'), str(venv/'bin/librelane'), str(shims/'openroad'), str(tmp_path/'kit'), 'unset', str(shims/'openroad')]


def test_environment_mode_is_explicit_and_rejects_unknown_mode(tmp_path):
    result = shell_environment(tmp_path, FLOW_TOOL_MODE='environment', FLOW_PY='/chosen/python', LIBRELANE='/chosen/librelane', FLOW_OPENROAD='/chosen/openroad')
    assert result.returncode == 0
    assert result.stdout.splitlines()[:3] == ['/chosen/python', '/chosen/librelane', '/chosen/openroad']
    assert shell_environment(tmp_path, FLOW_TOOL_MODE='typo').returncode == 2


def test_missing_environment_tools_remain_missing(tmp_path):
    # Minimal executable inventory gives bash its path-resolution utilities,
    # but deliberately provides no OpenROAD, LibreLane or Python.
    bindir = tmp_path / 'bin';bindir.mkdir()
    for name in ('bash', 'dirname'):
        (bindir/name).symlink_to(shutil.which(name))
    result = shell_environment(tmp_path, FLOW_TOOL_MODE='environment', PATH=str(bindir))
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[:3] == ['', '', '']


def test_pnr_and_optional_checker_use_new_entry_points():
    text = (ROOT / 'hw/soc/flow/pnr_soc_top.sh').read_text()
    assert '. "$SOC_DIR/flow/physical_env.sh"' in text
    assert 'LANE=("$LIBRELANE")' in text
    assert 'LANE=("$FLOW_PY" "$PNR/interface_flow.py"' in text
    assert '$HOME/Documents/' not in text
    assert '$HOME/Documents/' not in (ROOT / 'scripts/ci_local.sh').read_text()
