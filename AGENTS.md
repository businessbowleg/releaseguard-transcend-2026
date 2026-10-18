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
