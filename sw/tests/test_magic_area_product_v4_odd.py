# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Supplemental exact C-language area arithmetic; old v4 evidence stays sealed."""
import shutil
import struct
import subprocess

import pytest


@pytest.mark.parametrize('x,y',[(3,3),(9673,329),(137873,329)])
def test_real_native_C_odd_area_division_and_unchanged_float_storage(tmp_path,x,y):
    cc=shutil.which('cc')
    if cc is None:pytest.skip('Native compiler unavailable')
    assert x*y<2**31 and x*y%2==1
    src=tmp_path/'area.c';exe=tmp_path/'area'
    src.write_text('#include <stdio.h>\nint main(void){volatile int x=%d,y=%d;float old=(x*y)/2;float fixed=((double)x*y)/2;printf("%%.17g %%.17g\\n",(double)old,(double)fixed);return 0;}\n'%(x,y))
    subprocess.run([cc,'-O0','-fsanitize=signed-integer-overflow','-fno-sanitize-recover=all',str(src),'-o',str(exe)],check=True,capture_output=True)
    p=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    actual=list(map(float,p.stdout.split()))
    f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
    assert actual==[f32((x*y)//2),f32((x*y)/2)] and not p.stderr
    # For sufficiently small products the actual retained half unit is visible;
    # float32 storage may round larger products identically, which is retained.
    if x*y<2**24:assert actual[1]-actual[0]==.5
