"""Source-only control context for a separate real GitHub branch."""
import os
from types import SimpleNamespace
import mainchip_stale_wire_routing as stale
import cloud_mainchip_bulk_postdrt_antenna as original_host
import check_mainchip_bulk_postdrt_integration as original_controls

BRANCH="codex/mainchip-stale-wire-admission-controls"
source_context=stale.clone(original_host.context,BRANCH=BRANCH)
source_host=SimpleNamespace(**vars(original_host))
source_host.context=source_context
source_main=stale.clone(original_controls.main,host=source_host)

def main():
    before=dict(os.environ)
    try:return source_main()
    finally:
        assert dict(os.environ)==before,"actual environment changed by source-control adapter"

if __name__=="__main__":main()
