[CmdletBinding()]
param(
    [string]$ConfigPath,
    [string[]]$Services,
    [switch]$SkipInstall,
    [switch]$SkipDatabase,
    [switch]$SkipMigrate,
    [switch]$SkipHealthCheck,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $scriptDirectory = Split-Path -Parent $PSCommandPath
    $ConfigPath = Join-Path $scriptDirectory "start-local-stack.config.json"
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

function Get-ObjectPropertyValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Object,
        [Parameter(Mandatory = $true)]
        [string]$FieldName,
        [switch]$Required
    )

    $property = $Object.PSObject.Properties[$FieldName]
    if ($null -eq $property) {
        if ($Required) {
            throw "Config field '$FieldName' is required."
        }
        return $null
    }

    return $property.Value
}

function Get-RequiredString {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Value,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $result = [string]$Value
    if ([string]::IsNullOrWhiteSpace($result)) {
        throw "Config field '$FieldName' cannot be empty."
    }
    return $result
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

function Assert-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$CommandName' was not found in PATH."
    }
}

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComposeFile,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [switch]$DryRun
    )

    Write-Host ("`n> docker compose -f " + $ComposeFile + " " + ($Arguments -join " "))
    if ($DryRun) {
        return
    }

    & docker compose -f $ComposeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker compose command failed with exit code $LASTEXITCODE."
    }
}

function Ensure-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string]$EnvExamplePath,
        [Parameter(Mandatory = $true)]
        [string]$EnvFilePath,
        [Parameter(Mandatory = $true)]
        [switch]$DryRun
    )

    $envExample = Resolve-PathFromConfig -BaseDirectory $WorkingDirectory -PathValue $EnvExamplePath -FieldName "env_example"
    $envFile = Resolve-PathFromConfig -BaseDirectory $WorkingDirectory -PathValue $EnvFilePath -FieldName "env_file"

    if (-not (Test-Path -LiteralPath $envExample)) {
        throw "Env template not found: $envExample"
    }

    if (Test-Path -LiteralPath $envFile) {
        Write-Host "Env file already exists: $envFile"
        return
    }

    Write-Host "Create env file from template: $envFile"
    if (-not $DryRun) {
        Copy-Item -LiteralPath $envExample -Destination $envFile
    }
}

function Convert-ToPowerShellLiteral {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    return $Value.Replace("'", "''")
}

function Start-ServiceShell {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ShellExecutable,
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [string]$WindowTitle,
        [string]$InstallCommand,
        [string]$PrepareCommand,
        [Parameter(Mandatory = $true)]
        [string]$StartCommand,
        [Parameter(Mandatory = $true)]
        [switch]$SkipInstall,
        [Parameter(Mandatory = $true)]
        [switch]$SkipPrepare,
        [Parameter(Mandatory = $true)]
        [switch]$DryRun
    )

    $escapedDirectory = Convert-ToPowerShellLiteral -Value $WorkingDirectory
    $commandParts = @(
        '$ErrorActionPreference = ''Stop'''
        "Set-Location -LiteralPath '$escapedDirectory'"
    )

    if (-not [string]::IsNullOrWhiteSpace($WindowTitle)) {
        $escapedTitle = Convert-ToPowerShellLiteral -Value $WindowTitle
        $commandParts += "`$host.UI.RawUI.WindowTitle = '$escapedTitle'"
    }

    if (-not $SkipInstall -and -not [string]::IsNullOrWhiteSpace($InstallCommand)) {
        $commandParts += $InstallCommand
    }

    if (-not $SkipPrepare -and -not [string]::IsNullOrWhiteSpace($PrepareCommand)) {
        $commandParts += $PrepareCommand
    }

    $commandParts += $StartCommand
    $commandText = $commandParts -join "; "

    Write-Host ("`n[" + $ServiceName + "] " + $commandText)
    if ($DryRun) {
        return
    }

    Start-Process -FilePath $ShellExecutable `
        -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $commandText) `
        -WorkingDirectory $WorkingDirectory | Out-Null
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
        [int]$TimeoutSeconds
    )

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

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$configFile = (Resolve-Path -LiteralPath $ConfigPath).Path
$configDirectory = Split-Path -Parent $configFile
$config = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8 | ConvertFrom-Json

