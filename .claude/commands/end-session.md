---
description: Write the session to memory and tell the user they can run push.ps1
---

End a work session on the NOVNAL rewrite:

1. **Write memory**: update `CLAUDE.md` (Progress, decisions, rules — nothing private) and the private memory notes
   outside the repository so both describe the same state. Close the REA/Ghidra target with `close_binary`, saving the
   snapshot to `work\rea\novnal_exe.snapshot` (overwrite).
2. **Check before the user pushes**: `git status --short`, and confirm that nothing sensitive would be committed
   (no `.fdb/.gdb/.fbk`, `app\settings.ini`, `Nalozi\`, `work\`, `.mcp.json`, passwords, real names/accounts/EMBG).
   Do **not** commit or push — the user pushes.
3. **Tell the user** they can now run `.\push.ps1 "message"`, and suggest a one-line commit message that sums up
   the session's changes.
