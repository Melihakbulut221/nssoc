#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact saved native observations for derived geometry finalization."""
import re
PREFIX="docs/evidence/mainchip-saved-repair-audit-terminal-41187928413/"
PRODUCER=dict(run=41187928413,source="b8aa8fb2da6cc15a4660f96e8f2115efc5d9379e",
 release=429832753,tag="cloud-results-41187928413-1-mainchip-bulk-postdrt-antenna",files=1261,
 archive=dict(bytes=46137991,sha256="5881606e3ba90e34a13b9b8871c7ebd7f04e3cae5e919f08b6b191b94aebf3f1"))
BASE={
 "bulk-postdrt-inner-result.json",
 "bulk-postdrt-antenna/saved-delta.json",
 "bulk-postdrt-antenna/saved-delta-summary.json",
 "bulk-postdrt-antenna/saved-native-master-identity.json",
 "bulk-postdrt-antenna/saved-before-wire-index.json",
 "bulk-postdrt-antenna/saved-after-wire-index.json",
 "bulk-postdrt-antenna/saved-wire-compare-failure.json"}
def require(ok,message):
    if not ok:raise ValueError(message)
def select(files):
    require(BASE<=set(files),"complete saved core records")
    selected=set(BASE)
    for label in("before","after"):
        pattern=r"bulk-postdrt-antenna/saved-"+label+r"-wire-[0-9a-f]{64}\.json"
        names={name for name in files if re.fullmatch(pattern,name)}
        require(len(names)==608,"all608 "+label+" native wire observations")
        selected|=names
    require(len(selected)==1223,"exact saved input scope")
    return selected
