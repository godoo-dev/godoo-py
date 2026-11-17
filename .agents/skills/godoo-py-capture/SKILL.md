---
name: godoo-py-capture
description: Capture, triage, retrieve and update godoo-py work in its GitHub issues — requests, breakdowns, decisions, deferred observations and delivery updates — and route knowledge godoo-py does not own, including Odoo-server behaviour to Atlas intake. Documentation edits use godoo-py-docs.
---

# Capture godoo-py work

Work records live in the public
[godoo-py issues](https://github.com/godoo-dev/godoo-py/issues). Pass
`--repo godoo-dev/godoo-py` on every `gh` command. Private values, such as the
local evidence root, live in the ignored `.mafe-si.toml` of the main checkout.
Read them there and never copy them into the repository or an issue.

Lasting knowledge that godoo-py owns goes in its docs through
[godoo-py-docs](../godoo-py-docs/SKILL.md). Working notes go in `.scratch/`.

## Decide whether to write

Create an issue for an explicit request, an actionable follow-up, a blocker or
an open decision. Update the existing issue when the outcome, scope, decision or
next actor changes. Write nothing for routine progress, a passed check, a merge
or a handback; the conversation or the PR is enough. A tiny settled task can
skip an issue and go straight to a PR.

## Find existing coverage

Open an issue that someone names, together with its comments:

```sh
gh issue view NUMBER --repo godoo-dev/godoo-py --comments
```

Otherwise search all states, including closed issues and linked PRs:

```sh
gh issue list --repo godoo-dev/godoo-py --state all --limit 100 --search 'TERMS'
```

A same-outcome issue is a duplicate, so update it instead. A related issue gets
a link. A closed delivery is dated history, not something to reopen.

## Write a record

Use reporting-for-humans to write, and run pre-post immediately before each
command that posts tracker text. Compose the body once from what the reader needs:
the outcome, why it matters, what is known and uncertain, and the next step. Link
supporting material rather than copying it.

```sh
gh issue create --repo godoo-dev/godoo-py --title 'Desired outcome' --body-file .scratch/issue.md
gh issue edit NUMBER --repo godoo-dev/godoo-py --body-file .scratch/issue.md
gh issue comment NUMBER --repo godoo-dev/godoo-py --body-file .scratch/comment.md
```

Read the record back only if a command reported an error. After an uncertain
response, search before you retry so that you do not create a duplicate.

This repository is public. Leave out customer and supplier identities, private
thread IDs, local paths and raw private source keys. When imported intake needs
a stable identity, publish only `Source identity: sha256:<digest>` and keep the
mapping in private owner evidence. The digest is the SHA-256 of
`namespace + "\n" + source_reference`.

## Breakdowns, triage and lifecycle

- **Requests:** new intake gets `Triage: untriaged` in the body. That records the
  request but does not commit to doing it.
- **Breakdowns:** use a checklist in the body for steps. Create linked issues or
  sub-issues only for outcomes that someone can deliver or accept independently.
  Keep the original outcome, because finishing one piece does not finish the
  whole.
- **States:** issues are open or closed, and there is no project board. Record
  `needs-info` (what is missing and who supplies it) or `deferred` (why, and
  when to revisit) in the body, and keep the issue open. Use existing labels only
  when they help. Do not invent labels, priorities, assignees or dates.
- **Closing:** state the reason in the body. Then run
  `gh issue close NUMBER --repo godoo-dev/godoo-py --reason completed` or
  `--reason 'not planned'`. Closing for duplicates, withdrawals or migration
  needs the owner's direction or an evident duplicate.
- **Dependencies:** GitHub supports native blocked-by links and sub-issues
  through the REST API:

  ```sh
  ID=$(gh api repos/godoo-dev/godoo-py/issues/BLOCKER --jq .id)
  gh api -X POST repos/godoo-dev/godoo-py/issues/NUMBER/dependencies/blocked_by -F issue_id="$ID"
  gh api -X DELETE repos/godoo-dev/godoo-py/issues/NUMBER/dependencies/blocked_by/"$ID"
  gh api -X POST repos/godoo-dev/godoo-py/issues/PARENT/sub_issues -F sub_issue_id="$CHILD_ID"
  ```

## Deferred observations

When you notice something off-task, record it briefly in an issue, or add it to
the matching existing issue: what you saw, where, and why it may matter. Then
return to the current task. Historical findings stay leads until current
evidence confirms them.

## Knowledge godoo-py does not own

Classify the claim before you retain it:

| Claim | Owner | What to do from a godoo-py session |
| --- | --- | --- |
| How godoo-py code behaves, Python targets, how to work on godoo-py | godoo-py | Edit the docs through godoo-py-docs. Track remaining work here. |
| What the Odoo server does by version, edition or module | Atlas | Send it to Atlas intake: give the owner a handoff with the claim, the Odoo version, edition and modules, how it was observed, and a reproduction. Once the fact ID exists, add the godoo-py reflection and its `atlas:` marker through godoo-py-docs. |
| What an agent should do with an MCP tool | MCP repository | Hand off to that project. |
| Another Godoo component's behaviour or work | That component | Hand off to that project. |
| Synthesis or decisions across components | The owner's coordination docs | Hand off to the owner. |

Hand-offs go through coordinate-projects as a proposal to the owner in the
current conversation. Never write into another project's tracker or knowledge
store from here. If godoo-py work waits on the hand-off, track that dependency
in a godoo-py issue. Recording something does not authorize executing it.

## Update after delivery

When a PR changes an issue's outcome, blocker or next actor, re-read the issue
and rewrite its body to describe the current state. Keep acceptance evidence,
remaining pieces and sources, and drop claims that are no longer true. Use
comments only for substantive discussion. For a correction, amend the open PR.
Report the issue URL, what changed and who acts next.
