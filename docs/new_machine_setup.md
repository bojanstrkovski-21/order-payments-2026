# Moving the NOVNAL workplace to another PC — step by step

Written for: the owner of the project, who will keep working on a different Windows PC and stop using this one.
All commands are PowerShell. The repository is **public**: nothing below puts a password, a database or personal data
into it — those travel on a USB stick (or another private way), never through GitHub.

## What travels how

| Thing | Where it lives | How it moves |
|---|---|---|
| Source code, specs, ministry lists, `CLAUDE.md`, slash commands (`.claude\commands`) | GitHub | `git push` here, `git clone` there |
| Python packages | `requirements.txt` | `pip install -r requirements.txt` |
| **The new program's database** (your real working data) | `D:\My Backups\Bojan\nalozi-26\NOVNAL.FDB` | **gbak backup → USB → gbak restore** |
| Test baseline `work\db\novnal_for_nalozi26.fbk` (has real data) | local only (`work\` is ignored) | USB |
| `app\settings.ini` (has the database password) | local only | **do not copy — recreate** |
| REA / Ghidra: `.mcp.json`, `work\rea\novnal_exe.snapshot`, `Nalozi\NOVNAL.exe`, `extracted\asm`, `extracted\forms`, `extracted\decomp` | local only | USB (+ install Ghidra, JDK, Node there) |
| Claude's private notes (`...\.claude\projects\...\memory`) | outside the repo | USB (optional — `CLAUDE.md` is the canonical record) |

> **One working database only.** The database is not in git. If you enter orders on both PCs the two copies drift apart
> and cannot be merged. Make the new PC the only one you work on, and stop using the database on this one.

---

# Part A — on THIS PC (before you leave it)

**A1. Finish and push the code.** Close the program, then in the project folder:

```powershell
cd "D:\My Backups\Bojan\ghidra-test"
git status
.\push.ps1 "Last changes before moving to another PC"
```

Check on github.com/bojanstrkovski-21/order-payments-2026 that the last commit is there.

**A2. Back up the new program's database** (read-only copy with `gbak -b -g`; never copy the `.FDB` file itself).
Use your Firebird SYSDBA password (the one in `app\settings.ini`):

```powershell
New-Item -ItemType Directory -Force "D:\handover" | Out-Null
$gbak = "C:\Program Files (x86)\Firebird\Firebird_2_1\bin\gbak.exe"
& $gbak -b -g -user SYSDBA -password "<SYSDBA-password>" "localhost:D:\My Backups\Bojan\nalozi-26\NOVNAL.FDB" "D:\handover\NOVNAL_new.fbk"
```

It must print no error and `D:\handover\NOVNAL_new.fbk` should be about 13 MB.

**A3. Collect the local-only files into `D:\handover\`** (keep the same sub-folder names):

```powershell
$p = "D:\My Backups\Bojan\ghidra-test"
Copy-Item "$p\work\db\novnal_for_nalozi26.fbk" D:\handover\                       # test baseline
New-Item -ItemType Directory -Force D:\handover\work\rea, D:\handover\Nalozi, D:\handover\extracted | Out-Null
Copy-Item "$p\work\rea\novnal_exe.snapshot" D:\handover\work\rea\                  # REA snapshot (RE only)
Copy-Item "$p\Nalozi\NOVNAL.exe" D:\handover\Nalozi\                               # the old program (RE only)
Copy-Item "$p\extracted\asm", "$p\extracted\forms", "$p\extracted\decomp" D:\handover\extracted\ -Recurse   # RE dumps
Copy-Item "$p\.mcp.json" D:\handover\                                              # REA config (paths to edit there)
Copy-Item "$env:USERPROFILE\.claude\projects\d--My-Backups-Bojan-ghidra-test\memory" D:\handover\claude-memory -Recurse
```

Do **not** copy `app\settings.ini` (you recreate it with the new PC's paths) and not the whole `Nalozi\` folder unless you
need the old program's other versions — it holds the old databases with real names, accounts and EMBG.

**A4. Put `D:\handover\` on a USB stick** (ideally encrypted with BitLocker To Go). It contains personal data:
never upload it to GitHub or a public cloud folder. Delete the copy on this PC only when the new PC works (Part B done).

---

# Part B — on the NEW PC

## B1. Install the programs

1. **Git for Windows** (git-scm.com). Then set who you are:
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "your-github-email"
   ```
2. **Python 3.14, 64-bit** (python.org). Tick *Add python.exe to PATH* and keep the `py` launcher. Check: `py -3.14 --version`.
3. **Firebird 2.1** (firebirdsql.org → Downloads → *Firebird 2.1*, the **Win32** installer; this PC runs 2.1.1).
   In the installer choose: *Super Server*, *Run as a service*, *Start at boot*, and **set a SYSDBA password** — write it down;
   it goes into `app\settings.ini`. Check that the service **Firebird Server - DefaultInstance** is *Running*
   (`Get-Service *Firebird*`).
4. **VS Code** and **Claude Code** (follow the official setup: docs.claude.com → Claude Code → Setup), sign in with your account.
5. A printer, or just use *Microsoft Print to PDF* — the program also writes its own PDFs. Segoe UI ships with Windows.

## B2. Get the code

```powershell
cd D:\          # or any folder; the examples below use D:\NOVNAL
git clone https://github.com/bojanstrkovski-21/order-payments-2026.git NOVNAL
cd D:\NOVNAL
```

(Cloning a public repo needs no login. The first `git push` opens a browser window to sign in to GitHub — that is the
Git Credential Manager, it is normal.)

## B3. Python environment

```powershell
cd D:\NOVNAL
py -3.14 -m venv demo\.venv
demo\.venv\Scripts\python.exe -m pip install -r requirements.txt
demo\.venv\Scripts\python.exe -c "import wx, firebirdsql, fpdf, pymupdf; print('imports ok', wx.version())"
```

The project's environment must be exactly `demo\.venv` (the tests, the slash commands and `CLAUDE.md` use that path).

## B4. Put the database back

1. Copy `NOVNAL_new.fbk` from the USB stick to `D:\NOVNAL\work\db\` (create the folder; it is git-ignored), and
   `novnal_for_nalozi26.fbk` next to it.
2. Make a folder for the live database that the Firebird service may write to, e.g. `D:\NOVNAL-data`:
   ```powershell
   New-Item -ItemType Directory -Force D:\NOVNAL-data | Out-Null
   $gbak = "C:\Program Files (x86)\Firebird\Firebird_2_1\bin\gbak.exe"
   & $gbak -c -user SYSDBA -password "<SYSDBA-password>" D:\NOVNAL\work\db\NOVNAL_new.fbk "localhost:D:\NOVNAL-data\NOVNAL.FDB"
   ```
   No output means success. (`-c` creates; it refuses to overwrite — use `-r` only when you really want to replace.)
3. The program adds its own new columns/tables on start (`db.ensure_schema()`), so the restored database is complete.

## B5. Tell the program where the database is

```powershell
Copy-Item app\settings.example.ini app\settings.ini
notepad app\settings.ini
```

Set `path = D:\NOVNAL-data\NOVNAL.FDB`, `user = SYSDBA`, `password = <your SYSDBA password>`; keep `host = localhost`.
`settings.ini` is ignored by git — never commit it. Check the connection:

```powershell
cd app
$env:PYTHONPATH = "."
..\demo\.venv\Scripts\python.exe -X utf8 -c "import db; print(len(db.list_konta()), 'konta,', len(db.list_accounts()), 'accounts')"
cd ..
```

You should see **985 konta** (393 rashodi and 592 prihodi, your 3 old ones among them) and your accounts. If the number is
smaller, the restore used an older backup.

## B6. Run the tests

```powershell
.\tools\run_tests.ps1 -Runs 2
```

It restores `work\db\novnal_for_nalozi26.fbk` to a throwaway `TEST.FDB` (never your live database), runs every
`tools\test_*.py`, and prints OK/FAIL per file. Run it twice after database changes (each run gets its own fresh copy).
Running the tests twice on the **same** copy by hand fails by design — always use the script.

> **Known state when this guide was written (2026-10-28):** 7 test files (`test_nal60/61/62/70/76/80_form`, `test_workdays`)
> fail because of the unfinished "order-form picks" work in `app\orders.py` (`_add_ellipsis_button` inserts the "…" button
> into a vertical sizer with `wxALIGN_CENTER_VERTICAL`, wx refuses it, and the fallback adds the same button twice, which
> crashes the order dialog). Until that is fixed the order forms cannot open. If this is already fixed in `CLAUDE.md`
> ("Progress"), ignore this note and delete it.

## B7. Start the program

```powershell
cd D:\NOVNAL\app
..\demo\.venv\Scripts\python.exe main.py
```

Shipment screen, the seven order forms, and Шифрарник (Генералии, Сметки, Конта, Општини, Уплатни сметки) are there.
The program only ever uses the database in `settings.ini`. The old program's database (`D:\nalozi\NOVNAL.FDB` on the old
PC) is never written to — `db.ensure_schema()` refuses that path.

## B8. Claude Code on the new PC

1. Open the folder `D:\NOVNAL` in VS Code and start Claude Code there. It reads `CLAUDE.md` automatically, and the two slash
   commands `/start-session` and `/end-session` come with the repository (`.claude\commands`).
2. **Private notes (optional):** Claude keeps notes outside the repo in
   `%USERPROFILE%\.claude\projects\<project-folder-name>\memory`. The folder name is built from the project path
   (`D:\My Backups\Bojan\ghidra-test` → `d--My-Backups-Bojan-ghidra-test`; `D:\NOVNAL` → `d--NOVNAL`). Run Claude Code once in
   the project, then copy the `.md` files from `claude-memory` on the USB stick into the new `...\memory` folder.
   `CLAUDE.md` is the canonical record; the notes only add private facts (e.g. that the database password is local).
3. Start every day with `/start-session` (pull, check, run tests, summary) and end it with `/end-session`, then run
   `.\push.ps1 "message"` yourself — Claude does not push.

## B9. REA + Ghidra (reverse engineering of the old program) — only needed when behaviour of `NOVNAL.exe` is unclear

Registers and order work are mostly app-side now, so you can skip this and add it later. When you need it:

1. **Install** (each from its official site):
   - **Node.js** (LTS) — `npx` downloads the REA server on first use, so this PC needs internet then. Check `node --version`.
   - **JDK 21** (Temurin or Oracle). This PC runs 21.0.12. Check `java -version`.
   - **Ghidra 12.1.4** — download `ghidra_12.1.4_PUBLIC_20260921.zip` from
     github.com/NationalSecurityAgency/ghidra/releases and unzip it, e.g. to `C:\Tools\ghidra_12.1.4_PUBLIC`.
2. **Put the local-only RE files back** in the project (same relative places, from the USB stick):
   - `Nalozi\NOVNAL.exe` — the old program (the one analysed was the 25.02.2020 build)
   - `work\rea\novnal_exe.snapshot` — saved analysis, so Ghidra need not re-analyse
   - `extracted\asm\`, `extracted\forms\`, `extracted\decomp\` — the dumps of the old program (not in git)
3. **Create `D:\NOVNAL\.mcp.json`** (git-ignored; it holds machine paths). Use the file from the USB stick and fix the two
   paths, or write it fresh:
   ```json
   {
     "mcpServers": {
       "rea": {
         "command": "cmd.exe",
         "args": ["/d", "/c", "npx", "-y", "rea-agents@6.7.0", "mcp"],
         "env": {
           "GHIDRA_INSTALL_DIR": "C:\\Tools\\ghidra_12.1.4_PUBLIC",
           "JAVA_HOME": "C:\\Program Files\\Java\\jdk-21",
           "REA_ANALYSIS_PROVIDER": "ghidra"
         }
       }
     }
   }
   ```
   `GHIDRA_INSTALL_DIR` is the folder that contains `ghidraRun.bat`; `JAVA_HOME` is the JDK folder. Keep the version
   `rea-agents@6.7.0` so the snapshot stays compatible.
4. **Restart Claude Code** in the project folder and approve the project MCP server when it asks. Check with `/mcp` that
   `rea` is *connected*.
5. **Reopen the old program quickly** — ask Claude to call `open_binary` with the full path to `Nalozi\NOVNAL.exe` and
   `snapshot_path` = the full path to `work\rea\novnal_exe.snapshot`. (The snapshot must match the same `NOVNAL.exe`; if REA
   refuses it, open without the snapshot and let it analyse again — slower, same result.)
6. **Limits** (same as on the old PC): Ghidra support for Windows in REA is experimental and *read-only* — renaming,
   comments and bookmarks are unavailable, and Ghidra misses many Delphi handlers. That is why the project has its own
   helpers: `tools\delphi_methods.py` (event handlers and field offsets from the Delphi tables), `tools\delphi_listing.py`
   (Capstone listing with field names and strings) and `tools\param_map.py` (which value goes into which SQL parameter);
   they need `pefile` and `capstone`, already in `requirements.txt`. Large outputs overflow and are saved to files.
7. When you are done with a session, ask Claude to `close_binary` and save the snapshot to `work\rea\novnal_exe.snapshot`
   (`/end-session` does this).

## B10. Everyday work on the new PC

```powershell
cd D:\NOVNAL
# start of day: in Claude Code type /start-session
# ... work ...
# end of day: in Claude Code type /end-session, then in PowerShell:
.\push.ps1 "what changed today"
```

`push.ps1` commits everything that is not in `.gitignore`, so before pushing check `git status` for stray database files,
passwords or real names/accounts/EMBG.

## When something goes wrong

| Symptom | Cause / fix |
|---|---|
| "connection refused" / cannot connect to `localhost` (port 3050) | The Firebird service is not running: `Start-Service FirebirdServerDefaultInstance` (display name *Firebird Server - DefaultInstance*; or start it in `services.msc`). |
| `Your user name and password are not defined` | Wrong SYSDBA password in `app\settings.ini`; it must match what you set in the Firebird installer. |
| `I/O error ... CreateFile (create)` ... *path not found* on restore | The target folder does not exist or the Firebird service may not write there. Create it (e.g. `D:\NOVNAL-data`) and put the database inside. |
| `I/O error ... CreateFile (create)` ... *The file exists* on restore | `-c` never overwrites. Choose a new file name, or use `-r` if you really want to replace the database. |
| `ModuleNotFoundError: No module named 'db'` when running a script | Run it from `app\`, or set `$env:PYTHONPATH = "."` first (the `-I` flag removes the script folder from the path; the tests insert it themselves). |
| Cyrillic shows as `?` or crashes when output goes to a file | Always run Python with `-X utf8`. |
| wxPython does not install | Wrong Python: it must be 64-bit Python 3.14 (`py -3.14 -c "import struct; print(struct.calcsize('P')*8)"` prints 64). |
| A test fails only on the second run | You reused the same scratch database. Use `.\tools\run_tests.ps1`; it restores a fresh copy every run. |
| REA says no app is open | Open the old program first (`open_binary`, step B9.5); nothing stays open between Claude Code sessions. |

## Checklist

- [ ] A1 pushed · A2 `NOVNAL_new.fbk` made · A3 local files collected · A4 USB stick safe
- [ ] B1 Git, Python 3.14, Firebird 2.1 (service running), VS Code + Claude Code
- [ ] B2 repository cloned · B3 `demo\.venv` built, imports ok
- [ ] B4 database restored · B5 `settings.ini` written, 985 konta counted
- [ ] B6 `.\tools\run_tests.ps1 -Runs 2` — result noted (see the *Known state* note)
- [ ] B7 program starts · B8 Claude Code reads `CLAUDE.md`, `/start-session` works
- [ ] B9 (optional) Node, JDK 21, Ghidra, `.mcp.json`, `/mcp` shows `rea` connected, `open_binary` works
- [ ] Only now: stop using the database on the old PC
