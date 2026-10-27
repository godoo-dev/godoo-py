---
name: godoo-py-capture
description: Capture, triage, retrieve and reconcile godoo-py work in its GitHub issues, including incoming requirements, recovered findings and consequential delivery updates.
---

# Retain Python project work

Work belongs in https://github.com/godoo-dev/godoo-py/issues. Confirm the selected
checkout's `git remote get-url origin` and `gh repo view godoo-dev/godoo-py
--json nameWithOwner,isPrivate,url` before provider writes. Use explicit
`--repo godoo-dev/godoo-py` throughout; an inherited tracker binding is not intake.
Local category values live in ignored `.mafe-si.toml`; tracked instructions must
remain usable without machine paths or HQ. Read AGENTS.md for authority.

## Choose the home

Retain the actionable request, open decision, impact, uncertainty and next check
in an issue early. Useful execution pieces can be a checklist; create linked
issues only for independently useful outcomes, acceptance or distinct ownership.
Preserve the original outcome when discovery changes the breakdown. Completing
one piece does not complete the integrated outcome.

Canonical API/target guidance belongs in README.md and docs/ through
[godoo-py-docs](../godoo-py-docs/SKILL.md). Provisional research, designs and private
evidence use owner-paths (or an explicit owner destination), outside source.
Link public supporting material only when accessible to the issue's readers;
keep essential qualified meaning self-contained if evidence is private or missing.
Missing supporting storage must not suppress a supported work-only capture.
When Marc or established practice selects a detailed issue discussion, keep its
useful tradeoffs and sources there; do not force a duplicate document. Routine
progress stays in the session. Use reporting-for-humans for the selected readers
when available, otherwise write the problem/result, limits and next action plainly.

## Find existing coverage and preserve source identity

Open an explicit issue first, including relevant comments and linked current
summaries:

```sh
gh issue view NUMBER --repo godoo-dev/godoo-py --json number,title,body,state,stateReason,labels,comments,url,updatedAt
```

Otherwise use `gh issue list --repo godoo-dev/godoo-py --state all --limit 100
--search 'TERMS' --json number,title,body,state,url,labels`. Search related terms
and inspect likely matches, including closed records and linked PRs. If limited,
paginate with `gh api --paginate 'repos/godoo-dev/godoo-py/issues?state=all&per_page=100'`
and distinguish issues from PRs. A closed delivery is dated evidence, not an
invitation to reopen it. Existing canonical coverage stays canonical.

For imported intake, retain the complete deduplication tuple: repository
`godoo-dev/godoo-py`, source namespace and immutable source reference. For private
sources publish only `Source identity: sha256:<digest>`, where digest is SHA256 of
UTF-8 `namespace + "\n" + source_reference`, without a trailing newline. Keep the
original tuple and mapping in private owner evidence. Reuse that identity on a
retry, including after an uncertain response; never blindly repeat a create.
Search all states for the digest and read the matching body before mutation.
GitHub provides no uniqueness constraint: recheck before creating, and stop on
ambiguous or concurrent ownership rather than choosing a second canonical issue.
Distinct corrections or independently tracked splits use distinct stable source
references and link the original; preserve its closed history.

Public titles, bodies, labels, comments, links and attachments must exclude private
company/customer identities, supplier details, thread IDs, local paths and raw
source keys. Sanitize before sending, including provider metadata. A SHA digest
identifies the source; it does not make a raw private payload safe to publish.

## Capture and triage

Write a reviewed body to an external file, then:

```sh
gh issue create --repo godoo-dev/godoo-py --title 'Desired outcome' --body-file /absolute/body.md
gh issue edit NUMBER --repo godoo-dev/godoo-py --body-file /absolute/body.md
```

New incoming work is open with `Triage: untriaged` in the body, not an accepted
execution commitment. Use body fields for `needs-info` (missing evidence and next
actor), `deferred` (reason and revisit condition), or accepted work under actual
owner direction. Do not invent labels, dates, priorities, assignees or schedules;
use existing descriptive labels only when useful. Keep needs-info/deferred issues
open. For supported closure, explain duplicate/superseded/withdrawn versus verified
completion in the body, link canonical remaining coverage, then use `gh issue close
NUMBER --repo godoo-dev/godoo-py --reason 'not planned'` or `--reason completed`
according to actual disposition. Migration closure means tracking migrated, not
problem fixed. Read back the result and state the remaining next actor.

Keep historical recovered findings as re-triage leads until current evidence
establishes each one. Separate observation, proposed solution, selected decision,
source/test result, publication/runtime and consumer acceptance. Retain authority,
attribution, dates and meaningful scope qualifications. A known supplier dependency
stays qualified in the issue; report needed owner decisions to Marc here without
contacting another project. Capture does not commission engineering or release
holdings. No inbox, dispatch, notification, schedule or delegate follows capture.

## Reconcile a consequential handback

Before handing back a changed result, blocker or next actor, reread the canonical
issue and compose its whole current body afresh. Preserve useful context, actual
acceptance, unresolved pieces and sources; remove superseded present-tense claims
and resolved detours. Reconcile known contradictory linked active summaries,
including a selected detailed discussion, under the same write authority. Keep
dated proposals and closed delivery accounts as dated history; a later evaluation
decision need not authorize production. A failure stays in the summary only while
it explains a current limit or next action. Unchanged routine progress warrants
no write. Comments are for substantive discussion explicitly in scope, never
migration narration, receipts or agent messages.

Read `updatedAt`/body again immediately before an edit; GitHub issue edits have no
compare-and-swap guarantee. Preserve concurrent changes or stop overlapping writes.
Read back every real result with the view command above, including labels, comments,
source identity, privacy and links. On a lost response, reconcile canonical source
coverage before retrying. Return the URL, created/updated/already-covered outcome,
actual disposition, authority limits and next actor through the current invocation.
For delivery corrections, amend the same open PR where appropriate; a post-merge
operational fix still needs its normal source checks and separate operation authority.
Linked remaining work survives either path. Read-only retrieval changes nothing.
