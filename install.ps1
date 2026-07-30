[CmdletBinding()]
param(
    [string]$DestinationRoot
)

$ErrorActionPreference = "Stop"
$skillName = "blur-video-faces"
$version = "1.0.0"
$packageUrl = "https://raw.githubusercontent.com/pinxihao-code/-skill/main/dist/blur-video-faces-skill-v$version.zip"

if (-not $DestinationRoot) {
    $codexRoot = if ($env:CODEX_HOME) {
        $env:CODEX_HOME
    } else {
        Join-Path $env:USERPROFILE ".codex"
    }
    $DestinationRoot = Join-Path $codexRoot "skills"
}

$DestinationRoot = [System.IO.Path]::GetFullPath($DestinationRoot)
$destination = Join-Path $DestinationRoot $skillName
if (Test-Path -LiteralPath $destination) {
    throw "Skill already exists: $destination"
}

New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
$staging = Join-Path $DestinationRoot ("." + $skillName + ".installing-" + [guid]::NewGuid().ToString("N"))
$downloadRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("blur-video-faces-install-" + [guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    $localSource = Join-Path $PSScriptRoot "skills\$skillName"

    if (Test-Path -LiteralPath (Join-Path $localSource "SKILL.md")) {
        Copy-Item -Recurse -Force -Path (Join-Path $localSource "*") -Destination $staging
    } else {
        New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
        $archive = Join-Path $downloadRoot "skill.zip"
        $extract = Join-Path $downloadRoot "extract"
        Invoke-WebRequest -Uri $packageUrl -OutFile $archive
        Expand-Archive -LiteralPath $archive -DestinationPath $extract
        $packageSource = Join-Path $extract $skillName
        if (-not (Test-Path -LiteralPath (Join-Path $packageSource "SKILL.md"))) {
            throw "Downloaded package does not contain $skillName\SKILL.md"
        }
        Copy-Item -Recurse -Force -Path (Join-Path $packageSource "*") -Destination $staging
    }

    if (-not (Test-Path -LiteralPath (Join-Path $staging "SKILL.md"))) {
        throw "Staged Skill is invalid: SKILL.md is missing"
    }

    Move-Item -LiteralPath $staging -Destination $destination
    Write-Host "Installed $skillName to $destination"
    Write-Host "The Skill will be available on the next Agent turn."
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -Recurse -Force -LiteralPath $staging
    }
    if (Test-Path -LiteralPath $downloadRoot) {
        $resolvedDownload = (Resolve-Path -LiteralPath $downloadRoot).Path
        $tempRoot = [System.IO.Path]::GetTempPath().TrimEnd("\")
        if ($resolvedDownload.StartsWith($tempRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -Recurse -Force -LiteralPath $resolvedDownload
        }
    }
}
