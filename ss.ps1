<#
Slugshot marketing commands. Run from this folder as `.\ss <command> ...` (ss.cmd calls this file).

  doctor                                     tool versions and setup checks
  import <file> --format PVP --concept X --hook Y   copy a recording into media\raw\ with the naming convention
  voice "<text>" <out.wav> [--voice am_puck]  Kokoro AI narration (scripts\voice.py -h)
  audition [NAMES]                           Gemini voice candidates per character (out\voices\review.html)
  cast [--redo NAME ...]                     design each character's fixed reference voice from config\cast.json (once)
  dialogue <jobs\dialogue\x.txt> [--engine]  cast script -> per-line voices + timing manifest + captions (scripts\dialogue.py -h)
  audio tidy|mix ...                         clean a voiceover; mix with ducked music + SFX (scripts\audio.py -h)
  caption <audio-or-video>                   Whisper -> .srt + .words.json, game terms auto-fixed (check the .srt)
  fixcaps <file.srt|file.words.json> ...     re-apply config\glossary.json to caption files
  vertical <clip> <out.mp4> [options]        FFmpeg 1080x1920 with captions/hook, then QC (scripts\vertical.py -h)
  render <job> <clip> [--format PVP] ...     Remotion template -> exports\<job>.mp4, then QC (scripts\render.py -h)
  batch <jobs\file.json>                     several variants from one set of assets (scripts\batch.py -h)
  assemble <jobs\edit.json>                  multi-scene video: clips, stills, cards, script/VO, music, SFX
  candidates <video> <gemini.csv>            cut Gemini's timestamped moments (+/- 5 s) for human review
  qc <file.mp4> ...                          technical checks: size, codec, loudness, black/frozen/silent parts
  sheet <file.mp4> [--every 1]               frame sheet for creative review (<file>.sheet.jpg)
  roblox <validate|list|audit|build|switch|rebuild|guard|compare|import|film|rec>   Roblox-native filming (roblox-native/README.md)
  studio                                     open Remotion Studio to tweak the template
  clip <args>                                MakeMyClip CLI, confined to media\ (e.g. `.\ss clip ui`)
  yt <args>                                  YouTube collector (scripts\yt_collect.py -h)
  wiki|trends|twitch|rbx|observe <args>      research collectors (docs\research-data.md)
  references <pack|apify-check>                build local creative reference packs or check Apify credit and pricing
  research status|prune|runs|collect|bundle|families   collection runs, bundles, query families
  analyze <intake|describe|repeat|sensitivity|trend|changepoints|sample|blind-packet|coding-packet|join-annotations|context>
  evidence <new|validate|card|export-evidenceguard>   evidence ledger (docs\research-evidence.md)
  kb <validate|find|show|due|brief|stats|render|export|migrate|new>   knowledge banks (docs\knowledge-banks.md)
  sentiment <status|packet|join|list|prune>   audience comment coding (docs\audience-sentiment.md)
  composio status|test|audit                 Composio read-only checks (docs\composio.md)
  export                                     check platform metrics and write shareable CSVs to exports\share\
  dash [open|sync|status|import|export|install|demo|stop]   personal dashboard (docs\dashboard\README.md)
  publish <accounts|list|show|new|check|package|mark-posted>   publishing drafts (owner approves in the dashboard)
  smoke                                      run the smoke test and write reports\smoke-test.md
#>
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
Set-Location $Root
# New installs (winget FFmpeg) only reach PATH in new terminals; read it fresh every time.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$PyTts = Join-Path $Root '.venv-tts\Scripts\python.exe'
$Ffmpeg = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source

function Use-MakeMyClipEnv {
    New-Item -ItemType Directory -Force (Join-Path $Root 'media') | Out-Null
    $env:MAKEMYCLIP_WORKSPACE = Join-Path $Root 'media'
    if ($Ffmpeg) { $env:MAKEMYCLIP_FFMPEG_PATH = $Ffmpeg }
}

