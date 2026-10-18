# ReleaseGuard: GitLab Duo Agent Operating Contract

This independent open-source hackathon prototype contains no proprietary ATLAS code.

Agents only investigate and propose. They are NOT an independent judge.
The deterministic releaseguard.py gate examines exact changes and recorded
evidence. Missing or contradictory evidence must block stage admission.

Rules for Duo:
- Research the actual merge request, commits, licensing and CI history.
- Distinguish independently verified facts from guesses.
- Use PASS, FAIL or UNVERIFIED; never invent passing jobs.
- Read-only GitLab tools only. No merge, deploy, push, payment, or auto-promotion.
- The Human Input gate can acknowledge STAGING CANDIDATE only.
- No role may bypass or delete evidence checks.
- Never disclose secrets, company documents or private ATLAS assets.
- A local test fixture is NOT GitLab Duo execution evidence.

Until the GitLab workspace is provisioned and the custom flow is validated and
executed there, the GitLab Duo integration is NOT VERIFIED.

Run automated tests with Python unittest discovery. Do not run on ATLAS production.

## Opt-in reviewed comment

When the GitLab Duo HumanInputComponent genuinely returns APPROVE, only the
approved_audit_publisher component may post one review summary to the specific
merge request, using the official create_merge_request_note tool. It must
first read the existing note history via gitlab_api_get and refuse to write if
the lookup cannot be completed or the marker already exists. This is a
candidate integration: real GitLab validation is still outstanding.

Human chat messages outside an actual workflow approval event never authorize
the publisher; the executor must be reached through the approved route.


## Visible human decision contract

The owner gate must show the exact GitLab project ID, MR target, and
independent assessor's actual findings. A vague 'approve changes' prompt is
NOT acceptable. Approving means permission for at most one reviewed MR note,
not code edits, merging, deployment, or production promotion.

This custom flow is API-only and requires no repository clone.
Until GitLab's flow builder validates it and a genuine Session completes,
static YAML/test verification is not a functioning GitLab integration.
