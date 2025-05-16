# Directorios de trabajo
$downloadFolder = "E:\Descargas"
$outputFolder = "D:\Extracciones"
$excludedFolder = Join-Path $downloadFolder "TempDownload"

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
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($archive in $filesToExtract) {
        $archiveName = [System.IO.Path]::GetFileNameWithoutExtension($archive.FullName)
        $extractionPath = Join-Path -Path $outputFolder -ChildPath $archiveName

        # Verificar si el archivo está protegido con contraseña (usando 7zAES o AES en el método)
        Write-Output "Verificando cifrado en $($archive.FullName)..."
        $7zOutput = & 7z.exe l "`"$($archive.FullName)`"" 2>&1
        if ($7zOutput -match "Method =.*(7zAES|AES)") {
            Write-Output "Archivo cifrado detectado (AES). Se omite: $($archive.FullName)"
            $notifEncryptScript = Join-Path $PSScriptRoot "notificationEncrypted.py"
            Write-Output "Ejecutando notificación de extracción: $notifEncryptScript"
            & python $notifEncryptScript
            continue
        }

        # Crear carpeta para la extracción
        if (-not (Test-Path -Path $extractionPath)) {
            New-Item -Path $extractionPath -ItemType Directory | Out-Null
        }

        # Esperar hasta que el archivo no esté en uso
        Write-Output "Verificando si $($archive.FullName) está en uso por IDM o Hydra..."
        while (Is-FileInUseByIDMan -filePath $archive.FullName -or Is-FileInUseByHydra -filePath $archive.FullName) {
            Write-Output "Archivo en uso por IDM o Hydra. Esperando..."
            Start-Sleep -Seconds 5
        }

        # Verificar si el archivo fue usado por Hydra.exe
        if (Is-FileInUseByHydra -filePath $archive.FullName) {
            Write-Output "Archivo usado por Hydra. Esperando a que termine de descargar..."
            while (Is-FileInUseByHydra -filePath $archive.FullName) {
                Write-Output "Archivo aún en uso por Hydra. Esperando..."
                Start-Sleep -Seconds 5
                # cls
            }
            # cls
            Write-Output "Archivo ya no está en uso por Hydra. Ejecutando instalador..."

            Start-Process -FilePath "python" -ArgumentList "`"D:\Programacion\Python\Automatic Game Instalation\ui.py`"" -NoNewWindow -Wait
            Write-Output "ui.py ejecutado para $($archive.FullName)"
        } else {
            Write-Output "Extrayendo $($archive.FullName) a $extractionPath..."
            $arguments = "x `"$($archive.FullName)`" -o`"$extractionPath`" -aoa"
            Start-Process -FilePath "7z.exe" -ArgumentList $arguments -NoNewWindow -Wait

            # Eliminar archivo después de la extracción
            Remove-Item -Path $archive.FullName -Force
            Write-Output "Archivo eliminado: $($archive.FullName)"

            # Ejecutar notificationExtract.py después de la extracción
            $notifScript = Join-Path $PSScriptRoot "notificationExtract.py"
            Write-Output "Ejecutando notificación de extracción: $notifScript"
            & python $notifScript
        }
    }
}






# Función para cerrar IDMan.exe
function Close-IDMan {
    if (Get-Process -Name "IDMan" -ErrorAction SilentlyContinue) {
        Write-Output "Cerrando IDM..."
        Stop-Process -Name "IDMan" -Force
        Start-Sleep -Seconds 1  # Dar tiempo a que el proceso se cierre
        # cls  # Limpiar la pantalla de la consola
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
    Write-Output "Esperando a que IDM esté en ejecucion o que un archivo esté en uso por Hydra..."

    while (-not (Is-IDManRunning) -and (Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { Is-FileInUseByHydra -filePath $_.FullName }).Count -eq 0) {
        Start-Sleep -Seconds 3
    }

    Write-Output "IDM o archivo en uso por Hydra detectado. Comprobando archivos..."

    # Obtener todos los archivos
    $allFiles = Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($file in $allFiles) {
        $extension = $file.Extension.ToLower()
    
        # Ignorar archivos .tmp, .temp, .aria2
        if ($extension -eq ".tmp" -or $extension -eq ".temp" -or $extension -eq ".aria2" -or $extension -eq ".crdownload") {
            Write-Output "Ignorando archivo temporal: $($file.FullName)"
            continue
        }
    
        if ($extension -ne ".rar" -and $extension -ne ".zip" -and $extension -ne ".7z") {
            # Archivo NO es comprimido, mover a Extracciones
            $destination = Join-Path -Path $outputFolder -ChildPath $file.Name
            Write-Output "Moviendo archivo no comprimido: $($file.FullName) -> $destination"
            Move-Item -Path $file.FullName -Destination $destination -Force
    
            Close-IDMan
            # Ejecutar notificationExtract.py
            $notifScript = Join-Path $PSScriptRoot "notificationExtract.py"
            Write-Output "Ejecutando notificación de archivo movido: $notifScript"
            & python $notifScript
        }
    }
    

    # Verificar si hay archivos comprimidos para extraer
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    if ($filesToExtract.Count -gt 0) {
        # Extraer archivos
        Extract-Files

        # Cerrar IDMan.exe si está en ejecución
        Close-IDMan

        # Esperar a que IDMan.exe o Hydra.exe se vuelva a ejecutar
        Write-Output "Esperando a que IDM o Hydra se vuelvan a iniciar..."
        while (-not (Is-IDManRunning) -and -not (Is-HydraRunning)) {
            Start-Sleep -Seconds 3
        }

        Write-Output "IDM o Hydra detectados nuevamente. Continuando con la siguiente verificacion..."
    } else {
        Write-Output "No hay archivos comprimidos para extraer."
    }
    cls
    Start-Sleep -Seconds 3
}

