# Directorios de trabajo
$downloadFolder = "E:\Descargas"
$outputFolder = "D:\Extracciones"

# Ruta a handle.exe
$handlePath = "D:\Programacion\Path\handle.exe"

# Función para verificar si un archivo está en uso por IDMan.exe
function Is-FileInUseByIDMan {
    param (
        [string]$filePath
    )

    $handleOutput = & $handlePath $filePath
    return $handleOutput -match "IDMan.exe"
}

# Función para verificar si un archivo está en uso por Hydra.exe
function Is-FileInUseByHydra {
    param (
        [string]$filePath
    )

    $handleOutput = & $handlePath $filePath
    return $handleOutput -match "aria2c.exe"
}

# Función para verificar y extraer archivos
function Extract-Files {
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse
    foreach ($archive in $filesToExtract) {
        $archiveName = [System.IO.Path]::GetFileNameWithoutExtension($archive.FullName)
        $extractionPath = Join-Path -Path $outputFolder -ChildPath $archiveName

        # Crear carpeta para la extracción
        if (-not (Test-Path -Path $extractionPath)) {
            New-Item -Path $extractionPath -ItemType Directory | Out-Null
        }

        # Esperar hasta que el archivo no esté en uso por IDM o Hydra
        Write-Output "Verificando si $($archive.FullName) está en uso por IDM o Hydra..."
        while (Is-FileInUseByIDMan -filePath $archive.FullName -or Is-FileInUseByHydra -filePath $archive.FullName)) {
            Write-Output "Archivo en uso por IDM o Hydra. Esperando..."
            Start-Sleep -Seconds 5
        }

        # Si el archivo fue usado por Hydra, esperar hasta que ya no lo esté
        if (Is-FileInUseByHydra -filePath $archive.FullName) {
            Write-Output "Archivo usado por Hydra. Esperando a que termine de descargar..."
            while (Is-FileInUseByHydra -filePath $archive.FullName) {
                Write-Output "Archivo aún en uso por Hydra. Esperando..."
                Start-Sleep -Seconds 5
                cls
            }
            cls
            Write-Output "Archivo ya no está en uso por Hydra."
        }

        # Si contiene "SteamRIP", ejecutar instalador
        if ($archive.Name -like "*SteamRIP*") {
            Write-Output "Archivo contiene 'SteamRIP'. Ejecutando instalador..."
            Start-Process -FilePath "python" -ArgumentList "`"D:\Programacion\Python\Automatic Game Instalation\ui.py`"" -NoNewWindow -Wait
            Write-Output "ui.py ejecutado para $($archive.FullName)"
        } else {
            # Si el archivo no es SteamRIP o ya fue manejado por el instalador, extraerlo
            Write-Output "Extrayendo $($archive.FullName) a $extractionPath..."
            $arguments = "x `"$($archive.FullName)`" -o`"$extractionPath`" -aoa"
            Start-Process -FilePath "7z.exe" -ArgumentList $arguments -NoNewWindow -Wait

            # Eliminar archivo después de la extracción
            Remove-Item -Path $archive.FullName -Force
            Write-Output "Archivo eliminado: $($archive.FullName)"
        }
    }
}




# Función para cerrar IDMan.exe
function Close-IDMan {
    if (Get-Process -Name "IDMan" -ErrorAction SilentlyContinue) {
        Write-Output "Cerrando IDM..."
        Stop-Process -Name "IDMan" -Force
        Start-Sleep -Seconds 1  # Dar tiempo a que el proceso se cierre
        cls  # Limpiar la pantalla de la consola
    }
}

# Función para verificar si IDMan.exe está en ejecución
function Is-IDManRunning {
    return Get-Process -Name "IDMan" -ErrorAction SilentlyContinue
}


# Función para verificar si Hydra.exe está en ejecución
function Is-HydraRunning {
    return Get-Process -Name "Hydra" -ErrorAction SilentlyContinue
}

# Bucle principal
while ($true) {
    # Esperar a que IDMan.exe esté en ejecución o que un archivo esté en uso por Hydra.exe
    Write-Output "Esperando a que IDM este en ejecucion o que un archivo este en uso por Hydra..."

    # Aquí se verifica si IDMan.exe está en ejecución o si algún archivo está siendo manejado por Hydra.exe
    while (-not (Is-IDManRunning) -and (Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { Is-FileInUseByHydra -filePath $_.FullName }).Count -eq 0) {
        Start-Sleep -Seconds 5
    }

    Write-Output "IDM o archivo en uso por Hydra detectado. Comenzando la extraccion de archivos..."

    # Verificar si hay archivos para extraer
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse

    if ($filesToExtract.Count -gt 0) {
        # Extraer archivos
        Extract-Files

        # Cerrar IDMan.exe si está en ejecución
        Close-IDMan

        # Esperar a que IDMan.exe o Hydra.exe se vuelva a ejecutar
        Write-Output "Esperando a que IDM o Hydra se vuelvan a iniciar..."
        while (-not (Is-IDManRunning) -and -not (Is-HydraRunning)) {
            Start-Sleep -Seconds 5
        }

        Write-Output "IDM o Hydra detectados nuevamente. Continuando con la siguiente verificacion..."
    } else {
        Write-Output "No hay archivos para extraer."
    }

    # Esperar un intervalo antes de la próxima verificación
    Start-Sleep -Seconds 5
}
