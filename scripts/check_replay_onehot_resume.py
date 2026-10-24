#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-binding controls only; fixture success is never native CAD evidence."""
import copy
import json
import os
from cloud_replay_onehot_postcts import (BOOT_RUN, BOOT_HEAD, PROTOCOL_RUN,
    PLACEMENT_STATUS, require_candidate, relative)
from cloud_chunked_results import controls as archive_controls


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    spec = dict(run=BOOT_RUN, head=BOOT_HEAD, protocol_run=PROTOCOL_RUN,
                bank_proof_and_protocol_verified=True, artifact=1, zip_sha256="a" * 64)
    fixture = dict(status=PLACEMENT_STATUS, sources_unchanged=True, returncode=0,
        source_head="b" * 40, cts_state="run/27-openroad-cts/state_out.json",
        outputs={"run/27-openroad-cts/state_out.json": "c" * 64},
        preparation={"macros": {str(n): {} for n in range(20)}},
        boot_source=dict(source_spec=spec, source_run=BOOT_RUN, source_head_original=BOOT_HEAD,
            source_artifact=1, original_zip_sha256="a" * 64,
            gate_result=dict(passed=True, sources_unchanged=True),
            configuration=dict(RF_CORRPRE=1, RF_SYNPRE=0, SOC_SRAM_MBIST=1, SOC_ETH_MBIST=1,
                CORE_REQ_REG=0, CORE_WB_STAGE=0, SOC_PCIE_PROFILE="packet-async", interface_profile="full")))
    assert require_candidate(fixture, "b" * 40) == spec
    mutations = [
        (("boot_source", "source_spec", "run"), 38994926932),
        (("boot_source", "source_spec", "head"), "471a966524f68c18b9801488bfc512bee2dc2de0"),
        (("boot_source", "source_spec", "protocol_run"), 39013401471),
        (("boot_source", "source_spec", "bank_proof_and_protocol_verified"), False),
        (("boot_source", "source_spec", "zip_sha256"), "0" * 64),
        (("boot_source", "gate_result", "passed"), False),
        (("boot_source", "configuration", "SOC_ETH_MBIST"), 0),
        (("boot_source", "configuration", "CORE_WB_STAGE"), 1),
        (("source_head",), "d" * 40),
        (("sources_unchanged",), False),
        (("returncode",), 1),
        (("cts_state",), "run/27-openroad-cts/../../state_out.json"),
        (("cts_state",), "run/28-other-step/state_out.json"),
    ]
    for keys, value in mutations:
        bad = copy.deepcopy(fixture)
        target = bad
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        try:
            require_candidate(bad, "b" * 40)
        except AssertionError:
            continue
        raise AssertionError("Source mutation accepted: " + ".".join(keys))
    for path in ("/tmp/escape", "../escape", "run/../../escape", ""):
        try:
            relative(path)
        except AssertionError:
            continue
        raise AssertionError("Unsafe saved path accepted")
    from cloud_replay_onehot_postcts import require_same_proofs
    prior = dict(run=BOOT_RUN, proofs=[1,2,3], source_hashes={"rtl": {"old": "a"*64}})
    now = dict(run=BOOT_RUN, proofs=[1,2,3], source_hashes={"rtl": {"new": "a"*64}})
    require_same_proofs(prior, now)
    for field in ("source_hashes", "proofs", "run"):
        bad = copy.deepcopy(now)
        bad[field] = {"rtl": {"new": "b"*64}} if field == "source_hashes" else [] if field == "proofs" else 1
        try: require_same_proofs(prior, bad)
        except AssertionError: pass
        else: raise AssertionError("Altered revalidation accepted: " + field)
    print(json.dumps(dict(status="PASS_SOURCE_BINDING_AND_ARCHIVE_CONTROLS_ONLY",
        synthetic_source_fixture=True, source_mutations_rejected=len(mutations),
        invalid_paths_rejected=4, archive=archive_controls(), physical_acceptance=False)))


if __name__ == "__main__":
    main()
