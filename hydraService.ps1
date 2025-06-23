# Directorios de trabajo
$downloadFolder = "E:\Descargas"
$excludedFolder = Join-Path $downloadFolder "TempDownload"

# Ruta a handle.exe
$handlePath = "handle.exe"

# Función para verificar si un archivo está en uso por Hydra.exe
function Test-FileInUse {
    param (
        [string]$filePath
    )

    $handleOutput = & $handlePath $filePath
    return $handleOutput -match "aria2c.exe"
}

# Función para verificar y extraer archivos
function Install-Game {
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse |
                      Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($archive in $filesToExtract) {
        # Esperar hasta que el archivo no esté en uso
        Write-Output "Verificando si $($archive.FullName) está en uso por Hydra..."
        while (Test-FileInUse -filePath $archive.FullName) {
            Write-Output "Archivo en uso por Hydra. Esperando..."
            Start-Sleep -Seconds 5
        }

        # Verificar si el archivo fue usado por Hydra.exe
        if (Test-FileInUse -filePath $archive.FullName) {
            Write-Output "Archivo usado por Hydra. Esperando a que termine de descargar..."
            while (Test-FileInUse -filePath $archive.FullName) {
                Write-Output "Archivo aún en uso por Hydra. Esperando..."
                Start-Sleep -Seconds 5
            }
            Write-Output "Archivo ya no está en uso por Hydra. Ejecutando instalador..."
            $uiScript = Join-Path $PSScriptRoot "ui.py"
            Start-Process -FilePath "python" -ArgumentList "`"$uiScript`"" -NoNewWindow -Wait
            Write-Output "ui.py ejecutado para $($archive.FullName)"
        } else {
            Write-Output "Archivo ya no está en uso por Hydra."
        }
    }

}

function Test-IDManRunning {
    return Get-Process -Name "IDman" -ErrorAction SilentlyContinue
}

# Función para verificar si Hydra.exe está en ejecución
function Test-HydraRunning {
    return Get-Process -Name "Hydra" -ErrorAction SilentlyContinue
}

# Bucle principal
while ($true) {
    Write-Output "Esperando a que un archivo esté en uso por Hydra..."

    while (-not (Test-IDManRunning) -and (Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { Test-FileInUse -filePath $_.FullName }).Count -eq 0) {
        Start-Sleep -Seconds 3
    }

    Write-Output "Archivo en uso por Hydra detectado. Comprobando archivos..."

    # Verificar si hay archivos
    $files = Get-ChildItem -Path $downloadFolder -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    if ($files.Count -gt 0) {
        # Extraer archivos
        Install-Game

        # Esperar a que Hydra.exe se vuelva a ejecutar
        Write-Output "Esperando a que Hydra se vuelva a iniciar..."
        while (-not (Test-IDManRunning) -and -not (Test-HydraRunning)) {
            Start-Sleep -Seconds 3
        }

        Write-Output "Hydra detectado nuevamente. Continuando con la siguiente verificacion..."
    } else {
        Write-Output "No hay archivos comprimidos para extraer."
    }
    Clear-Host
    Start-Sleep -Seconds 3
}