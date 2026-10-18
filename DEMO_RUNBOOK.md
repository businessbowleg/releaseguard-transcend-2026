# ReleaseGuard — 2m30s judge-ready video plan

**Not a finished or recorded video.** Do not fabricate GitLab Duo sessions
or CI success screenshots. This plan becomes executable once the hackathon
organizer provisions the account's GitLab project.

## Before recording: evidence prerequisites

1. GitLab public project URL exists within the hackathon workspace.
   Configure the custom flow ONLY for assigning it as a merge-request
   REVIEWER, where the trigger goal is the numeric merge-request IID.
2. The .gitlab-ci.yml pipeline has executed in that project's actual history.
3. The Duo custom flow is saved, validated and has completed a genuine session.
4. An independent human approval checkpoint is visible in that session.
5. The pipeline produces the release_decision.json and the HTML static artifact.
6. One adversarial pipeline test demonstrates NO_GO for a genuine failing check.
7. Never reveal personal credentials, private GitLab project names, or ATLAS.

## Proposed 2m30s sequence

0:00–0:16 — Problem/hook
Visual: Short animated title over the *actual* evidence dashboard.
Narration: "Generating code is fast. Trusting it is harder. How do you know
an agent's release recommendation is backed by independent evidence?"

0:16–0:37 — GitLab merge request
Visual: Authenticated GitLab project and example merge request.
Narration: "A real GitLab merge request triggers our release-review flow.
Two agents independently inspect change risks and required tests."

0:37–1:04 — Duo agent execution
Visual: Genuine GitLab Duo Sessions entry and first investigator result.
Navigate to the independent assessor result. Do not replace it with
illustrative transcripts.
Narration: "One agent investigates. A second assessor challenges
the first conclusions rather than rubber-stamping them."

1:04–1:27 — Human review and one restricted action
Visual: Genuine HumanInputComponent pause showing the EXACT GitLab project,
target MR, independently verified findings, and Approve/Reject/Modify.
After genuine approval, show the newly posted evidence-labelled MR review note.
Never present a blank approval screen as proof of governed review.
Narration: "The human can permit exactly one MR review note,
modify the request, or reject it. There is no production autopilot."

1:27–1:56 — GitLab CI evidence
Visual: Actual six-stage pipeline and job artifacts.
Narration: "The tests, security and license checks run as normal CI jobs.
Only recorded artifacts and exact commit/pipeline identities count as
evidence for the deterministic release gate."

1:56–2:17 — Failure demonstration
Visual: Genuine GitLab CI pipeline run for a separate intentionally failing
unit-test branch. Show the actual failed test job, and verify that evidence
collection and staging did NOT run. Then return to the real green pipeline.
Never assert a NO_GO JSON was produced if downstream jobs were skipped.
Narration: "A failed test blocks downstream evidence and release admission.
The absence of a release decision is fail-closed, not silent approval."

2:17–2:30 — Evidence dashboard/close
Visual: Dashboard produced from actual GitLab pipeline artifacts; open
source MIT README.
Narration: "The result is a readable evidence trail—no automatic
production deployment, and no claims of safety without proof."

## Practical recording

- Use a real browser recorder; 1920x1080, 30fps, under three minutes.
- AI narration is fine when labeled accurately, but do not create false
  footage, fake messages or fake success.
- Prefer continuous browser movement; crop private data; keep timestamps.
- Publish to **public YouTube**; a GitHub video alone is not sufficient.
- Use only footage and content you are authorized to share.

## Submission fields

Category: Path A / Start Fresh / Assisted.
GitLab repository: [VERIFIED_PROJECT_URL]
Duo session: [VERIFIED_SESSION_URL]
Passing CI pipeline: [VERIFIED_PIPELINE_URL]
YouTube public URL: [VERIFIED_YOUTUBE_URL]
Devpost URL: [VERIFIED_DEVPOST_URL]

Completion and prize status remain unverified until URLs exist.
