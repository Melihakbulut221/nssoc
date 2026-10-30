#!/usr/bin/env python3
"""Versioned typed coefficient observer; all numerical extraction and equivalence gates unchanged."""
import argparse,collections,hashlib,math,os,shutil,subprocess,types
from pathlib import Path
import cloud_magic_resistor_provenance_build as b
ROOT=b.ROOT
require=b.require
decode=b.decode
encode=b.encode
write=b.write
pin=b.pin
frozen=b.frozen
historical=b.historical
source_census=b.source_census
trace_sources=b.trace_sources
PAYLOAD="scripts/magic_resistor_provenance_trace_v2.inc"
OLD_PAYLOAD="scripts/magic_resistor_provenance_trace.inc"
TYPE_PROOF="docs/evidence/magic-qualified-build-source-terminal-40984220615/readback/qualified-build-text.json"
TYPE_SHA="d433137da8c2240bc81f6f406a86c95838a9e42adb13d89ce67accc6f7d13015"
TYPE_BYTES=1575956
OLD_SHA="58c6ae5da8240f63131efcf25850a197b3195c78f4993c8703e556459ff58268"
RULES=[('/* NSSOC resistor provenance v1.', '/* NSSOC resistor provenance v2.'), ('nssoc_resistor_provenance_v1', 'nssoc_resistor_provenance_v2'), ('\\"sheet_resist_raw\\":%d,', '\\"sheet_resist_raw_hex\\":\\"%a\\",'), ('                ExtCurStyle->exts_sheetResist[resistor->rr_tt],', '                (double)ExtCurStyle->exts_sheetResist[resistor->rr_tt],'), ('                ExtCurStyle->exts_viaResist[resistor->rr_tt]);', '                (int)ExtCurStyle->exts_viaResist[resistor->rr_tt]);')]
START='#pragma GCC diagnostic push\n#pragma GCC diagnostic error "-Wformat"\n'
END='#pragma GCC diagnostic pop\n'

def derived_payload(raw):
    require(hashlib.sha256(raw).hexdigest()==OLD_SHA,"immutable v1 payload")
    text=raw.decode()
    for old,new in RULES:
        require(text.count(old)==1,"one typed format seam")
        text=text.replace(old,new)
    result=START+text+END
    restored=result.removeprefix(START).removesuffix(END)
    for old,new in reversed(RULES):
        require(restored.count(new)==1,"one reverse typed format seam")
        restored=restored.replace(new,old)
    require(restored.encode()==raw,"v2 reverse exact v1 bytes")
    return result.encode()

def type_proof(root=ROOT):
    raw=frozen.regular(root,TYPE_PROOF).read_bytes()
    require(len(raw)==TYPE_BYTES and hashlib.sha256(raw).hexdigest()==TYPE_SHA,"actual qualified type proof")
    files=decode(raw);h=files["work/trace-source/extract/extractInt.h"]
    require(hashlib.sha256(h["text"].encode()).hexdigest()==h["identity"]["sha256"]==
      "6a448fd1f72e4abcf3d1ff404613927428395ea6db10e82f2014f4c7e16f68d5","actual qualified header hash")
    text=h["text"]
    require("typedef int ResValue;"in text and "double\t\t exts_sheetResist[NT];"in text and
      "ResValue\t\texts_viaResist[NT];"in text,"actual independent coefficient field declarations")
    error=files["supervision/instrumented-make.stderr"]
    require(hashlib.sha256(error["text"].encode()).hexdigest()==error["identity"]["sha256"]==
      "c3428c6087ec8ea684425267b50b8a5700d4dfba3de01e85f9eba2e3bbb787cc","actual original compiler error")
    require("ResPrint.c:149:68: warning:"in error["text"]and "double"in error["text"],"actual v1 warning")
    return dict(header=h["identity"],compiler_stderr=error["identity"],sheet_type="double",via_type="int",
      v1_sheet_and_via_diagnostic_fields_unqualified=True)

def qualified_payload(root=ROOT):
    type_proof(root)
    actual=frozen.regular(root,PAYLOAD).read_bytes()
    require(actual==derived_payload(frozen.regular(root,OLD_PAYLOAD).read_bytes()),"exact versioned payload")
    return actual

