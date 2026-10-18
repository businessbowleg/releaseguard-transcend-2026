# ReleaseGuard — Evidence-first GitLab Duo release governance

**Status: independently tested local candidate, NOT yet entered or validated on GitLab.**

ReleaseGuard demonstrates a governed AI DevSecOps workflow: investigate an MR,
independently check evidence, run security/licensing/testing gates, produce a
staging-candidate artifact, and obtain human acknowledgement. AI conclusions
are advisory; the release decision is deterministic.

Created for the **GitLab Transcend Life After Code** hackathon (October 2026).
This is an original, standalone MIT-licensed project and does not contain any
proprietary ATLAS code, internal infrastructure configurations or credentials.

## What it solves

Teams increasingly generate code faster than they verify it. Automated agents
can accidentally overstate passing tests, overlook secret leaks, or treat a
successful build as permission to deploy. ReleaseGuard makes these boundaries
visible: evidence is explicit, independent judgments are required, and a
staging candidate is never confused with a production deployment.

## Core controls

- Two proposed GitLab Duo agents, independent investigator and assessor,
  plus HumanInputComponent review (candidate flow YAML).
- Deterministic stage checks for tests, security, licensing, documentation
  and a written rollback plan.
- Exact source commit and evidence digests; rejecting paths that escape the
  repository or point to symlinks, sensitive files or embedded secrets.
- Three-way stage statuses: PASS, FAIL, UNVERIFIED. Missing evidence = NO_GO.
- Strict proposal schema. No action named deploy-production is accepted.
- Human HMAC acknowledgement (only for staging candidates), never production.
- GitLab CI stages for testing, secret scanning, license checks, evidence
  collection, gating and a static, non-deployed staging artifact.

## Local test

No paid service, external API, model download or GPU required.

    python3 -m unittest discover -s tests -v
    python3 ci_security.py
    python3 ci_evidence.py
    python3 releaseguard.py check --root . --proposal release_proposal.json --evidence release_evidence.json --output release_decision.json
    python3 stage_preview.py

The local evidence file MUST say LOCAL_FIXTURE_NOT_GITLAB and is not a live
GitLab Duo result. Real pipeline results require a project provisioned by
GitLab plus actual GitLab CI execution, with visible job and session history.

An adversarial demonstration:

1. In an isolated test fixture, mark security FAIL. The judge returns NO_GO.
2. Remove a required evidence stage. The judge refuses the schema.
3. Attempt an autonomous production action. The proposal is refused.
4. Provide valid local fixture evidence. The judge can issue STAGING_CANDIDATE
   with production_permitted=false and deployment_performed=false.
5. Have a separate human acknowledge staging evidence; this is not a deploy.

## GitLab Duo integration — unverified until onboarding

The candidate flow is at .gitlab/duo/flows/releaseguard.flow.yml.
Import it through GitLab project > AI > Flows > New flow, inspect and validate
the UI schema, then enable the flow for the project under its safe trigger.
The flow uses real GitLab Duo agents and a HumanInputComponent, but its YAML
file alone is NOT proof those agents ran. If the GitLab UI rejects any
configuration, correct it against current official docs before claiming success.

After contributor onboarding, import this repository into the provided
GitLab hackathon project. Run the GitLab pipeline, trigger Duo on an example
merge request, and capture authentic visible CI history and AI Sessions.

## Key limits

- No production deployment or rollback is implemented.
- The staging_preview stage creates a static artifact; it does not deploy.
- This minimal built-in regex scanner is not a substitute for enterprise SAST.
- Pipeline-bound evidence depends on protected, genuine GitLab CI jobs;
  local fixture claims are never treated as remote proof.
- The working GitLab Duo agent run, public GitLab repo, <3-minute public
  YouTube video and Devpost entry are still missing.
- Prize eligibility and a winning probability cannot be guaranteed.

## Competition

Official site: https://gitlab-transcend.devpost.com/
Official rules: https://gitlab-transcend.devpost.com/rules
GitLab access onboarding: https://contributors.gitlab.com/transcend-hackathon

The submission deadline is October 27, 2026 at 13:00 UTC
(9:00 AM Eastern Daylight Time). The binding rules take precedence
over other event pages if times differ.

Requirements include actual GitLab Duo Agent Platform use, visible GitLab CI
pipeline history, public MIT-licensed GitLab source, a public YouTube video
under three minutes and a completed Devpost submission.

No money was spent and no prize or client payment has been obtained.
