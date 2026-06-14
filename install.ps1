#requires -Version 5

[CmdletBinding()]
param(
    [string]$CodexHome = (Join-Path $HOME '.codex'),

    [string]$AgentsHome = (Join-Path $HOME '.agents'),

    [string]$Repo,

    [switch]$RepoOnly,

    [switch]$WithReverseCore,

    [switch]$StartReverseServices,

    [switch]$VerifyReverseReady,

    [string]$ReverseCapabilities,

    [switch]$DryRun,

    [switch]$Backup,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$KitRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.'))
$ReverseBootstrapScriptRel = 'reverse-skill\skills\scripts\bootstrap-reverse.ps1'

function Write-Log {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host $Message
}

function Resolve-AbsolutePath {
    param([Parameter(Mandatory = $true)][string]$PathValue)

    return [System.IO.Path]::GetFullPath($PathValue)
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$Preview
    )

    if ($DryRun) {
        Write-Host "[dry-run] $Preview"
        return
    }

    & $Action
}

function Get-ReverseBootstrapCapabilities {
    if (-not [string]::IsNullOrWhiteSpace($ReverseCapabilities)) {
        return @(
            foreach ($item in ($ReverseCapabilities -split ',')) {
                $trimmed = $item.Trim()
                if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                    $trimmed
                }
            }
        )
    }

    return @(
        'jadx',
        'apktool',
        'frida',
        'r2',
        'adb',
        'nmap',
        'sqlmap',
        'ffuf',
        'nuclei',
        'binwalk',
        'graphviz',
        'jshookmcp',
        'anything-analyzer',
        'ghidra-mcp'
    )
}

function Copy-ToolkitFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Target
    )

    $sourceItem = Get-Item -LiteralPath $Source -ErrorAction Stop
    $targetParent = Split-Path -Path $Target -Parent
    if (-not [string]::IsNullOrWhiteSpace($targetParent) -and -not (Test-Path -LiteralPath $targetParent)) {
        Invoke-Step -Preview "New-Item -ItemType Directory -Path `"$targetParent`" -Force" -Action {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }
    }

    if (Test-Path -LiteralPath $Target) {
        if ((Get-Item -LiteralPath $Target).PSIsContainer) {
            throw "Target exists as a directory: $Target"
        }

        if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash) {
            Write-Log "skip identical: $Target"
            return
        }

        if ($Force) {
            Write-Log "replace: $Target"
        }
        elseif ($Backup) {
            $backupPath = "$Target.bak-$(Get-Date -Format 'yyyyMMddHHmmss')"
            Write-Log "backup: $Target -> $backupPath"
            Invoke-Step -Preview "Copy-Item -LiteralPath `"$Target`" -Destination `"$backupPath`" -Force" -Action {
                Copy-Item -LiteralPath $Target -Destination $backupPath -Force
            }
        }
        else {
            Write-Log "conflict: $Target"
            Write-Log "  use -Backup to preserve the current file, or -Force to replace it"
            throw "Conflict detected: $Target"
        }
    }
    else {
        Write-Log "create: $Target"
    }

    Invoke-Step -Preview "Copy-Item -LiteralPath `"$Source`" -Destination `"$Target`" -Force" -Action {
        Copy-Item -LiteralPath $Source -Destination $Target -Force
    }
}

function Copy-ToolkitTree {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )

    $rootItem = Get-Item -LiteralPath $SourceRoot -ErrorAction Stop
    foreach ($file in Get-ChildItem -LiteralPath $SourceRoot -Recurse -File | Sort-Object FullName) {
        $relative = $file.FullName.Substring($rootItem.FullName.Length).TrimStart('\', '/')
        $target = Join-Path $TargetRoot $relative
        if ($relative -ieq 'docs\architecture.md' -and -not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath (Join-Path $TargetRoot 'docs'))) {
            $existingArchitecture = Get-ChildItem -LiteralPath (Join-Path $TargetRoot 'docs') -File |
                Where-Object { $_.Name -ieq 'architecture.md' } |
                Select-Object -First 1
            if ($existingArchitecture) {
                Write-Log "conflict: $($existingArchitecture.FullName)"
                Write-Log "  existing architecture doc differs by case; update references manually instead of creating a duplicate"
                throw "Case-insensitive architecture.md conflict"
            }
        }
        Copy-ToolkitFile -Source $file.FullName -Target $target
    }
}

function Install-GlobalAgents {
    Copy-ToolkitFile -Source (Join-Path $KitRoot 'global\AGENTS.md') -Target (Join-Path $CodexHome 'AGENTS.md')
}

function Install-ReverseRouterSkill {
    Copy-ToolkitFile `
        -Source (Join-Path $KitRoot 'reverse-skill-router\reverse-engineering\SKILL.md') `
        -Target (Join-Path $CodexHome 'skills\reverse-engineering\SKILL.md')
}

