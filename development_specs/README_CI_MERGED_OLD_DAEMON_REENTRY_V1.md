# Long-horizon daemon self-healing across a certified GitHub merge

## Actual incident, 27 November 2026, Dell-115

The offline development daemon stopped at 17:12 MYT while running the old
PR #674 main checkout. CI-verified PR #675 then merged to GitHub at
17:16. The source-attested native watchdog refused to restart a checkout
that no longer matched GitHub main. The independently tested deployment
mechanism could not cut over because it required an active old daemon.
The promotion controller stopped, creating an actual deadlock.

A one-time manually verified old-daemon restart was followed by the existing
guarded PR #675 cutover and native watchdog restart of the controller.
The change in this PR makes the same **autonomous-code promotion** edge
case an executable registry recovery rather than a manually repeated fix.

## Executable solution

When the original native offline daemon is stopped, its genuine saved
heartbeat is stale and explicitly STOPPED, and current GitHub main is
ahead of the clean old checkout, the five-minute watchdog may use a single
immutable, already-merged, source-code promotion claim to check:

1. Its job, original GitHub PR, one-claim merger, exact old base and new
   merge commit are unique, internally consistent and publisher-safe.
2. Live GitHub independently confirms that exact PR was merged; the new
   main has the same tree as that verified PR head, with the original base
   as its only parent (squash merge).
3. The latest matching head SHA Windows reliability workflow and both
   independent Windows jobs completed successfully; no other exact-head
   workflow is pending or failed.
4. The original scheduled task remains the same named limited interactive
   Windows account owner, has a verified ready state, and no old active
   process. The new source is NOT deployed in this recovery step.

It then starts ONLY the original stopped daemon; it will start the
original promotion controller only after a fresh process/heartbeat has
been independently attested. That controller resumes the existing
SHA-pinned guarded deployment and protects the old journal.

If any source, status, merged PR, tree, CI, live PID or one-claim receipt
is missing, ambiguous or changed, this bridge fails closed. It does not
retry any uncertain Gemini browser Send, call a paid API, merge GitHub PRs,
replay a claimed deployment, modify academic evidence, publish student
content, or mark G2/G3 science/audio/video as academically accepted.

## Verification

- `tests/test_development_pending_merge_restart_bridge_v1.py`: GitHub
  fake-PR/merge/CI/state fault-injection; rejects dirty source, wrong
  merge tree, duplicate claims, missing job, CI failures and all unsafe
  source/API/publication flags.
- `tests/test_development_windows_autorestart_watchdog_v1.py`: bounded
  cross-revision restart of an explicitly stopped original daemon, successful
  controller resumption, and fail-closed unexpected GitHub source changes.
- Live **read-only verification against genuine merged PR #676** on Dell-115,
  source old `e2986ac`, new merge `060f848`, original Windows CI run
  `45973304527`, returned `VERIFIED_PENDING_CI_MERGE_OLD_DAEMON_REENTRY_NO_SEND`.
  This verifies source/CI provenance; no artificial production crash was
  introduced.
