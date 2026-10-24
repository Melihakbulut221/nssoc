#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Recover exact native tree device provenance for remaining headroom failures."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-tree-device-map'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir();reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],physical_change=False,accepted=False,serial_phy_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        dest=OUT/'source'
        prior,proof=reports.restore_report('tx-driver-headroom-physical',38929031066,
            '81910cf6e44471e82d0f337bb886f37c404b943337cfb088185877fa31a6918c',
            '6252ca833dfb6bf118f7691141d07e2cd89163da4d74da74a081236ec272e108',
            dest,('actual-tree-binding.json',))
        assert prior['status']=='COMPLETE_EXACT_CAPTURE_REPLAY_AND_HBT_MINIMA_NOT_PHY_ACCEPTANCE' and prior['source_unchanged']
        assert prior['all_original_engineering_fields_reproduced'] and prior['missing_current_probe_control']=='REJECTED'
        binding=dest/'actual-tree-binding.json';assert sha(binding)=='f54124fa051b49a32f0c3837ef8f771e6cda3ea9aba18417ba5cc932e856c3b9'
        data=json.loads(binding.read_text());assert len(data['devices'])==162
        # Publish native names/parameters/terminal bindings without assuming that
        # sequential native IDs imply a schematic role or ordering.
        result['source']=proof;result['native_binding']=data
        result['source_unchanged']=all(sha(dest/n)==v['sha256'] for n,v in proof['restore']['selected_files'].items())
        assert result['source_unchanged']
        result['status']='COMPLETE_EXACT_NATIVE_TREE_BINDING_INVENTORY_NOT_CAUSAL_OR_PHY_ACCEPTANCE'
        print(json.dumps(dict(status=result['status'],device_count=len(data['devices']),device_container=type(data['devices']).__name__),indent=2))
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