def source_guard(expected,root=ROOT):
    result=b.source_guard(expected,root);qualified_payload(root);return result

def validate_coefficients(r):
    require("sheet_resist_raw"not in r,"old untyped sheet field forbidden")
    if r["type_index_valid"]:
        require(type(r["sheet_resist_raw_hex"])is str and type(r["via_resist_raw"])is int,
          "typed coefficient observations")
        require(math.isfinite(float.fromhex(r["sheet_resist_raw_hex"])),"finite sheet observation")
    else:
        require("sheet_resist_raw_hex"not in r and "via_resist_raw"not in r,"invalid type has no coefficients")
    return True

def instrument_source(baseline,out,c,root=ROOT):
    spec=decode(frozen.regular(root,historical.SPEC).read_bytes())
    expected={n:c["source_producer"]["candidate"][n]for n in spec["files"]}
    sources={n:(baseline/n).read_bytes()for n in expected}
    payloads={r["payload"]:frozen.regular(root,r["payload"]).read_bytes()for r in spec["rules"]if "payload"in r}
    require(set(payloads)=={"scripts/magic_resistor_provenance_trace.inc"},"only original payload seam")
    payloads["scripts/magic_resistor_provenance_trace.inc"]=qualified_payload(root)
    after=trace_sources(sources,expected,spec["rules"],payloads)
    target=out/"trace-source";shutil.copytree(baseline,target)
    for n,raw in after.items():(target/n).write_bytes(raw)
    final=source_census(target);initial=source_census(baseline)
    require(set(final)==set(initial)and {n for n in final if final[n]!=initial[n]}==set(expected),"only five diagnostic source changes")
    write(out/"trace-source-derivation.json",encode(dict(before=initial,after=final,rules=spec["rules"],
      all_original_bytes_reverse_exact=True,numerical_statements_changed=False,
      prior_three_upstream_snapshots_used_as_current=False,reduced_element_ownership_proved=False,
      instrumentation="nssoc_resistor_provenance_v2",payload=pin(frozen.regular(root,PAYLOAD)),
      diagnostic_format_errors_are_compiler_errors=True)))
    return target,final

def validate_trace(path,emitted_count,expected_lines=None):
    counts=collections.Counter();seq=0;epochs=0;active=False;footer=None;snapshot=None;seen_start=False;emitted=[]
    with path.open("rb")as stream:
        for line in stream:
            require(footer is None,"records after footer")
            r=decode(line);e=r.get("event");require(r.get("schema")==1,"trace schema");counts[e]+=1
            if e=="trace_start":
                require(not seen_start and seq==0 and counts[e]==1,"trace first record")
                require(r["instrumentation"]=="nssoc_resistor_provenance_v2"and r["resistor_footprint_is_not_inferred"]is True,"trace identity")
                seen_start=True;continue
            require(seen_start,"missing trace start")
            if e=="trace_end":
                require(r["records_before_footer"]==seq and r["epochs"]==epochs and r["net_still_open"]is False
                  and r["physical_ownership_proved"]is False and not active and snapshot is None,"complete trace footer")
                footer=r;continue
            seq+=1;require(r.get("seq")==seq,"contiguous trace sequence")
            if e=="net_begin":
                require(not active,"nested trace net");active=True;epochs+=1
                require(r["physical_ownership_proved"]is False and isinstance(r["net_name_hex"],str),"net provenance")
                bytes.fromhex(r["net_name_hex"])
            require(r.get("epoch")==epochs and epochs>0,"trace epoch")
            if e=="net_end":require(active,"net end without begin");active=False
            elif e=="snapshot_begin":
                require(snapshot is None and r["phase"]in ("before_simplify","after_simplify"),"snapshot begin")
                snapshot=[r["phase"],0]
            elif e=="snapshot_resistor":
                require(snapshot is not None and r["phase"]==snapshot[0]and r["index"]==snapshot[1],"snapshot sequence")
                snapshot[1]+=1
            elif e=="snapshot_end":
                require(snapshot==[r["phase"],r["count"]],"snapshot complete count");snapshot=None
            require(e in ("net_begin","net_end","create_tile","create_contact","snapshot_begin","snapshot_resistor",
              "snapshot_end","emitted_resistor","emitted_orphan_zero"),"unknown trace event")
            if "rr_value_milliohms_hex"in r:
                value=float.fromhex(r["rr_value_milliohms_hex"])
                require(math.isfinite(value)and value>=0,"finite native resistance observation")
                require(type(r["rr_tt"])is int and type(r["type_index_valid"])is bool,"typed material observation")
            if "rr_value_milliohms_hex"in r:validate_coefficients(r)
            if expected_lines is not None and e in ("emitted_resistor","emitted_orphan_zero"):
                first=r["node1"]["name_hex"]if e=="emitted_resistor"else r["node1_name_hex"]
                second=r["node2"]["name_hex"]if e=="emitted_resistor"else r["node2_name_hex"]
                emitted.append(b'resist "'+bytes.fromhex(first)+b'" "'+bytes.fromhex(second)+b'" '+r["ext_value_token"].encode())
            if e in ("create_tile","create_contact","emitted_resistor","emitted_orphan_zero"):
                require(r["final_footprint_proved"]is False,"no reduced footprint ownership")
    require(footer is not None and counts["trace_start"]==counts["trace_end"]==1,"trace complete")
    require(counts["create_tile"]>0 and counts["create_contact"]>0 and counts["snapshot_resistor"]>0,"actual constructor observations")
    require(counts["emitted_resistor"]+counts["emitted_orphan_zero"]==emitted_count,"all native resistor emissions observed")
    require(counts["net_begin"]==counts["net_end"]==epochs,"all construction epochs closed")
    if expected_lines is not None:require(emitted==expected_lines,"every trace emitted endpoint/value/order matches native file")
    return dict(status="PASS_COMPLETE_ACTUAL_RESISTOR_TRACE_NOT_REDUCED_OWNERSHIP",counts=dict(counts),
      trace=pin(path),epochs=epochs,records=seq,reduced_element_ownership_proved=False)

