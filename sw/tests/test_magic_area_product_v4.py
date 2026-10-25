# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest

P=Path(__file__).resolve().parents[2]/'scripts/patch_magic_area_product_v4.py'
spec=importlib.util.spec_from_file_location('area_patch',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def source():
    return '/* unchanged native fields and resistance expression */\nfloat stored_area;\n'+'\n'.join(f'stored_area += {a};' for a,b in m.EDITS)+'\n'


def test_exactly_eight_operand_promotions_and_no_other_edit(monkeypatch):
    text=source();monkeypatch.setattr(m,'SOURCE_SHA',hashlib.sha256(text.encode()).hexdigest())
    patched=m.transform(text)
    assert len(m.EDITS)==8
    for old,new in m.EDITS:
        assert patched.count(new)==1
        patched=patched.replace(new,old)
    assert patched==text


@pytest.mark.parametrize('fault',['changed_source','missing_product','repeated_product'])
def test_patch_rejects_unbound_or_changed_native_construct(monkeypatch,fault):
    text=source();wanted=hashlib.sha256(text.encode()).hexdigest()
    if fault=='changed_source':text+='/* changed */'
    elif fault=='missing_product':text=text.replace(m.EDITS[0][0],'0')
    else:text+='\n'+m.EDITS[0][0]
    monkeypatch.setattr(m,'SOURCE_SHA',wanted if fault=='changed_source' else hashlib.sha256(text.encode()).hexdigest())
    with pytest.raises(ValueError):m.transform(text)


@pytest.mark.parametrize('dimensions',[(131071,16384),(131072,16384),(131073,16384),(209236,16000)])
def test_real_C_signed_overflow_control_and_preproduct_promotion(tmp_path,dimensions):
    compiler=shutil.which('cc')
    if not compiler:pytest.skip('native C compiler unavailable; native fixture results remain separate')
    a,b=dimensions
    original='#include <stdio.h>\nint main(void){volatile int x=%d,y=%d;float area=(x*y)/2;printf("%%.17g\\n",(double)area);return 0;}\n'%(a,b)
    fixed=original.replace('(x*y)/2','((double)x*y)/2')
    outputs=[]
    for index,text in enumerate((original,fixed)):
        src=tmp_path/f'case{index}.c';exe=tmp_path/f'case{index}';src.write_text(text)
        subprocess.run([compiler,'-O0','-fsanitize=signed-integer-overflow','-fno-sanitize-recover=all',str(src),'-o',str(exe)],check=True,capture_output=True)
        outputs.append(subprocess.run([str(exe)],capture_output=True,text=True))
    if a*b>2**31-1:
        assert outputs[0].returncode!=0 and 'signed integer overflow' in outputs[0].stderr
    else:assert outputs[0].returncode==0
    assert outputs[1].returncode==0 and not outputs[1].stderr
    assert float(outputs[1].stdout)>0
    # Native area storage is intentionally stillfloat, so retain its rounding.
    assert float(outputs[1].stdout)==pytest.approx(a*b/2,rel=1e-7)
