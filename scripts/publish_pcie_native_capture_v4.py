#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reconcile uncertain uploads before bounded, non-overwriting retries.

V3's transport children, byte comparisons, deadlines and process ownership
remain exact. A timed-out upload followed by confirmed absence may be retried;
an existing ambiguous, incomplete or different asset is always an error.
"""
import hashlib
import inspect
from pathlib import Path

import publish_pcie_native_capture_v3 as previous

PREVIOUS_SHA = "b2ea742c31c20c19bf02b30b3b1954342d5aa73772732dc69c8f170f46e1fa0f"
pin, save = previous.pin, previous.save
lifecycle = previous.lifecycle
OWNER_SHA = previous.OWNER_SHA
REPO, TAG = previous.REPO, previous.TAG
IntegrityError, TransportError = previous.IntegrityError, previous.TransportError


class Client(previous.Client):
    def __init__(self, *args, **kwargs):
        if pin(previous.__file__)["sha256"] != PREVIOUS_SHA:
            raise IntegrityError("Frozen publisher V3 changed")
        super().__init__(*args, **kwargs)
        self.reconciliations = []

    def resolve_asset(self, tag, row):
        """Never clobber; distinguish uncertain transport from integrity failure."""
        expected = {key: row[key] for key in ("bytes", "sha256")}

        def lookup():
            self.check()
            found = [asset for asset in self.api(f"releases/tags/{tag}")["assets"]
                     if asset["name"] == row["name"]]
            if len(found) > 1:
                raise IntegrityError("Ambiguous immutable asset")
            if found:
                previous.validate_asset(found[0], row)
                return found[0]
            return None

        def persist():
            save(self.directory / "reconciliation.json", self.reconciliations)

        successful_upload = False
        for attempt in range(1, self.attempts + 1):
            self.check()
            if pin(row["path"]) != expected:
                raise IntegrityError("Local capture changed before upload reconciliation")
            resolution = dict(name=row["name"], attempt=attempt, status="RUNNING",
                              successful_upload_previously_observed=successful_upload)
            self.reconciliations.append(resolution)
            persist()
            try:
                found = lookup()
                if found is not None:
                    resolution.update(status="RESOLVED_EXISTING", asset_id=found["id"])
                    return found
                uncertain = permanent = None
                # A successful upload with delayed visibility needs metadata
                # retries only. It must not be submitted a second time.
                if not successful_upload:
                    try:
                        self.upload(tag, row["path"])
                        successful_upload = True
                        resolution["upload"] = "SUCCESS"
                    except TransportError as error:
                        uncertain = error
                        resolution["upload"] = "UNCERTAIN_TRANSPORT"
                    except RuntimeError as error:
                        # An immutable-name race may be reported as HTTP422.
                        # Reconcile it, but never retry a permanent absent error.
                        permanent = error
                        resolution["upload"] = "PERMANENT_ERROR"
                self.check()
                found = lookup()
                if found is not None:
                    resolution.update(status="RESOLVED_AFTER_UPLOAD", asset_id=found["id"])
                    return found
                if permanent is not None:
                    raise permanent
                resolution["status"] = "ABSENT_AFTER_SUCCESS" if successful_upload else "ABSENT_AFTER_UNCERTAIN_UPLOAD"
                if attempt == self.attempts:
                    if uncertain is not None:
                        raise TransportError("Upload retry budget exhausted; asset remains absent") from uncertain
                    raise IntegrityError("Successful upload remains absent after bounded reconciliation")
            except BaseException as error:
                resolution.update(status="FAILED", error=repr(error))
                raise
            finally:
                persist()
            self.stop.wait(min(self.backoff * 2 ** (attempt - 1), 8.0))
        raise AssertionError("Unreachable reconciliation completion")


# Keep the complete V3 CLI, integrity checks and two download paths unchanged.
# This explicit byte bridge is independently testable and source-pinned.
if pin(previous.__file__)["sha256"] != PREVIOUS_SHA:
    raise IntegrityError("Frozen publisher V3 changed")
OLD_RESOLUTION = '''            found=[x for x in client.api(f"releases/tags/{a.tag}")["assets"] if x["name"]==row["name"]]
            if not found:
                try:
                    client.upload(a.tag,row["path"])
                except TransportError:
                    # An uncertain upload may have succeeded: inspect immutable state.
                    pass
                found=[x for x in client.api(f"releases/tags/{a.tag}")["assets"] if x["name"]==row["name"]]
            if len(found)!=1:raise IntegrityError("Missing/ambiguous asset after state reconciliation")
            asset=found[0];validate_asset(asset,row)'''
main_source = inspect.getsource(previous.main)
replacements = [
    (OLD_RESOLUTION, '            asset=client.resolve_asset(a.tag,row)'),
    ('publisher_revision=3,', 'publisher_revision=4,'),
    ('        record["explicit_stop"]=client.stop.is_set()',
     '        record["explicit_stop"]=client.stop.is_set()\n'
     '        record["upload_reconciliations"]=client.reconciliations\n'
     '        record["publisher_v3"]=pin(frozen_v3_path)'),
]
original_source = main_source
for before, after in replacements:
    if main_source.count(before) != 1:
        raise IntegrityError("Publisher main source bridge is no longer exact")
    main_source = main_source.replace(before, after)
BRIDGE = dict(original_sha256=hashlib.sha256(original_source.encode()).hexdigest(),
              modified_sha256=hashlib.sha256(main_source.encode()).hexdigest(),
              exact_replacements=replacements)
namespace = dict(vars(previous))
namespace.update(__file__=__file__, Client=Client,
                 frozen_v3_path=str(Path(previous.__file__).resolve()))
exec(compile(main_source, __file__ + ":main", "exec"), namespace)
main = namespace["main"]


if __name__ == "__main__":
    raise SystemExit(main())
