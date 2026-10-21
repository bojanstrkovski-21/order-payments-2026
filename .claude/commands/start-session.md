---
description: Sync with GitHub and summarise where the NOVNAL rewrite stands
---

Start a work session on the NOVNAL rewrite:

1. **Sync with GitHub**: `git pull --no-rebase` on `main` in the project root. Report if it pulled anything, and stop
   and tell the user if there is a conflict or uncommitted local work that blocks the pull. Do not commit or push.
2. **Check the setup** quickly: Firebird service running, `D:\My Backups\Bojan\nalozi-26\NOVNAL.FDB` and
   `work\db\novnal_for_nalozi26.fbk` present, `app\settings.ini` present, `demo\.venv` imports wx and firebirdsql,
   REA/Ghidra reachable (reopen `Nalozi\NOVNAL.exe` with the snapshot `work\rea\novnal_exe.snapshot`).
3. **Run the test suite** once on a fresh throwaway database copy (see "How to work" in CLAUDE.md).
4. **Summarise for the user**, short and in plain words: what is done, what was last worked on, open questions and
   open items for the user, and what comes next — taken from CLAUDE.md "Progress" and the private memory notes.
   Then continue with the next item unless the user says otherwise.
