$configPath = Join-Path $PSScriptRoot "config.yaml"
$config = Get-Content $configPath -Raw | ConvertFrom-Yaml
$downloadFolder = $config.paths.download_folder -replace '\\\\', '\'
$excludedFolder = Join-Path $downloadFolder "TempDownload"
$handlePath = "handle.exe"

function Test-FileInUse {
    param (
        [string]$filePath
    )

    $handleOutput = & $handlePath $filePath
    return $handleOutput -match "aria2c.exe"
}

function Install-Game {
    $files = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($archive in $files) {
        Write-Output "Verificando si $($archive.FullName) esta en uso por Hydra..."
        while (Test-FileInUse -filePath $archive.FullName) {
            Write-Output "Archivo en uso por Hydra. Esperando..."
            Start-Sleep -Seconds 5
        }
            Write-Output "Archivo ya no esta en uso por Hydra. Ejecutando instalador..."
            $uiScript = Join-Path $PSScriptRoot "ui.py"
            Start-Process -FilePath "python" -ArgumentList "`"$uiScript`"" -NoNewWindow -Wait
            Write-Output "ui.py ejecutado para $($archive.FullName)"
        else {
            Write-Output "Archivo ya no esta en uso por Hydra."
        }
    }
}

function Test-IDManRunning {
    return Get-Process -Name "IDman" -ErrorAction SilentlyContinue
}

function Test-HydraRunning {
    return Get-Process -Name "Hydra" -ErrorAction SilentlyContinue
}

# Bucle principal
while ($true) {
    Write-Output "Esperando a que un archivo este en uso por Hydra..."

    while (-not (Test-IDManRunning) -and (Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { Test-FileInUse -filePath $_.FullName }).Count -eq 0) {
        Start-Sleep -Seconds 3
    }

    Write-Output "Archivo en uso por Hydra detectado. Comprobando archivos..."

    # Verificar si hay archivos
    $files = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    if ($files.Count -gt 0) {
        Install-Game

        Write-Output "Esperando a que Hydra se vuelva a iniciar..."
        while (-not (Test-IDManRunning) -and -not (Test-HydraRunning)) {
            Start-Sleep -Seconds 3
        }

        Write-Output "Hydra detectado nuevamente. Continuando con la siguiente verificacion..."
    } else {
        Write-Output "No hay archivos."
    }
    Clear-Host
    Start-Sleep -Seconds 3
}