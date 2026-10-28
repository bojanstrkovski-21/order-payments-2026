# Restore a fresh throwaway database and run every tools\test_*.py against it (see "How to work" in CLAUDE.md).
#
#   .\tools\run_tests.ps1             one run on a fresh copy
#   .\tools\run_tests.ps1 -Runs 2     two runs, each on its own fresh copy (run twice after database changes)
#
# Needs: app\settings.ini (host, user, password of the Firebird server), work\db\novnal_for_nalozi26.fbk (the test
# baseline), the Firebird server running, and demo\.venv. Never touches the database named in settings.ini:
# the tests use work\db\TEST.FDB and work\test_settings.ini, both rebuilt on every run.
param([int]$Runs = 1)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "demo\.venv\Scripts\python.exe"
$baseline = Join-Path $root "work\db\novnal_for_nalozi26.fbk"
$scratch = Join-Path $root "work\db\TEST.FDB"
$testSettings = Join-Path $root "work\test_settings.ini"

foreach ($f in @($py, $baseline, (Join-Path $root "app\settings.ini"))) {
    if (-not (Test-Path $f)) { Write-Host "Missing: $f  (see docs\new_machine_setup.md)"; exit 2 }
}

# settings.ini: [database] host / user / password
$cfg = @{}
foreach ($line in Get-Content (Join-Path $root "app\settings.ini")) {
    if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.*?)\s*$') { $cfg[$Matches[1].ToLower()] = $Matches[2] }
}
foreach ($k in "host", "user", "password") {
    if (-not $cfg[$k]) { Write-Host "app\settings.ini has no '$k'"; exit 2 }
}

# gbak.exe of the installed Firebird server
$gbak = Get-ChildItem -Path ${env:ProgramFiles(x86)}, $env:ProgramFiles -Filter gbak.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "Firebird" } | Select-Object -First 1 -ExpandProperty FullName
if (-not $gbak) { Write-Host "gbak.exe not found - is the Firebird server installed?"; exit 2 }

# test_settings.ini = settings.ini with the path of the scratch database
$text = Get-Content (Join-Path $root "app\settings.ini") -Raw
$text = [regex]::Replace($text, '(?im)^\s*path\s*=.*$', { param($m) "path = $scratch" })
Set-Content -Path $testSettings -Value $text -Encoding UTF8

$failed = @()
for ($run = 1; $run -le $Runs; $run++) {
    Remove-Item $scratch -ErrorAction SilentlyContinue
    & $gbak -c -user $cfg["user"] -password $cfg["password"] $baseline "$($cfg['host']):$scratch" | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $scratch)) { Write-Host "gbak could not restore the baseline"; exit 2 }
    Write-Host "=== run $run of $Runs on a fresh copy"
    foreach ($t in Get-ChildItem (Join-Path $root "tools") -Filter "test_*.py" | Sort-Object Name) {
        $out = & $py -I -X utf8 $t.FullName $testSettings 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("OK    " + $t.Name)
        } else {
            Write-Host ("FAIL  " + $t.Name)
            $out | Select-Object -Last 6 | ForEach-Object { Write-Host "      $_" }
            $failed += "$($t.Name) (run $run)"
        }
    }
}
Remove-Item $scratch -ErrorAction SilentlyContinue
if ($failed) { Write-Host "`nFAILED: $($failed -join ', ')"; exit 1 }
Write-Host "`nAll tests passed ($Runs run(s))."
