[CmdletBinding()]
param(
    [string]$ConfigPath,
    [string[]]$Services,
    [switch]$Rebuild,
    [switch]$SkipHealthCheck,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $scriptDirectory = Split-Path -Parent $PSCommandPath
    $ConfigPath = Join-Path $scriptDirectory "restart-services.config.json"
}

function Resolve-PathFromConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseDirectory,
        [Parameter(Mandatory = $true)]
        [string]$PathValue,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        throw "Config field '$FieldName' cannot be empty."
    }

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $BaseDirectory $PathValue))
}

function Get-RequiredStringArray {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Value,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $result = @($Value | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($result.Count -eq 0) {
        throw "Config field '$FieldName' must contain at least one value."
    }
    return $result
}

function Get-RequiredInt {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Value,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    if ($null -eq $Value) {
        throw "Config field '$FieldName' is required."
    }

    try {
        return [int]$Value
    }
    catch {
        throw "Config field '$FieldName' must be an integer."
    }
}

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [Parameter(Mandatory = $true)]
        [switch]$DryRun
    )

    Write-Host ("`n> docker " + ($Args -join " "))
    if ($DryRun) {
        return @()
    }

    $output = & docker @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed with exit code $LASTEXITCODE."
    }
    return $output
}

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [int]$Retries,
        [Parameter(Mandatory = $true)]
        [int]$IntervalSeconds,
        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds,
        [Parameter(Mandatory = $true)]
        [switch]$DryRun
    )

    if ($DryRun) {
        Write-Host "DRY RUN: skip health check -> $Url"
        return
    }

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSeconds -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Host "Health check passed: $Url (status $($response.StatusCode))"
                return
            }
        }
        catch {
            if ($attempt -eq $Retries) {
                throw "Health check failed for '$Url' after $Retries attempts."
            }
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Install Docker Desktop and ensure 'docker' is available in PATH."
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$configFile = (Resolve-Path -LiteralPath $ConfigPath).Path
$configDir = Split-Path -Parent $configFile
$config = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8 | ConvertFrom-Json

$composeFile = Resolve-PathFromConfig -BaseDirectory $configDir -PathValue ([string]$config.compose_file) -FieldName "compose_file"
if (-not (Test-Path -LiteralPath $composeFile)) {
    throw "Compose file not found: $composeFile"
}

$defaultServices = Get-RequiredStringArray -Value $config.default_services -FieldName "default_services"
$targetServices = if ($Services -and $Services.Count -gt 0) { $Services } else { $defaultServices }
$targetServices = @(
    $targetServices |
        ForEach-Object { [string]$_ } |
        ForEach-Object { $_ -split "," } |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)
if ($targetServices.Count -eq 0) {
    throw "No target services provided."
}

$healthUrls = @($config.health_urls | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
$healthCheck = $config.health_check
$retries = Get-RequiredInt -Value $healthCheck.retries -FieldName "health_check.retries"
$intervalSeconds = Get-RequiredInt -Value $healthCheck.interval_seconds -FieldName "health_check.interval_seconds"
$timeoutSeconds = Get-RequiredInt -Value $healthCheck.timeout_seconds -FieldName "health_check.timeout_seconds"

$composePrefix = @("compose", "-f", $composeFile)
$availableServicesOutput = Invoke-Docker -Args ($composePrefix + @("config", "--services")) -DryRun:$DryRun
if (-not $DryRun) {
    $availableServices = @($availableServicesOutput | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $unknownServices = @($targetServices | Where-Object { $_ -notin $availableServices })
    if ($unknownServices.Count -gt 0) {
        throw "Unknown services: $($unknownServices -join ", "). Available: $($availableServices -join ", ")"
    }
}

$upArgs = @("up", "-d")
if ($Rebuild) {
    $upArgs += "--build"
}
$upArgs += $targetServices

Invoke-Docker -Args ($composePrefix + $upArgs) -DryRun:$DryRun | Out-Null
Invoke-Docker -Args ($composePrefix + @("ps")) -DryRun:$DryRun | Out-Null

if (-not $SkipHealthCheck -and $healthUrls.Count -gt 0) {
    foreach ($url in $healthUrls) {
        Test-HttpEndpoint -Url $url -Retries $retries -IntervalSeconds $intervalSeconds -TimeoutSeconds $timeoutSeconds -DryRun:$DryRun
    }
}

Write-Host "`nRestart flow completed for services: $($targetServices -join ", ")"
