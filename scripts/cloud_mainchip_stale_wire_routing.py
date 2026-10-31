"""Exact inherited cloud execution with scoped stale-wire/clock census adapters."""
import sys
from types import SimpleNamespace
import cloud_mainchip_saved_diode_routing as old
import mainchip_stale_wire_routing as a

def perform(ctx,proof,evidence):
    a.source_gate()
    proxy=SimpleNamespace(**vars(old.c))
    proxy.create_argv=lambda *args:a.hosted_argv(old.c.create_argv,*args)
    derived=a.host_perform(old.perform,source_gate=a.source_gate,MANIFEST=a.MANIFEST,c=proxy)
    return derived(ctx,proof,evidence)

def main():
    return a.clone(old.main,perform=perform)()

if __name__=="__main__":main()