function Install-ReversePack {
    Copy-ToolkitTree -SourceRoot (Join-Path $KitRoot 'reverse-skill') -TargetRoot (Join-Path $CodexHome 'reverse-skill')
}

function Install-Skills {
    $skillsRoot = Join-Path $KitRoot 'skills'
    foreach ($skillDir in Get-ChildItem -LiteralPath $skillsRoot -Directory | Sort-Object Name) {
        Copy-ToolkitTree -SourceRoot $skillDir.FullName -TargetRoot (Join-Path $AgentsHome "skills\$($skillDir.Name)")
    }
}

function Install-RepoTemplate {
    if ([string]::IsNullOrWhiteSpace($Repo)) {
        return
    }
    if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
        throw "target repo does not exist: $Repo"
    }
    Copy-ToolkitTree -SourceRoot (Join-Path $KitRoot 'repo-template') -TargetRoot $Repo
}

function Invoke-ReverseBootstrap {
    $bootstrapScript = Join-Path $KitRoot $ReverseBootstrapScriptRel
    $installedBootstrapScript = Join-Path $CodexHome $ReverseBootstrapScriptRel
    if (-not $DryRun -and (Test-Path -LiteralPath $installedBootstrapScript)) {
        $bootstrapScript = $installedBootstrapScript
    }
    if (-not (Test-Path -LiteralPath $bootstrapScript)) {
        throw "reverse bootstrap script missing: $bootstrapScript"
    }

    $capabilities = Get-ReverseBootstrapCapabilities
    if ($capabilities.Count -eq 0) {
        throw 'reverse bootstrap capability list is empty'
    }

    $previewArgs = @($capabilities)
    if ($StartReverseServices) {
        $previewArgs += '-StartServices'
    }
    $preview = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$bootstrapScript`" -Capability @('$($capabilities -join ''',''')')"
    if ($StartReverseServices) {
        $preview += ' -StartServices'
    }

    Invoke-Step -Preview $preview -Action {
        $params = @{
            FilePath = 'powershell.exe'
            ArgumentList = @(
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-File', $bootstrapScript,
                '-Capability'
            ) + $capabilities
            NoNewWindow = $true
            Wait = $true
            PassThru = $true
        }
        $env:CODEX_CONFIG_PATH = (Join-Path $CodexHome 'config.toml')
        $env:CLAUDE_MCP_CONFIG = (Join-Path $HOME '.claude\mcp.json')
        if ($StartReverseServices) {
            $params.ArgumentList += '-StartServices'
        }
        $process = Start-Process @params
        if ($process.ExitCode -ne 0) {
            throw "reverse bootstrap failed with exit code $($process.ExitCode)"
        }
    }
}

function Invoke-ReverseReadyVerifier {
    $verifyScript = Join-Path $KitRoot 'scripts\verify_reverse_ready.py'
    if (-not (Test-Path -LiteralPath $verifyScript)) {
        throw "reverse readiness verifier missing: $verifyScript"
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw 'python or python3 is required to run verify_reverse_ready.py'
    }

    $preview = "$($python.Source) `"$verifyScript`" --user-home `"$HOME`" --codex-config `"$CodexHome\config.toml`""
    Invoke-Step -Preview $preview -Action {
        & $python.Source $verifyScript --user-home $HOME --codex-config (Join-Path $CodexHome 'config.toml')
        if ($LASTEXITCODE -ne 0) {
            throw "verify_reverse_ready.py failed with exit code $LASTEXITCODE"
        }
    }
}

if ($Backup -and $Force) {
    throw '-Backup and -Force cannot be used together'
}

if ($RepoOnly -and [string]::IsNullOrWhiteSpace($Repo)) {
    throw '-RepoOnly requires -Repo PATH'
}

if ($StartReverseServices -and -not $WithReverseCore) {
    throw '-StartReverseServices requires -WithReverseCore'
}

$CodexHome = Resolve-AbsolutePath -PathValue $CodexHome
$AgentsHome = Resolve-AbsolutePath -PathValue $AgentsHome
if (-not [string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = Resolve-AbsolutePath -PathValue $Repo
}

if (-not $RepoOnly) {
    Install-GlobalAgents
    Install-ReverseRouterSkill
    Install-ReversePack
    Install-Skills
}
Install-RepoTemplate

if (-not $RepoOnly -and $WithReverseCore) {
    Write-Log 'bootstrap reverse core tools'
    Invoke-ReverseBootstrap
}

if (-not $RepoOnly -and ($VerifyReverseReady -or $WithReverseCore)) {
    Invoke-ReverseReadyVerifier
}

Write-Log 'Install plan complete.'
if ($DryRun) {
    Write-Log 'No files were written because -DryRun was used.'
}