$cmd = $args[0]
$rest = @($args | Select-Object -Skip 1)  # always an array, so a single argument isn't split into characters
# PowerShell turns an unquoted `en,es` into an array; re-join it so `--lang en,es` reaches Python as one value.
$rest = @($rest | ForEach-Object { if ($_ -is [array]) { $_ -join ',' } else { $_ } })
switch ($cmd) {
    'doctor' {
        $kden = Join-Path $env:LOCALAPPDATA 'Programs\Kdenlive\bin\kdenlive.exe'
        $obs = Join-Path $env:ProgramFiles 'obs-studio\bin\64bit\obs64.exe'
        "git       $(git --version)"
        "python    $(& $Py --version) (.venv)"
        "whisper   $(& $Py -c "import importlib.metadata as m; print(m.version('openai-whisper'))")"
        "kokoro    $(& $PyTts -c "import importlib.metadata as m; print(m.version('kokoro-onnx'))") (.venv-tts)"
        "node      $(node --version)"
        "ffmpeg    $(if ($Ffmpeg) { (ffmpeg -hide_banner -version | Select-Object -First 1) } else { 'MISSING' })"
        "obs       $(if (Test-Path $obs) { (Get-Item $obs).VersionInfo.ProductVersion } else { 'MISSING' })"
        "kdenlive  $(if (Test-Path $kden) { 'installed' } else { 'MISSING' })"
        "remotion  $(node -p "require('./node_modules/remotion/package.json').version")"
        "makemyclip $(node -p "require('./node_modules/@makemyclip/editor/package.json').version")"
        "youtube   $(if ((Test-Path .env) -and (Select-String -Path .env -Pattern '^YOUTUBE_API_KEY=.+' -Quiet)) { 'key present in .env' } else { 'BLOCKED: no key in .env' })"
        "twitch    $(if ((Test-Path .env) -and (Select-String -Path .env -Pattern '^TWITCH_CLIENT_SECRET=.+' -Quiet)) { 'credentials present in .env' } else { 'BLOCKED: no Twitch credentials in .env' })"
        Use-MakeMyClipEnv
        & npx.cmd --no-install clip doctor
    }
    'import' { & $Py scripts\import_capture.py @rest }
    'voice' { & $PyTts scripts\voice.py @rest }
    'dialogue' { & $Py scripts\dialogue.py @rest }
    'audition' { & $Py scripts\gemini_tts.py audition @rest }
    'cast' {
        # qwen-tts prints a harmless "sox not found" warning on stderr; don't let PowerShell treat it as fatal.
        $ErrorActionPreference = 'Continue'
        & (Join-Path $Root '.venv-voicelab\Scripts\python.exe') scripts\voicelab.py cast @rest 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch "sox|SoX|sourceforge|path variables|proceed here|flash-attn|^\*+$" }
    }
    'sfx' { & $Py scripts\sfx.py @rest }
    'audio' { & $Py scripts\audio.py @rest }
    'caption' { & $Py scripts\caption.py @rest }
    'fixcaps' { & $Py scripts\glossary.py fix @rest }
    'vertical' {
        & $Py scripts\vertical.py @rest
        if (-not $LASTEXITCODE) { & $Py scripts\qc.py $rest[1] }
    }
    'render' { & $Py scripts\render.py @rest }
    'batch' { & $Py scripts\batch.py @rest }
    'assemble' { & $Py scripts\assemble.py @rest }
    'candidates' { & $Py scripts\candidates.py @rest }
    'sheet' { & $Py scripts\sheet.py @rest }
    'roblox' {
        $sub = $rest[0]
        $more = @($rest | Select-Object -Skip 1)
        switch ($sub) {
            'validate' { & $Py roblox-native\tools\scene.py validate @more }
            'list' { & $Py roblox-native\tools\scene.py list }
            'audit' { & $Py roblox-native\tools\audit_place.py roblox-native\studio\SlugshotMarketing.rbxlx @more }
            'build' { & $Py roblox-native\tools\make_marketing_place.py @more }
            'switch' { & $Py roblox-native\tools\studio_switch.py @more }
            'rebuild' { & $Py roblox-native\tools\studio_switch.py --rebuild }
            'guard' { & $Py roblox-native\tools\studio_guard.py --probe }
            'compare' { & $Py roblox-native\tools\take.py compare @more }
            'import' { & $Py roblox-native\tools\take.py import @more }
            'film' { & $Py roblox-native\tools\take.py film @more }
            'rec' { & $Py roblox-native\tools\rec.py @more }
            default { 'ss roblox validate|list|audit|build|switch|rebuild|guard|compare|import (see roblox-native/README.md)' }
        }
    }
    'qc' { & $Py scripts\qc.py @rest }
    'studio' { & npm.cmd run studio }
    'clip' {
        Use-MakeMyClipEnv
        # MakeMyClip confines MCP/UI paths to its workspace but trusts the CLI, so check paths here.
        $media = $env:MAKEMYCLIP_WORKSPACE + '\'
        foreach ($a in $rest) {
            # Anything that looks like a path: has a separator, a drive, or a file extension.
            if ("$a" -match '[\\/]|^[A-Za-z]:|\.[A-Za-z0-9]{2,6}$') {
                $p = if ([IO.Path]::IsPathRooted("$a")) { "$a" } else { Join-Path $Root "$a" }
                $full = [IO.Path]::GetFullPath($p)
                # Follow junctions/symlinks so a link inside media\ can't point elsewhere.
                $item = Get-Item -LiteralPath $full -ErrorAction SilentlyContinue
                if ($item -and $item.LinkType) { $full = [IO.Path]::GetFullPath(@($item.Target)[0]) }
                if (-not $full.StartsWith($media, [StringComparison]::OrdinalIgnoreCase)) {
                    throw "Refusing '$a': MakeMyClip may only use files under media\ (copy the file there first)."
                }
            }
        }
        & npx.cmd --no-install clip @rest
    }
    'yt' { & $Py scripts\yt_collect.py @rest }
    'wiki' { & $Py scripts\wiki_collect.py @rest }
    'trends' { & $Py scripts\trends_collect.py @rest }
    'twitch' { & $Py scripts\twitch_collect.py @rest }
    'rbx' { & $Py scripts\rbx_collect.py @rest }
    'observe' { & $Py scripts\observe.py @rest }
    'research' { & $Py scripts\research_admin.py @rest }
    'references' { & $Py scripts\creative_references.py @rest }
    'analyze' { & $Py scripts\research_analysis.py @rest }
    'evidence' { & $Py scripts\evidence.py @rest }
    'kb' { & $Py scripts\kb.py @rest }
    'sentiment' { & $Py scripts\sentiment.py @rest }
    'composio' { & $Py scripts\composio_check.py @rest }
    'export' { & $Py scripts\export_metrics.py @rest }
    'dash' { & $Py -m dashboard @rest }
    'publish' { & $Py -m dashboard publish @rest }
    'smoke' { & $Py scripts\smoke_test.py @rest }
    default { (Get-Content $PSCommandPath -TotalCount 20) -join "`n" }
}
exit $LASTEXITCODE

