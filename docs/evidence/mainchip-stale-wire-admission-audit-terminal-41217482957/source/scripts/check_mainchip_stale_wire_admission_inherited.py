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

PHASE_KEY="NSSOC_BULK_PHASE"
PHASE_VALUES=frozenset(
    name for kind,name,seconds in original_controls.inner.PHASE_COMMANDS.values()if kind=="native"
)|{"antenna-restore-audit","failure-restore-plan","failure-restored-audit"}

def with_fixture_phase(callback,env=None):
    """Restore only the inherited synthetic lifecycle's documented phase key."""
    env=os.environ if env is None else env
    before=dict(env);missing=object()
    try:return callback()
    finally:
        after=dict(env)
        changed={key for key in set(before)|set(after)if before.get(key,missing)!=after.get(key,missing)}
        # Restore our one owned fixture key even if an unrelated mutation must be refused.
        if PHASE_KEY in before:env[PHASE_KEY]=before[PHASE_KEY]
        else:env.pop(PHASE_KEY,None)
        assert not changed-{PHASE_KEY},("unexpected environment mutation",sorted(changed-{PHASE_KEY}))
        if PHASE_KEY in changed:
            assert after.get(PHASE_KEY)in PHASE_VALUES,"unknown synthetic lifecycle phase"
        assert dict(env)==before,"actual environment changed by source-control adapter"

def main():
    return with_fixture_phase(source_main)

if __name__=="__main__":main()
