# ReleaseGuard rollback and recovery protocol

ReleaseGuard itself never deploys. Staging is represented by a CI artifact and
does not change an application, URL, customer, Git branch, or production system.

For any future adopter that integrates an external deployment:
1. Identify last independently verified good commit and immutable image digest.
2. Block promotion and notify the authorized owner.
3. Pause deployment changes before any rollback attempt.
4. Require a separate, authenticated production rollback permission policy.
5. Deploy a known-good pinned digest through the actual deployment system.
6. Probe health, provenance and financial truth; collect traceable evidence.
7. Preserve audit events for both failure and recovery.

These operational steps are a *plan*, not a validated deployment rollback.
The demo cannot initiate, execute or attest a real production rollback.
