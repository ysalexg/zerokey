# Directorios de trabajo
$downloadFolder = "E:\Descargas"
$outputFolder = "D:\Extracciones"
$excludedFolder = Join-Path $downloadFolder "TempDownload"
$folderToCheck = "E:\Descargas\TempDownload\DwnlData\Alex"
# Esto elimina todos los archivos temporales y sus respectivas claves de registro, ya no se puede reanudar descargas
Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
$key = '\d+'
Get-ItemProperty 'HKCU:\SOFTWARE\DownloadManager\*' | Where-Object { $_.PSChildName -match $key } | Select-Object -ExpandProperty PSPath | Remove-Item -Recurse -Verbose -ErrorAction SilentlyContinue

# Ruta a handle.exe
$handlePath = "handle.exe"

# Función para verificar si un archivo está en uso por IDMan.exe
function Is-CompressedFileInUseByIDMan {
    param (
        [string]$filePath
    )

    $handleOutput = & $handlePath $filePath
    return $handleOutput -match "IDMan.exe"
}

function Get-FoldersInUseByIDMan {
    $foldersInUse = @()
    $subFolders = Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue
    foreach ($subFolder in $subFolders) {
        $handleOutput = & $handlePath $subFolder.FullName
        if ($handleOutput -match "IDMan.exe") {
            $foldersInUse += $subFolder.FullName
        }
    }
    return $foldersInUse
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
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse |
                      Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($archive in $filesToExtract) {
        $archiveName    = [System.IO.Path]::GetFileNameWithoutExtension($archive.FullName)
        $extractionPath = Join-Path -Path $outputFolder -ChildPath $archiveName

        Write-Output "Verificando cifrado en $($archive.FullName)..."
        $extension    = $archive.Extension.ToLowerInvariant()
        $isEncrypted  = $false

        if ($extension -eq ".rar") {
            # Para .rar: listar usando -p (vacío)
            $outputLines = & 7z.exe l '-p' '' $archive.FullName 2>&1
            $allOutput   = $outputLines -join "`n"
            Write-Output ">> DEBUG 7z l -p output:`n$allOutput"

            if ($allOutput -match "ERROR:.*Cannot open encrypted archive" `
                -or $allOutput -match "Wrong password") {
                $isEncrypted = $true
            }
        }
        else {
            # Para .zip y .7z: primero intentar listar con -p (vacío) como en .rar
            $outputLines = & 7z.exe l '-p' '' $archive.FullName 2>&1
            $allOutput   = $outputLines -join "`n"
            Write-Output ">> DEBUG 7z l -p output:`n$allOutput"

            if ($allOutput -match "ERROR:.*Cannot open encrypted archive" `
            -or $allOutput -match "Wrong password") {
            $isEncrypted = $true
            } else {
            # Si no hay error de cifrado, comprobar método AES
            $outputLines = & 7z.exe l $archive.FullName 2>&1
            $allOutput   = $outputLines -join "`n"
            Write-Output ">> DEBUG 7z l output:`n$allOutput"

            if ($allOutput -match "Method\s*=\s*.*(7zAES|AES)") {
                $isEncrypted = $true
            }
            }
        }

        if ($isEncrypted) {
            Write-Output "🚫 Archivo cifrado detectado. Se omite: $($archive.FullName)"
            $notifEncryptScript = Join-Path $PSScriptRoot "notifications\notificationEncrypted.py"
            Write-Output "Ejecutando notificación de extracción: $notifEncryptScript"
            & python $notifEncryptScript
            if ((Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count -eq 0){
                Close-IDMan
            }
            continue
        }
        # Crear carpeta para la extracción
        if (-not (Test-Path -Path $extractionPath)) {
            New-Item -Path $extractionPath -ItemType Directory | Out-Null
        }

        # Esperar hasta que el archivo no esté en uso
        Write-Output "Verificando si $($archive.FullName) está en uso por IDM o Hydra..."
        while (Is-CompressedFileInUseByIDMan -filePath $archive.FullName -or Is-FileInUseByHydra -filePath $archive.FullName) {
            Write-Output "Archivo en uso por IDM o Hydra. Esperando..."
            Start-Sleep -Seconds 5
        }

        # Verificar si el archivo fue usado por Hydra.exe
        if (Is-FileInUseByHydra -filePath $archive.FullName) {
            Write-Output "Archivo usado por Hydra. Esperando a que termine de descargar..."
            while (Is-FileInUseByHydra -filePath $archive.FullName) {
                Write-Output "Archivo aún en uso por Hydra. Esperando..."
                Start-Sleep -Seconds 5
            }
            Write-Output "Archivo ya no está en uso por Hydra. Ejecutando instalador..."
            $uiScript = Join-Path $PSScriptRoot "ui.py"
            Start-Process -FilePath "python" -ArgumentList "`"$uiScript`"" -NoNewWindow -Wait
            Write-Output "ui.py ejecutado para $($archive.FullName)"
        } else {
            Write-Output "Extrayendo $($archive.FullName) a $extractionPath..."
            $arguments = "x `"$($archive.FullName)`" -o`"$extractionPath`" -aoa"
            Start-Process -FilePath "7z.exe" -ArgumentList $arguments -NoNewWindow -Wait

            # Eliminar archivo después de la extracción
            Remove-Item -Path $archive.FullName -Force
            Write-Output "Archivo eliminado: $($archive.FullName)"

            # Ejecutar notificationExtract.py después de la extracción
            $notifScript = Join-Path $PSScriptRoot "notifications\notificationExtract.py"
            $Count = (Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count
            Write-Output "$Count archivos en $folderToCheck"
            Write-Output "Ejecutando notificación de extracción: $notifScript"
            & python $notifScript
            if ((Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count -eq 0){
                Close-IDMan
            }
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
# Variables para rastrear carpetas en uso y sus archivos
$prevFoldersInUse = @{}
$prevFoldersList  = @()

while ($true) {
    Write-Output "Verificando carpetas en uso por IDM..."

    # Obtener carpetas actualmente en uso por IDM
    $currentFoldersInUse = @{}
    $foldersInUseList = Get-FoldersInUseByIDMan

    foreach ($folder in $foldersInUseList) {
        $files = Get-ChildItem -Path $folder -File -ErrorAction SilentlyContinue
        $currentFoldersInUse[$folder] = $files.FullName
    }

    # Detectar carpetas que ya no están en uso (estaban antes, pero no ahora)
    $releasedFolders = @()
    foreach ($prevFolder in $prevFoldersList) {
        if ($foldersInUseList -notcontains $prevFolder) {
            $releasedFolders += $prevFolder
        }
    }

    # Procesar archivos de carpetas liberadas
    foreach ($releasedFolder in $releasedFolders) {
        $prevFiles = $prevFoldersInUse[$releasedFolder]
        foreach ($filePath in $prevFiles) {
            $fileName = [System.IO.Path]::GetFileName($filePath)
            $downloadedFile = Join-Path $downloadFolder $fileName
            if (Test-Path $downloadedFile) {
                $destination = Join-Path $outputFolder $fileName
                Write-Output "Moviendo archivo liberado de IDM: $downloadedFile -> $destination"
                Move-Item -Path $downloadedFile -Destination $destination -Force

                # Ejecutar notificación para archivo movido
                $notifScript = Join-Path $PSScriptRoot "notifications\notificationExtract.py"
                Write-Output "Ejecutando notificación de archivo movido: $notifScript"
                & python $notifScript
                if ((Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count -eq 0){
                    Close-IDMan
                }
            }
        }
    }

    # Actualizar estado previo
    $prevFoldersInUse = $currentFoldersInUse.Clone()
    $prevFoldersList  = $foldersInUseList

    Write-Output "Esperando a que IDM esté en ejecucion o que un archivo esté en uso por Hydra..."

    while (-not (Is-IDManRunning) -and (Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { Is-FileInUseByHydra -filePath $_.FullName }).Count -eq 0) {
        Start-Sleep -Seconds 3
        Start-Process -FilePath "soundvolumeview.exe" -ArgumentList '/SetVolume "System Sounds" 20' -NoNewWindow
	    Start-Process -FilePath "soundvolumeview.exe" -ArgumentList '/SetVolume "Playnite" 30' -NoNewWindow
    }

    Write-Output "IDM o archivo en uso por Hydra detectado. Comprobando archivos..."

    # Obtener todos los archivos
    $allFiles = Get-ChildItem -Path $downloadFolder -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    foreach ($file in $allFiles) {
        $extension = $file.Extension.ToLower()
    
        # Ignorar archivos .tmp, .temp, .aria2, .crdownload
        if ($extension -eq ".tmp" -or $extension -eq ".temp" -or $extension -eq ".aria2" -or $extension -eq ".crdownload") {
            Write-Output "Ignorando archivo temporal: $($file.FullName)"
            continue
        }
    
        if ($extension -ne ".rar" -and $extension -ne ".zip" -and $extension -ne ".7z") {
            # Archivo NO es comprimido, mover a Extracciones
            $destination = Join-Path -Path $outputFolder -ChildPath $file.Name
            Write-Output "Moviendo archivo no comprimido: $($file.FullName) -> $destination"
            Move-Item -Path $file.FullName -Destination $destination -Force
            
            # Ejecutar notificación para archivo movido
            $notifScript = Join-Path $PSScriptRoot "notifications\notificationExtract.py"
            Write-Output "Ejecutando notificación de archivo movido: $notifScript"
            & python $notifScript
            
            # Cerrar IDM solo si no hay carpetas en "E:\Descargas\TempDownload\DwnlData\Alex"
            if ((Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count -eq 0){
                Close-IDMan
            }
        }
    }

    # Verificar si hay archivos comprimidos para extraer
    $filesToExtract = Get-ChildItem -Path $downloadFolder -Include *.rar, *.zip, *.7z -File -Recurse | Where-Object { $_.FullName -notlike "$excludedFolder\*" }

    if ($filesToExtract.Count -gt 0) {
        # Extraer archivos
        Extract-Files

        # Cerrar IDM solo si no hay carpetas en "E:\Descargas\TempDownload\DwnlData\Alex"
        if ((Get-ChildItem -Path $folderToCheck -Directory -ErrorAction SilentlyContinue).Count -eq 0){
            Close-IDMan
        }

        # Esperar a que IDMan.exe o Hydra.exe se vuelva a ejecutar
        Write-Output "Esperando a que IDM o Hydra se vuelvan a iniciar..."
        while (-not (Is-IDManRunning) -and -not (Is-HydraRunning)) {
            Start-Sleep -Seconds 3
        }

        Write-Output "IDM o Hydra detectados nuevamente. Continuando con la siguiente verificacion..."
    } else {
        Write-Output "No hay archivos comprimidos para extraer."
    }
    Clear-Host
    Start-Sleep -Seconds 3
}