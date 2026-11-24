<#
Slugshot marketing commands. Run from this folder as `.\ss <command> ...` (ss.cmd calls this file).

  doctor                                     tool versions and setup checks
  import <file> --format PVP --concept X --hook Y   copy a recording into media\raw\ with the naming convention
  voice "<text>" <out.wav> [--voice am_puck]  Kokoro AI narration (scripts\voice.py -h)
  audio tidy|mix ...                         clean a voiceover; mix with ducked music + SFX (scripts\audio.py -h)
  caption <audio-or-video>                   Whisper -> .srt + .words.json, game terms auto-fixed (check the .srt)
  fixcaps <file.srt|file.words.json> ...     re-apply config\glossary.json to caption files
  vertical <clip> <out.mp4> [options]        FFmpeg 1080x1920 with captions/hook, then QC (scripts\vertical.py -h)
  render <job> <clip> [--format PVP] ...     Remotion template -> exports\<job>.mp4, then QC (scripts\render.py -h)
  batch <jobs\file.json>                     several variants from one set of assets (scripts\batch.py -h)
  qc <file.mp4> ...                          technical checks: size, codec, loudness, black/frozen/silent parts
  studio                                     open Remotion Studio to tweak the template
  clip <args>                                MakeMyClip CLI, confined to media\ (e.g. `.\ss clip ui`)
  yt <args>                                  YouTube collector (scripts\yt_collect.py -h)
  export                                     check platform metrics and write shareable CSVs to exports\share\
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
        Use-MakeMyClipEnv
        & npx.cmd --no-install clip doctor
    }
    'import' { & $Py scripts\import_capture.py @rest }
    'voice' { & $PyTts scripts\voice.py @rest }
    'audio' { & $Py scripts\audio.py @rest }
    'caption' { & $Py scripts\caption.py @rest }
    'fixcaps' { & $Py scripts\glossary.py fix @rest }
    'vertical' {
        & $Py scripts\vertical.py @rest
        if (-not $LASTEXITCODE) { & $Py scripts\qc.py $rest[1] }
    }
    'render' { & $Py scripts\render.py @rest }
    'batch' { & $Py scripts\batch.py @rest }
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
    'export' { & $Py scripts\export_metrics.py @rest }
    'smoke' { & $Py scripts\smoke_test.py @rest }
    default { (Get-Content $PSCommandPath -TotalCount 20) -join "`n" }
}
exit $LASTEXITCODE
