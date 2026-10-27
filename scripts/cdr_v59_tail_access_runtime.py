#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Load exact previously qualified ownership and launcher code; no new supervisor."""
import ast
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

SUPERVISOR="docs/evidence/cdr-v59-mim-qualified-process-supervisor-20261025.py"
SUPERVISOR_SHA="e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b"
SAMPLER="docs/evidence/cdr-v59-tail-qualified-memory-sampler-20261026.py"
SAMPLER_SHA="55fb9a3ba9a049c509b629e8638a688b5f827316485f9fd89cd5a8888804df07"
PROBE="scripts/check_cdr_v59_mim_runtime.py"
WRITER="scripts/cdr_v59_mim_admission.py"
WRITER_SHA="a985d8bf1c94c6a3ba3d4f19c24193f35598a883eab56a52ed6de86ff98c14e5"

def raw(root,path,expected):
    file=root/path
    assert file.is_file() and not file.is_symlink()
    text=file.read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==expected,path
    return file,text,ast.parse(text)

def supervisor(root,out,trace,gate,expected_sampler):
    gate()
    file,text,tree=raw(root,SUPERVISOR,SUPERVISOR_SHA)
    selected=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            if isinstance(node,ast.Import) and any(a.name=="check_pcie_gen12_training_records" for a in node.names):continue
            selected.append(node)
        elif isinstance(node,ast.Assign):
            names={n.id for n in node.targets if isinstance(n,ast.Name)}
            if names & {"ROOT","OUT","TRACE","METHOD","ORIGINAL"}:continue
            selected.append(node)
        elif isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name not in ("pins","main"):
            selected.append(node)
    module=types.ModuleType("cdr_tail_qualified_supervisor")
    module.__file__=str(file)
    module.__dict__.update(ROOT=root,OUT=out,TRACE=trace,pins=gate)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(file),"exec"),module.__dict__)
    assert module.SECONDS==1200 and module.MIN_AVAILABLE_KIB==2097152 and module.MAX_GROUP_RSS_KIB==10485760
    assert expected_sampler==SAMPLER_SHA
    sampler_file,_,_=raw(root,SAMPLER,expected_sampler)
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:
        spec=importlib.util.spec_from_file_location("cdr_tail_qualified_memory_sampler",sampler_file)
        sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
        sampler.install(module)
    finally:sys.dont_write_bytecode=previous
    assert module.memory_snapshot.bounded_fresh_rss_adapter is True
    return module

def launcher(root,gate,expected_probe):
    gate()
    file,text,tree=raw(root,PROBE,expected_probe)
    module=types.ModuleType("cdr_tail_qualified_launcher")
    module.__file__=str(file)
    writer_file,_,writer_tree=raw(root,WRITER,WRITER_SHA)
    writer_nodes=[n for n in writer_tree.body if isinstance(n,ast.FunctionDef) and n.name=="write"]
    assert len(writer_nodes)==1
    writer_scope={"json":json}
    exec(compile(ast.Module(body=writer_nodes,type_ignores=[]),str(writer_file),"exec"),writer_scope)
    module.admission=types.SimpleNamespace(ROOT=root,methods=gate,write=writer_scope["write"])
    selected=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            if isinstance(node,ast.Import) and any(a.name=="cdr_v59_mim_admission" for a in node.names):continue
            if isinstance(node,ast.ImportFrom) and node.module=="cloud_cdr_v59_binding_rc":continue
            selected.append(node)
        elif isinstance(node,ast.Assign):selected.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name!="main":selected.append(node)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(file),"exec"),module.__dict__)
    assert module.SUPERVISOR_SHA==SUPERVISOR_SHA
    return module
