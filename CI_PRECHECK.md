# ReleaseGuard: first GitLab workspace CI acceptance checklist

**Preparation only.** No organizer-provisioned workspace has yet been verified.
The GitHub repository is a preparation source, not the qualifying GitLab repo.

## When GitLab provisions the hackathon project

1. Record its exact organizer-provisioned project URL.
2. Import/push the public source from
   https://github.com/businessbowleg/releaseguard-transcend-2026
   into that project. Do not push proprietary ATLAS files.
3. Run the real GitLab CI/CD pipeline on the project's default branch.
4. Verify job history in the GitLab UI, not solely generated JSON.
5. Configure the READ-ONLY GitLab Duo flow in the project's UI,
   validate its YAML, and enable a safe merge request trigger.
6. Verify the authentic Duo Session and human review checkpoint;
   after actual approval, verify at most one MR note was posted on the
   intended MR, and no merge, deployment or cross-project write occurred.
7. Publish an actual under-three-minute demo to YouTube and submit Devpost.

## Expected CI jobs and records

- unit_tests -> attest_tests.json
- secret_scan -> attest_security.json and scan_results.json
- license_check -> attest_license.json
- documentation_check -> attest_documentation.json
- rollback_check -> attest_rollback.json
- create_evidence -> release_proposal.json, release_evidence.json, five proofs
- independent_gate -> release_decision.json
- staging_preview -> public/index.html and staging_receipt.json

The evidence step uses five explicit needs:artifacts dependencies and rejects
missing, inconsistent, or modified proof files. Collected proofs include
the upstream job ID, commit, pipeline ID, and source-file fingerprint.
These are NOT cryptographic attestation of GitLab infrastructure.
The genuine GitLab job history remains the authority.

The staging job downloads from BOTH independent_gate (decision) and
create_evidence (proposal and evidence). Without both, stage must fail.

## Required tests and checks

- [ ] Missing proof causes evidence collection failure.
- [ ] Wrong job, commit or pipeline causes evidence collection failure.
- [ ] Reused upstream job ID and changed file hash cause failure.
- [ ] Failed source security scan stops admission.
- [ ] Outside GitLab, --require-gitlab rejects local fixtures.
- [ ] Authentic pipeline and Duo sessions exist in the GitLab UI.
- [ ] The final dashboard is a CI artifact, not an app deployment.
- [ ] Production permission remains false.

## Simulation vs. execution

The local integration tests deliberately mock GitLab environment variables
in an isolated directory to exercise the runtime code path. They are not
real GitLab job output and must not be presented as such.

This remains a candidate until the organizer provisions the project,
Duo actually runs, and GitLab CI produces its visible history.


## Approval UI acceptance checks

- [ ] Actual gate displays the project ID, target MR, and entire assessor summary.
- [ ] Modify returns to the already-run assessor for revision, then pauses again.
- [ ] Reject terminates without any note.
- [ ] Approve is the ONLY route to the restricted note publisher.
- [ ] Publisher reads all MR notes and refuses duplicates or incomplete results.
- [ ] No agent can call GitLab merge, file modification or deployment tools.
- [ ] Duo executes with coding_environment: none (API-only review).
- [ ] Owner sees actual session evidence, not merely a local generated preview.

## Fresh runner dependency check

The unit test suite verifies the Duo flow with PyYAML, which is **not bundled**
with the minimal python:3.12-alpine image. GitLab CI installs precisely the
version specified in requirements-test.txt **before** running unittest.
Neither the gate, the scanner, nor the evidence collector depends on PyYAML.
If the runner has no PyPI access, mark the test job FAIL and do not fabricate
evidence or suppress the tests.

Do not count local or GitHub CI as actual GitLab execution.

## Exact merge request trigger contract

The ReleaseGuard Duo flow is designed for assigning the service account as
a REVIEWER to a specific merge request, not generic issue/comment/mention or
pipeline-event triggers. GitLab's context:goal then contains that MR's IID.
The flow must receive that positive decimal IID plus context:project_id.
When actual project access arrives, enable ONLY the reviewer-assignment event
and confirm the UI shows the exact numeric target. If an inappropriate trigger
is enabled, disable it and stop the demonstration until corrected.

Even the post-approval comment publisher must fetch the exact target MR, read
its note history and exit without writing when target identity is ambiguous.
This is currently a PROMPT CONTRACT; a real GitLab Duo session and notes API
inspection are required to verify enforcement.

## Genuine negative-case demonstration

Use a **separate non-default branch** with an intentionally failing,
harmless unit test. Its GitLab CI pipeline should fail in the test job and
prevent release evidence collection. A failed prerequisite may stop downstream
jobs, so do NOT claim a release_decision.json NO_GO artifact exists unless the
actual pipeline generated it. An absent decision is also a fail-closed outcome.
Do not merge the deliberately failing branch into main.
