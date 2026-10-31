#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only publication after current loaded execution; no native entry point."""
import copy,hashlib,json,os,shutil,traceback
from pathlib import Path

DIRECT={"native-result.json":"native/result.json",
 "preparation-summary.json":"preparation-proof/summary.json",
 "preparation-native-result.json":"preparation-proof/native-result.json"}
SOURCE_CHECK="publication-source-check.json"
PLAN="direct-publication-plan.json"
SOURCE_DIR="publication-source"

def strict_json(raw):
    def reject(value):raise ValueError("Nonfinite JSON constant: "+value)
    return json.loads(raw,parse_constant=reject)

def source_check(s,ctx):
    """Preserve the actual failed guard and changed regular bytes, without trusting them."""
    a=s.a;out=ctx["output"];errors=[];method=None;failure=None
    try:
        method=a.methods()
        a.require(all(n in method["protected_sha256"]for n in (
          "scripts/cdr_width_loaded_publication.py","scripts/check_cdr_width_loaded_publication.py",
          "docs/evidence/cdr-width-loaded-publication-repair-source-review-20261029.json")),
          "Current publication sources are not protected; evidence remains unqualified")
        a.require(method["source_controls_authorized"]is True
          and method["workflow_dispatch_authorized"]is True
          and method["controller_readiness"]is True
          and method["preparation_authorized"if ctx["prepare"]else"simulation_authorized"]is True,
          "Current execution authority not enabled; publication remains unqualified")
    except BaseException as error:
        failure=s.error_record("publication_source_authority",error)
    report={"source_head":os.environ["GITHUB_SHA"],"qualified":failure is None,
      "error":failure,"observations":[],"preservation_errors":errors,
      "changed_bytes_are_evidence_not_executable_authority":True}
    if failure is not None:
        saved=out/SOURCE_DIR
        a.require(not saved.exists()and not saved.is_symlink(),"Source failure evidence destination exists")
        saved.mkdir()
        protected={}
        # A malformed/unavailable method is evidence, never authority. Its raw
        # bytes are retained. Paths are checked by the original strict reader.
        try:
            raw=a.regular(a.ROOT,a.METHOD).read_bytes()
            target=saved/"execution-method.raw";target.write_bytes(raw)
            report["method_bytes"]={"member":str(target.relative_to(out)),
              "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
            parsed=strict_json(raw)
            a.require(type(parsed)is dict and type(parsed.get("protected_sha256"))is dict,
              "Unusable failed execution method map")
            protected=parsed["protected_sha256"]
        except BaseException as error:errors.append(s.error_record("preserve_failed_method",error))
        # These source paths are retained even if a corrupt method lost its map.
        names=set(protected)|set(a.NEW_REQUIRED)|{
          "scripts/cdr_width_loaded_publication.py","scripts/check_cdr_width_loaded_publication.py",
          "docs/evidence/cdr-width-loaded-publication-repair-source-review-20261029.json"}
        for name in sorted(names):
            expected=protected.get(name)
            try:
                raw=a.regular(a.ROOT,name).read_bytes();digest=hashlib.sha256(raw).hexdigest()
                if expected==digest:continue
                target=saved/"files"/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
                a.require(target.read_bytes()==raw,"Changed source preservation differs")
                report["observations"].append({"path":name,"expected_sha256":expected,
                  "actual_sha256":digest,"bytes":len(raw),"member":str(target.relative_to(out)),
                  "qualified":False})
            except BaseException as error:
                errors.append(dict(path=name,**s.error_record("preserve_changed_source",error)))
    a.write(out/SOURCE_CHECK,report)
    return report

def publish(s,ctx,result=None):
    a=s.a
    current=a.context()
    expected=s.context(ctx["case"],ctx["prepare"])
    a.require(ctx==expected,"Publication context/root differs from owned loaded case")
    tag,head=s.release.context(ctx["group"],os.environ)
    a.require(head==current["source"],"Publication current source mismatch")
    reservation=s.release.validate_release(s.release.api("releases/tags/"+tag),
      s.release.api("git/ref/tags/"+tag),tag,head)
    out=ctx["output"];transport=ctx["transport"]
    a.require(not out.is_symlink()and(not out.exists()or out.is_dir())
      and not transport.exists()and not transport.is_symlink(),"Invalid publication roots or transport exists")
    if not out.exists():out.mkdir(parents=True)
    a.require(not any((out/n).exists()or(out/n).is_symlink()for n in (SOURCE_CHECK,PLAN,SOURCE_DIR)),
      "Publication evidence already exists")
    # Recover available native files when the earlier source gate prevented the
    # normal finalize/copy path. Never overwrite a partially preserved tree.
    recovery=None
    if ctx["worker"].exists()and not(out/"native").exists():
        recovery=s.initial_result(ctx,{},{"publication_recovery":True})
        try:s.copy_worker(ctx,recovery)
        except BaseException as error:recovery["copy_error"]=s.error_record("publication_recovery_copy",error)
    terminal=None;terminal_error=None;raw_binding=None
    try:
        path=a.regular(out,"result.json");raw=path.read_bytes()
        raw_binding={"member":"result.json","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        terminal=strict_json(raw)
        a.require(type(terminal)is dict,"Loaded raw terminal must be an object")
        if result is not None:a.require(terminal==result,"Loaded in-memory/raw terminal differs")
        # The original validator is evaluated before publication-only metadata
        # changes the available output inventory. Include exactly the old map.
        prior_map={n:h for n,h in s.inventory(out).items()if n!="result.json"}
        a.require(terminal.get("outputs")==prior_map,"Loaded raw terminal complete output inventory differs")
        a.require(terminal["source_head"]==head and type(terminal["run_id"])is int
          and terminal["run_id"]==current["run_id"]and terminal["run_attempt"]==1,
          "Loaded terminal current identity changed")
        successful=s.validate_publication(ctx,terminal)
    except BaseException as error:
        terminal_error=s.error_record("raw_terminal_qualification",error);successful=False
    source=source_check(s,ctx)
    successful=successful and source["qualified"]
    # Keep the raw terminal untouched. This independent summary records failure
    # even when no valid terminal JSON ever reached disk.
    if successful:summary=copy.deepcopy(terminal)
    else:
        summary=s.initial_result(ctx,{},{"publication_recovery":True})
        summary.update(status="FAIL_UNQUALIFIED_CURRENT_WIDTH_LOADED_EVIDENCE",
          native_case_passed=False,terminal_finalization_complete=False,
          outer_terminal_finalization_complete=False)
    summary.update(publication_context=current,reservation=reservation,
      raw_terminal=raw_binding,raw_terminal_error=terminal_error,
      publication_source_check=source,publication_recovery=recovery,
      publication_qualified_as_success=successful,original_terminal_status=terminal.get("status")if type(terminal)is dict else None,
      raw_terminal_bytes_unchanged=True,accepted=False,full_phy_accepted=False,cdr_accepted=False,
      physical_accepted=False,qualified_pex=False)
    rows=[];direct_errors=[]
    for suffix,member in DIRECT.items():
        path=out/member
        a.require(not path.is_symlink(),"Symlink direct loaded report")
        if not path.exists():
            if successful and suffix=="native-result.json":
                direct_errors.append({"member":member,"error":"Successful native direct report missing"})
                successful=False
            rows.append({"member":member,"asset_suffix":suffix,"present":False,"disposition":"missing"})
            continue
        path=a.regular(out,member);raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        syntax_checked=False
        if successful:
            try:strict_json(raw);syntax_checked=True
            except BaseException as error:
                direct_errors.append(dict(member=member,**s.error_record("direct_terminal_qualification",error)))
                successful=False
        rows.append({"member":member,"asset_suffix":suffix,"present":True,"bytes":len(raw),
          "sha256":digest,"disposition":"direct_and_archive"if raw else"archive_only_empty",
          "JSON_syntax_checked":syntax_checked})
    if not successful:
        summary.update(status="FAIL_UNQUALIFIED_CURRENT_WIDTH_LOADED_EVIDENCE",native_case_passed=False,
          terminal_finalization_complete=False,outer_terminal_finalization_complete=False)
    summary["publication_qualified_as_success"]=successful
    summary["direct_terminal_errors"]=direct_errors
    plan={"schema":"current-width-loaded-direct-publication-plan-v1","files":rows,
      "empty_bytes_replaced":False,"zero_byte_files_preserved_in_archive":True,
      "publication_qualified_as_success":successful}
    a.write(out/PLAN,plan)
    s.storage(ctx,"publication")
    summary["outputs"]=s.inventory(out)
    transport.mkdir(parents=True)
    stem=ctx["group"]+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    summary_path=transport/(stem+".summary.json");a.write(summary_path,summary)
    manifest=s.pack(out,stem,transport,512*1024**2)
    files=s.evidence.publication_files(transport,summary_path,transport/(stem+".parts.json"),manifest)
    for suffix,member in {"direct-publication-plan.json":PLAN,"publication-source-check.json":SOURCE_CHECK}.items():
        target=transport/(stem+"."+suffix);shutil.copyfile(a.regular(out,member),target);files.append(target)
    for row in rows:
        if row["disposition"]!="direct_and_archive":continue
        path=a.regular(out,row["member"]);target=transport/(stem+"."+row["asset_suffix"])
        shutil.copyfile(path,target)
        a.require(target.stat().st_size==row["bytes"]and a.sha(target)==row["sha256"],"Direct loaded copy changed")
        files.append(target)
    a.require(len({p.name for p in files})==len(files)
      and all(p.stat().st_size>0 for p in files),"Empty or duplicate direct publication asset")
    a.require(s.inventory(out)==summary["outputs"],"Packed complete output tree changed")
    proof={"status":"RUNNING_LOADED_PUBLICATION","assets":[],"reservation":reservation,
      "current_context":current,"original_status":summary["original_terminal_status"],
      "publication_qualified_as_success":successful,"source_integrity_qualified":source["qualified"],
      "raw_terminal_bytes_unchanged":True,"direct_plan_sha256":a.sha(out/PLAN),
      "complete_outputs":summary["outputs"],"waveform_samples_deliberately_removed":False,"accepted":False}
    a.write(transport/"publication.json",proof)
    previous=s.publisher.release
    s.publisher.release=s.evidence.only_reserved(ctx["group"],os.environ,s.release.api)
    primary=None
    try:
        for path in files:
            before=a.sha(path);receipt=s.publisher.publish(path,tag)
            a.require(a.sha(path)==before,"Loaded asset changed during publication")
            a.require(type(receipt["id"])is int and receipt["id"]>0,"Published asset ID missing")
            a.require(all(x["id"]!=receipt["id"]for x in proof["assets"]),"Published asset ID collision")
            proof["assets"].append(receipt);a.write(transport/"publication.json",proof)
        proof["status"]="PASS_COMPLETE_LOADED_EVIDENCE_PUBLICATION_ONLY"
    except BaseException as error:
        primary=error;proof.update(status="FAIL_LOADED_PUBLICATION",error=repr(error),traceback=traceback.format_exc())
    finally:
        s.publisher.release=previous
        try:a.write(transport/"publication.json",proof)
        except BaseException as error:
            proof["publication_receipt_save_error"]=s.error_record("publication_receipt",error)
            try:print(json.dumps({"unsaved_loaded_publication_receipt":proof},sort_keys=True),flush=True)
            except BaseException:pass
            if primary is None:primary=error
    if primary is not None:raise primary
    return proof