def current_controls(raw,ctx):
    r=decode(raw)
    require(r["status"]=="PASS_MAGIC_COEFFICIENT_SOURCE_CONTROLS"and r["passed"]is True and
      r["counts"]==dict(positive=5,refusal=5,compiler=2),"actual coefficient controls")
    require(r["current_context"]==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False)and r["native_executed"]is False,"exact source coefficient controls")
    require(r["compiler"]["old_returncode"]!=0 and r["compiler"]["new_returncode"]==0 and
      r["compiler"]["run_returncode"]==0,"actual compiler refusal and corrected fixture")
    return r

def perform(ctx,reserved,controls_raw,expected,out,coefficient_controls,root=ROOT,
            api_call=frozen.api,fetch=frozen.download):
    source_guard(expected,root);tests=current_controls(coefficient_controls,ctx)
    write(out/"coefficient-source-controls.json",coefficient_controls)
    write(out/"coefficient-type-proof.json",encode(type_proof(root)))
    namespace=dict(b.perform.__globals__)
    changed=dict(instrument_source=instrument_source,validate_trace=validate_trace,source_guard=source_guard)
    namespace.update(changed)
    execute=types.FunctionType(b.perform.__code__,namespace,b.perform.__name__,b.perform.__defaults__,b.perform.__closure__)
    require(execute.__code__ is b.perform.__code__ and
      {k for k in namespace if namespace[k]is not b.perform.__globals__[k]}==set(changed),"only three explicit body-preserving seams")
    result=execute(ctx,reserved,controls_raw,expected,out,root,api_call,fetch)
    result.update(instrumentation="nssoc_resistor_provenance_v2",coefficient_type_proof=type_proof(root),
      compiler_format_gate="Scoped GCC error -Wformat on complete diagnostic payload",
      frozen_controller_code_identical=True,substituted_globals=sorted(changed),
      v1_coefficient_observations_remain_unqualified=True)
    return result

def main():
    p=argparse.ArgumentParser()
    for n in ("pins-sha256","reservation","controls","coefficient-controls","output"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args();ctx=b.context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout source")
    raw=Path(a.coefficient_controls).read_bytes()
    b.run(ctx,decode(Path(a.reservation).read_bytes()),Path(a.controls).read_bytes(),a.pins_sha256,
      Path(a.output).resolve(),lambda *args:perform(*args,coefficient_controls=raw))
if __name__=="__main__":main()