$composeFileValue = Get-ObjectPropertyValue -Object $config -FieldName "compose_file" -Required
$composeFile = Resolve-PathFromConfig -BaseDirectory $configDirectory -PathValue ([string]$composeFileValue) -FieldName "compose_file"
$databaseService = [string](Get-ObjectPropertyValue -Object $config -FieldName "database_service")
$shellExecutable = Get-RequiredString -Value (Get-ObjectPropertyValue -Object $config -FieldName "shell_executable" -Required) -FieldName "shell_executable"
$defaultServices = Get-RequiredStringArray -Value (Get-ObjectPropertyValue -Object $config -FieldName "default_services" -Required) -FieldName "default_services"
$serviceConfigs = Get-ObjectPropertyValue -Object $config -FieldName "services" -Required
$healthCheck = Get-ObjectPropertyValue -Object $config -FieldName "health_check" -Required

$retries = Get-RequiredInt -Value (Get-ObjectPropertyValue -Object $healthCheck -FieldName "retries" -Required) -FieldName "health_check.retries"
$intervalSeconds = Get-RequiredInt -Value (Get-ObjectPropertyValue -Object $healthCheck -FieldName "interval_seconds" -Required) -FieldName "health_check.interval_seconds"
$timeoutSeconds = Get-RequiredInt -Value (Get-ObjectPropertyValue -Object $healthCheck -FieldName "timeout_seconds" -Required) -FieldName "health_check.timeout_seconds"

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
    throw "No services selected."
}

$availableServices = @($serviceConfigs.PSObject.Properties.Name)
$unknownServices = @($targetServices | Where-Object { $_ -notin $availableServices })
if ($unknownServices.Count -gt 0) {
    throw "Unknown services: $($unknownServices -join ", "). Available: $($availableServices -join ", ")"
}

Assert-CommandAvailable -CommandName $shellExecutable

if (-not $SkipDatabase) {
    Assert-CommandAvailable -CommandName "docker"
    Invoke-DockerCompose -ComposeFile $composeFile -Arguments @("up", "-d", $databaseService) -DryRun:$DryRun
}

$healthUrls = [System.Collections.Generic.List[string]]::new()

foreach ($serviceName in $targetServices) {
    $serviceConfig = Get-ObjectPropertyValue -Object $serviceConfigs -FieldName $serviceName -Required
    $workingDirectory = Resolve-PathFromConfig -BaseDirectory $configDirectory -PathValue ([string](Get-ObjectPropertyValue -Object $serviceConfig -FieldName "working_directory" -Required)) -FieldName "$serviceName.working_directory"
    $requiredCommand = Get-RequiredString -Value (Get-ObjectPropertyValue -Object $serviceConfig -FieldName "required_command" -Required) -FieldName "$serviceName.required_command"
    $envExamplePath = Get-RequiredString -Value (Get-ObjectPropertyValue -Object $serviceConfig -FieldName "env_example" -Required) -FieldName "$serviceName.env_example"
    $envFilePath = Get-RequiredString -Value (Get-ObjectPropertyValue -Object $serviceConfig -FieldName "env_file" -Required) -FieldName "$serviceName.env_file"
    $windowTitle = [string](Get-ObjectPropertyValue -Object $serviceConfig -FieldName "window_title")
    $installCommand = [string](Get-ObjectPropertyValue -Object $serviceConfig -FieldName "install_command")
    $prepareCommand = [string](Get-ObjectPropertyValue -Object $serviceConfig -FieldName "prepare_command")
    $startCommand = Get-RequiredString -Value (Get-ObjectPropertyValue -Object $serviceConfig -FieldName "start_command" -Required) -FieldName "$serviceName.start_command"
    $serviceHealthUrls = @((Get-ObjectPropertyValue -Object $serviceConfig -FieldName "health_urls") | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

    Assert-CommandAvailable -CommandName $requiredCommand
    Ensure-EnvFile -WorkingDirectory $workingDirectory -EnvExamplePath $envExamplePath -EnvFilePath $envFilePath -DryRun:$DryRun
    Start-ServiceShell `
        -ShellExecutable $shellExecutable `
        -ServiceName $serviceName `
        -WorkingDirectory $workingDirectory `
        -WindowTitle $windowTitle `
        -InstallCommand $installCommand `
        -PrepareCommand $prepareCommand `
        -StartCommand $startCommand `
        -SkipInstall:$SkipInstall `
        -SkipPrepare:($SkipMigrate -or [string]::IsNullOrWhiteSpace($prepareCommand)) `
        -DryRun:$DryRun

    foreach ($url in $serviceHealthUrls) {
        if (-not $healthUrls.Contains($url)) {
            $healthUrls.Add($url)
        }
    }
}

if (-not $SkipHealthCheck -and -not $DryRun) {
    foreach ($url in $healthUrls) {
        Test-HttpEndpoint -Url $url -Retries $retries -IntervalSeconds $intervalSeconds -TimeoutSeconds $timeoutSeconds
    }
}

Write-Host "`nLocal startup flow completed for services: $($targetServices -join ", ")"
