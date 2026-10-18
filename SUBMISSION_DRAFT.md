# GitLab Transcend 2026 — ReleaseGuard submission (DRAFT, NOT SUBMITTED)

## Intended category and autonomy level

**Path A — Start Fresh. Assisted automation.** This is a new hackathon-period
project, not a preexisting ATLAS product. Deployment is optional under Path A.
The agents gather and assess evidence, CI performs independent controls,
and a human reviews the staging outcome. We do **not** claim Hands-off
autonomy, live production deployment, or that human approval actually deploys.

## Title

ReleaseGuard — Evidence-first governance for AI-generated code

## One-liner

Two independent GitLab Duo agents investigate a change, and an approval-gated
third agent may post a read-only review summary, while a deterministic
CI evidence gate refuses unsupported release claims, with human review before
staging acknowledgement.

## Inspiration

Software delivery is gaining speed with AI coding agents, but trust often
depends on whether an agent *said* tests passed. A release workflow should
know the difference between an AI assertion and actual evidence. ReleaseGuard
puts that distinction directly into the post-code lifecycle.

## What it does

ReleaseGuard coordinates an AI investigator and independent AI assessor to
review a GitLab merge request and its risks. After an explicit human approval,
a third restricted agent can post one evidence-labelled MR audit comment.
No automated merge or deployment is permitted. A GitLab CI pipeline then checks
automated tests, source security, MIT licensing, documentation, rollback
planning, and a structured provenance report. The deterministic gate returns
NO_GO when evidence is absent or fails. If all checks pass, it produces a
STAGING_CANDIDATE verdict, without performing deployment. A human checkpoint
can acknowledge or reject the proposal. The outcome is presented in a
read-only browser-accessible CI artifact dashboard.

## How it works

- GitLab Duo Agent Platform candidate custom flow: investigator -> independent
  assessor -> HumanInputComponent -> restricted MR audit-comment publisher.
  Only the post-approval publisher is given the note-writing tool.
- Python standard library policy engine; no external model needed by the
  deterministic judge and no paid inference required for local unit tests.
- GitLab CI YAML: unit tests -> security -> license -> evidence -> independent
  gate -> staging artifact.
- GitLab pipeline identity matching and fail-closed provenance checks.
- JSON decision digests; source path / symlink checks; refusal of unsafe
  actions and suspected secrets.
- Static dashboard distinguishing LOCAL TEST FIXTURE from declared GitLab CI,
  without calling either one a production deployment.

## Challenges

AI can confidently describe results that were never verified. Local fixtures
can also mimic real pipeline outputs. We separated recorded source evidence
from analysis, tied decisions to commits and pipeline context, and labeled
local fixtures prominently. Environment variables alone are not
cryptographic proof; real GitLab history is the final authority.

## Accomplishments VERIFIED LOCALLY AS OF OCTOBER 18

- 37 passing Python tests.
- Successful no-dependency secret scan.
- End-to-end local fixture evidence audit and static dashboard.
- Desktop and mobile browser checks.
- Public MIT-licensed *GitHub preparation* repository.

## Required evidence NOT YET VERIFIED — fill only after genuine runs

- Public organizer-provisioned GitLab project URL: [TO BE VERIFIED]
- Actual GitLab CI passing pipeline URL and job history: [TO BE VERIFIED]
- Real GitLab Duo custom flow / session URL and approved MR note: [TO BE VERIFIED]
- Human acknowledgement checkpoint screenshot/session: [TO BE VERIFIED]
- Public YouTube video (<3 minutes) of the ACTUAL GitLab run: [TO BE RECORDED]
- Devpost published project URL: [NOT SUBMITTED]

Do not submit a rendered local fixture as evidence of actual GitLab Duo
execution. The current custom flow YAML is only a candidate until the
actual GitLab flow builder accepts and executes it.

## Technologies

GitLab, GitLab Duo Agent Platform (pending live integration),
GitLab CI/CD YAML, Python 3.12, HTML/CSS, JSON, SHA-256, HMAC, unittest.

## Differentiation

ReleaseGuard does not equate an LLM response with a deployment permission.
It makes incomplete evidence visible, enforces a separate deterministic
evaluation, and explicitly denies autonomous production promotion.

## Next steps

Integrate into the contest-provisioned GitLab workspace, validate the custom
flow, generate real flow sessions, run actual GitLab CI, record the concise
demo, and submit before October 27, 2026 at 13:00 UTC.

## Constraints

No paid services, no real payments, no production deployment, no proprietary
ATLAS code. Competitive prizes are uncertain. This project has won none.

## Resources

GitHub preparation source:
https://github.com/businessbowleg/releaseguard-transcend-2026

Competition:
https://gitlab-transcend.devpost.com/

Official flow reference:
https://docs.gitlab.com/user/duo_agent_platform/flows/custom_flows_schema/
