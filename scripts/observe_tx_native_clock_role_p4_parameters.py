#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exactly derive observer using independently qualified four-p4 history."""
import hashlib
from pathlib import Path
import tx_native_clock_role_p4_history as p4
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/"scripts/observe_tx_native_clock_role_parameters.py"
ORIGINAL_SHA="03fc06ae693924f63f5b3c4f758d43926df66fc166050a0776b1a8729ab4f7c4"
EDITS=[
  [
    "KINDS={\"a\":\"pre\",\"b\":\"pre\",**{f\"p{stride}_{i}\":\"pre_low\"for stride in (4,8,16)for i in range(stride)},\"f\":\"final\"}",
    "KINDS=dict(p4.KINDS)"
  ],
  [
    "need(emitters==719,\"actual mux emitters\",719,emitters)",
    "need(emitters==863,\"actual mux emitters\",863,emitters)"
  ],
  [
    "elif name==\"wrong_low_tail\":dev(\"p4_0\",\"tail\")[\"parameters\"][\"nx\"]=8.",
    "elif name==\"wrong_low_tail\":dev(\"p8_0\",\"tail\")[\"parameters\"][\"nx\"]=8."
  ],
  [
    "    blocks=inspect_native(g);bad=mismatches(blocks)",
    "    original_g=g;g,kind_transition=p4.bind(g)\n    blocks=inspect_native(g);bad=mismatches(blocks)"
  ],
  [
    "    try:frozen.bind(g)",
    "    try:frozen.bind(original_g)"
  ],
  [
    "     \"catalog\":catalog,\"blocks\":blocks,",
    "     \"kind_transition\":kind_transition,\"catalog\":catalog,\"blocks\":blocks,"
  ]
]
def derive():
    raw=ORIGINAL.read_bytes();assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    source=raw.decode()
    for before,after in EDITS:
        assert source.count(before)==1,before
        source=source.replace(before,after,1)
    recovered=source
    for before,after in reversed(EDITS):
        assert recovered.count(after)==1,after
        recovered=recovered.replace(after,before,1)
    assert recovered==raw.decode()
    return source
ns={"__file__":str(ORIGINAL),"__name__":"p4_derived_observer","p4":p4}
exec(compile(derive(),str(ORIGINAL)+"#four-p4-history","exec"),ns)
mismatches=ns["mismatches"];source_catalog=ns["source_catalog"];verify_original_failure=ns["verify_original_failure"]
def controls():
    history=p4.controls();original=ns["controls"]()
    return {**original,"p4_history_controls":history}
def main():ns["main"]()
if __name__=="__main__":main()
