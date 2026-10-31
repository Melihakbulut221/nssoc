#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit host-admitted canonical-view entry; standalone core authority stays disabled."""
import argparse,os,sys
from pathlib import Path
import cdr_via2_m3_canonical_view_admission as a
q=a.q;ROOT=a.ROOT;require=a.require

def execute(mode,reference,physical,out,preflight):
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.authorize_native(ctx,c)
    require(mode in('prepare','planes','recover','verify'),'bounded view-only mode')
    require(out.is_absolute()and out.resolve()==out and out==preflight.parent/'native'and out.is_relative_to(ROOT/'hw/soc/out'),'owned exact native output')
    a.native_preflight(preflight,ctx,c,reference,physical)
    for name,pin in c['core']['files'].items():require(q.file_pin(q.regular(ROOT,name))==pin,'exact reviewed core source')
    import cdr_via2_m3_canonical_core as core
    require(Path(core.__file__).resolve()==ROOT/c['core']['module_path'],'core import not shadowed')
    config=q.decode(q.regular(ROOT,c['core']['config_path']).read_bytes());core.validate_config(config)
    workspace=out/'view';view=workspace/'candidate'
    if mode=='prepare':
        rm,_=a.metadata(c,'reference');pm,_=a.metadata(c,'physical')
        actual=core.prepare(reference,physical,workspace,ROOT,config,rm['files'],pm['files']);require(actual==view,'exact fresh view path')
    elif mode in('planes','recover'):core.derived(mode,view,ROOT,config)
    else:
        result=core.verify(reference,physical,view,workspace,ROOT,config)
        require(result['status']==c['core']['qualification_status']and result['native_view_executed']is True,'actual full canonical-view result')
    a.native_preflight(preflight,ctx,c,reference,physical);a.source_guard(ctx)

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['prepare','planes','recover','verify'],required=True)
    for name in('reference','physical','output','preflight'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();execute(args.mode,args.reference,args.physical,args.output,args.preflight)
if __name__=='__main__':main()
