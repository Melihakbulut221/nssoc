#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Keep historical fallback tests isolated from actual later-checkpoint authorization."""
import copy,hashlib,json,os,subprocess
from unittest.mock import patch
import cloud_pll_rhi120_c8_sparse as controller
import cloud_pll_rhi120_c8_sparse_resume as resume
REPO='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 # This entrypoint is controls-only. The native job runs the untouched controller
 # in a separate process and never imports this module or installs the fixture.
 original=resume.fallback_authorization
 message='Another native attempt exists; inspect its capsule instead of replaying initial'
 try:original()
 except AssertionError as e:assert str(e)==message,'Unexpected authorization failure';blocked=str(e)
 else:raise AssertionError('Stale initial fallback remains enabled after durable sparse progress')
 run=api('actions/runs/39941648965');job=api('actions/jobs/120374455456')
 annotations=api('check-runs/120374455456/annotations')
 artifacts=api('actions/runs/39941648965/artifacts')
 r=subprocess.run(['gh','api',REPO+'releases/tags/cloud-results-39941648965-1-pll-rhi120-c8-native-recovery'],capture_output=True,text=True)
 assert r.returncode!=0
 error=json.loads(r.stdout);assert str(error.get('status'))=='404'and error.get('message')=='Not Found'
 audit=dict(run=run,job=job,annotations=annotations,artifacts=artifacts,release_exists=False)
 proof=resume.fallback_gate(**audit)
 # Prove saved native method identity is exact, independently of the historical
 # fallback fixture. No native method change or compatibility exception is added.
 data=subprocess.check_output(['gh','api',REPO+'releases/assets/669929123','-H','Accept: application/octet-stream'])
 assert hashlib.sha256(data).hexdigest()=='3ff36c73fdcc52aa4096090d8d156e52e6173da3a837fa38ff5de81a6b0406bb'
 saved=json.loads(data);_,current=resume.source_contract()
 assert saved['method_hashes']==current
 assert resume.verify_resume_methods(saved,current)['mode']=='exact-current-RHI120-sparse'
 source=api('actions/runs/39967627133')
 spec=dict(run=39967627133,attempt=1,stage='sparse',
  summary_sha256='3ff36c73fdcc52aa4096090d8d156e52e6173da3a837fa38ff5de81a6b0406bb',
  parts_sha256='7bbe164c01ec4680d551aea120807503c137c03a7daf3cccd52130d6afe04b15')
 resume.source_gate(source,spec,saved)
 original_tests=controller.controls()
 # Run every original 11 fallback corruption and initial method fixture test
 # against the same real historical failure metadata. This fixture authorizes
 # no workflow dispatch and does not survive this controls-only context.
 with patch.object(resume,'fallback_authorization',lambda:(copy.deepcopy(proof),copy.deepcopy(audit))):
  all_resume_tests=controller.resume_controls()
 assert resume.fallback_authorization is original
 assert len(all_resume_tests['terminal_publication_fallback']['rejected'])==11
 try:original()
 except AssertionError as e:assert str(e)==message
 else:raise AssertionError('Historical fixture leaked into live authorization')
 print(json.dumps(dict(status='PASS_ALL_ORIGINAL_CONTROLS_WITH_ISOLATED_HISTORICAL_FALLBACK_AND_LIVE_STALE_SOURCE_REJECTION',
  original=original_tests,resume=all_resume_tests,live_stale_initial_rejected=blocked,
  saved_sparse_method_map_exact=True,all11_original_fallback_corruptions_preserved=True,
  historical_fixture_confined_to_test_context=True,production_authorizer_unchanged=True,
  native_process_activated=False,full_capture_accepted=False)))
if __name__=='__main__':main()
