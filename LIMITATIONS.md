# Known limitations

EvidenceLint verifies exposed GitHub evidence. It is not a substitute for
running, reviewing, or security-testing repository code.

## Collection boundary

- Only GitHub REST data and the current default-branch tree are collected.
- Target repositories are not cloned, checked out, built, or executed.
- Current CI means check runs attached to the captured default-branch SHA; it
  does not summarize historical reliability.
- Recursive Git tree truncation makes path-absence rules `unavailable`.
- Account batch mode covers repositories owned by the authenticated account,
  not every organization membership or contributed repository.
- API permissions, rate limits, network failures, and GitHub availability can
  prevent conclusions.

## Rule boundary

- Presence proves that an artifact is exposed, not that its contents are good.
- Conventional filenames and paths can miss custom project layouts.
- AI-project and upstream-boundary detection use conservative heuristics and
  can require human review.
- Relative README links are checked against repository paths. External URLs,
  anchors, rendered HTML behavior, and third-party badge availability are not.
- Workflow badges and Release links are verified only when they explicitly
  target the current GitHub repository.
- EvidenceLint does not infer originality, plagiarism, authorship, production
  scale, user counts, security posture, or business value.

## Reporting boundary

- No composite score is produced. Status and action categories must be read at
  rule level.
- `missing` means expected evidence was absent; it does not necessarily mean
  the software is broken.
- `unavailable` is not equivalent to either success or failure.
- Private reports retain repository names and aggregate findings but remove
  evidence paths and raw README or source content.
- Reports are point-in-time snapshots and should record their capture time when
  used in reviews or portfolio materials.

## Action boundary

The composite Action reads through APIs and does not checkout target code. A
workflow author still controls token scope, report retention, artifact upload,
and whether strict-mode evidence gaps should fail a job.
