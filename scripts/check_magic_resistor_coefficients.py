#!/usr/bin/env python3
"""Hosted source/compiler fixture controls; no Magic build or extraction."""
import argparse,copy,json,os,subprocess,tempfile,traceback
from pathlib import Path
import cloud_magic_resistor_coefficients as c
b=c.b

def resistor_body(text):
    start=text.index("static void mrpResistor(")
    end=text.index("\nvoid ResPhysicalTraceBegin",start)
    return text[start:end]

def compiler_fixture(old,new,directory):
    # The two declarations below are the independently authenticated current header
    # fields, not an assumption that every member uses ResValue.
    prelude=r"""
#include <stdio.h>
typedef int ResValue;
#define NT 1
typedef struct { double exts_sheetResist[NT]; ResValue exts_viaResist[NT]; int exts_resistScale; } ExtStyle;
typedef struct { int ignored; } resNode;
typedef struct { float rr_value; int rr_status,rr_tt,rr_width,rr_cl; resNode *rr_node[2]; } resResistor;
static ExtStyle style={{17.25},{7},1};
static ExtStyle *ExtCurStyle=&style;
static FILE *mrpFile;
static int DBNumTypes=1;
static const char *DBTypeLongNameTbl[]={"metal-fixture"};
#define DBIsContact(x) 0
static void mrpHex(const char *s) { if(s)fputs("\"fixture\"",mrpFile);else fputs("null",mrpFile); }
static void mrpNode(const resNode *n) { (void)n;fputs("null",mrpFile); }
"""
    suffix=r"""
int main(void) {
  resResistor r={1.5,0,0,32,4,{NULL,NULL}};
  mrpFile=stdout;fputs("{\"fixture\":true",stdout);
  mrpResistor(&r);fputs("}\n",stdout);return 0;
}
"""
    record={}
    for label,text in (("old",old),("new",new)):
        path=directory/(label+".c");path.write_text(prelude+resistor_body(text)+suffix)
        argv=["gcc","-std=c11","-Wall","-Wextra","-Wformat=2","-Werror=format",str(path),"-o",str(directory/label)]
        run=subprocess.run(argv,capture_output=True,text=True)
        record[label+"_argv"]=argv;record[label+"_returncode"]=run.returncode
        record[label+"_stdout"]=run.stdout;record[label+"_stderr"]=run.stderr
        record[label+"_fixture"]=b.pin(path)
    assert record["old_returncode"]!=0 and "double"in record["old_stderr"]and "format"in record["old_stderr"]
    assert record["new_returncode"]==0,record["new_stderr"]
    run=subprocess.run([str(directory/"new")],capture_output=True,text=True)
    record.update(run_returncode=run.returncode,run_stdout=run.stdout,run_stderr=run.stderr)
    assert run.returncode==0 and not run.stderr
    row=json.loads(run.stdout)
    c.validate_coefficients(dict(row,type_index_valid=True))
    assert float.fromhex(row["sheet_resist_raw_hex"])==17.25 and row["via_resist_raw"]==7
    record.update(actual_mrpResistor_body_used=True,full_Magic_build=False,numerical_extraction_executed=False)
    return record

def controls(expected):
    ctx=b.context(os.environ);c.source_guard(expected)
    positive=["actual_qualified_header_and_warning_join"];refused=[]
    old=b.frozen.regular(b.ROOT,c.OLD_PAYLOAD).read_bytes();new=c.qualified_payload()
    assert new==c.derived_payload(old);positive.append("exact_five_seam_versioned_reverse_payload")
    def reject(label,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError):refused.append(label)
        else:raise AssertionError("accepted "+label)
    reject("v1_payload_corruption",lambda:c.derived_payload(old+b"\n"))
    row=dict(type_index_valid=True,sheet_resist_raw_hex="0x1.14p+4",via_resist_raw=7)
    c.validate_coefficients(row);positive.append("typed_finite_double_and_integer")
    for label,values in (("old_sheet",dict(sheet_resist_raw=0)),("bad_via_bool",dict(via_resist_raw=True)),
                         ("nonfinite_sheet",dict(sheet_resist_raw_hex="nan")),("nonstr_sheet",dict(sheet_resist_raw_hex=0))):
        r=dict(row,**values);reject(label,lambda r=r:c.validate_coefficients(r))
    c.validate_coefficients(dict(type_index_valid=False));positive.append("invalid_material_retains_absent_coefficients")
    with tempfile.TemporaryDirectory(prefix="magic-format-fixture-")as temp:
        compiler=compiler_fixture(old.decode(),new.decode(),Path(temp))
    positive.append("actual_body_corrected_typed_output")
    assert(len(positive),len(refused))==(5,5)
    return dict(status="PASS_MAGIC_COEFFICIENT_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=5,refusal=5,compiler=2),positive=positive,refusals=refused,compiler=compiler,
      native_executed=False,source_fixture_c_compilation_executed=True,native_CAD_executed=False,
      physical_acceptance=False,reduced_element_ownership_proved=False,
      current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False))

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();primary=None
    try:r=controls(a.pins_sha256)
    except BaseException as exc:
        primary=exc;r=dict(status="FAIL_MAGIC_COEFFICIENT_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),native_executed=False,physical_acceptance=False)
    raw=b.encode(r);print(raw.decode(),end="",flush=True)
    try:b.write(a.output,raw)
    except BaseException:
        if primary is None:raise
    if primary is not None:raise primary
if __name__=="__main__":main()
