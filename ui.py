# 1. Empaquetar y subir a github.

import os
import sys
import requests
import shutil
import time
import subprocess
import tempfile
from pathlib import Path
from ruamel.yaml import YAML
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QLabel, 
                             QProgressBar, QWidget, QTextEdit, QDesktopWidget, QPushButton, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QIcon

if getattr(sys, "frozen", False):
    # Si está empaquetado por PyInstaller, buscar config junto al ejecutable
    # sys.argv[0] apunta al path del exe lanzado
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    # En desarrollo
    base_path = os.path.dirname(os.path.abspath(__file__))

script_dir = base_path
config_path = os.path.join(script_dir, "config.yaml")
assets = os.path.join(script_dir, "assets")

# Cargar configuración desde config.yaml
yaml = YAML(typ="safe")

try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.load(f)
    
    # Obtener rutas y opciones desde la configuración
    download_folder = config["paths"]["download_folder"]
    extraction_folder = config["paths"]["extraction_folder"]
    game_folder = config["paths"]["game_folder"]
    excluded_folders = config["paths"]["excluded_folders"]
    achievements = config.get("achievements", True)
    delete_files = config.get("delete_files", True)
    show_tray = config.get("show_tray", True)
except Exception as e:
    print(f"Error al cargar config.yaml: {e}")

CREATE_NO_WINDOW = 0x08000000
manifest_url = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/refs/heads/master/data/manifest.yaml"
manifest_path = os.path.join(assets, "manifest.yaml")
executableTXT = os.path.join(assets, "executable.txt")
crackTXT = os.path.join(assets, "crack.txt")
appidTXT = os.path.join(assets, "appid.txt")
# Necesarios para el plugin
temp_dir = tempfile.gettempdir()
gamePathTXT = os.path.join(temp_dir, "game_path.txt")
gameNameTXT = os.path.join(temp_dir, "game_name.txt")
fullExecutablePathTXT = os.path.join(temp_dir, "full_executable_path.txt")

autocrack_dir = os.path.join(assets, "autocrack")
if not os.path.exists(autocrack_dir):
    os.makedirs(autocrack_dir, exist_ok=True)
steamautocrack = os.path.join(autocrack_dir, "SteamAutoCrack.CLI.exe")

excluded_executables = [
    "dotNetFx40_Full_setup.exe",
    "dxwebsetup.exe",
    "oalinst.exe",
    "vcredist_2015-2019_x64.exe",
    "vcredist_2015-2019_x86.exe",
    "vcredist_x64.exe",
    "vcredist_x86.exe",
    "xnafx40_redist.msi",
    # "Setup.exe",
    # "setup.exe",
    "Language Selector.exe",
    "UEPrereqSetup_x64.exe",
    "crashpad_handler.exe",
    "SteamworksExample.exe",
    "Common.ExtProtocolExecutor.exe",
    "ezTransXP.ExtProtocol.exe",
    "Lec.ExtProtocol.exe",
    "UnityCrashHandler64.exe",
    "crs-video.exe",
    "crs-uploader.exe",
    "crs-handler.exe",
    "CrashReportClient.exe",
    "UnrealCEFSubProcess.exe",
    "unins000.exe",
    "createdump.exe",
    "EAAntiCheat.GameServiceLauncher.exe",
    "EAAntiCheat.Installer.exe",
    "Cleanup.exe",
    "start_protected_game.exe"
]

log_messages = []
extracted_paths = []
successful_paths = []

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona tanto para desarrollo como para el ejecutable"""
    try:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Eliminar logs.txt si existe al inicio
logs_dir = os.path.join(script_dir, "logs")
log_file = os.path.join(logs_dir, "logs.txt")
if os.path.exists(log_file):
    try:
        os.remove(log_file)
    except Exception as e:
        print(f"Error al eliminar logs.txt: {e}")

def log_message(msg):
    """Agrega el mensaje al log en memoria y lo guarda en logs/logs.txt."""
    global log_messages
    log_messages.append(msg)
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "logs.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def create_default_config():
    """
    Crea el archivo config.yaml con valores por defecto si no existe.
    Usa rutas de ejemplo y formato YAML estándar.
    """
    default_config = {
        "paths": {
            "download_folder": "A:\\Ejemplo",
            "extraction_folder": "D:\\Ejemplo",
            "game_folder": "D:\\Ejemplo",
            "excluded_folders": [
                "D:\\Ejemplo",
                "D:\\Ejemplo\\Ejemplo2",
            ]
        },
        "achievements": True,
        "delete_files": True,
        "show_tray": True
    }

    try:
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f)
            print("Archivo config.yaml creado con valores por defecto.")
    except Exception as e:
        print(f"Error al crear config.yaml: {e}")

# Descargar manifest.yaml
def download_manifest(update_progress):
    retries = 5
    delay = 5  # segundos

    for attempt in range(retries):
        try:
            update_progress(10, "Descargando base de datos...", log_message="Descargando base de datos...")
            print("Descargando manifest...")
            response = requests.get(manifest_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            with open(manifest_path, 'wb') as file:
                file.write(response.content)
            print("\033[32mManifest descargado correctamente.\033[0m")
            log_message("Manifest descargado correctamente.")
            return
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"Demasiadas solicitudes. Reintentando en {wait} segundos...")
                time.sleep(wait)
            else:
                print(f"Error al intentar descargar el manifest: {e}")
                if os.path.exists(manifest_path):
                    msg = "No se pudo descargar el manifest. Usando el archivo local existente."
                    update_progress(10, msg, log_message=msg)
                    print(f"\033[33m{msg}\033[0m")
                    log_message(f"\033[33m{msg}\033[0m")
                    return
                else:
                    error_msg = f"Error crítico: No se pudo descargar el manifest y no existe uno local. {e}"
                    update_progress(0, error_msg, log_message=error_msg)
                    print(f"\033[31m{error_msg}\033[0m")
                    log_message(f"\033[31m{error_msg}\033[0m")
                    raise

# Verificar si una carpeta está excluida
def is_excluded(folder_path):
    return any(folder_path.startswith(excluded) for excluded in excluded_folders)

def extract_archives(update_progress):
    try:
        def extract_recursive(file_path, destination_folder, start_progress=None, file_progress_range=None, is_main=True):
            os.makedirs(destination_folder, exist_ok=True)
            
            if is_main and start_progress is not None and file_progress_range is not None:
                # Monitorear progreso para la extracción principal
                process = subprocess.Popen(
                    ["7z", "x", file_path, f"-o{destination_folder}", "-aoa", "-bsp1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=CREATE_NO_WINDOW
                )
                for line in process.stdout:
                    if "%" in line:
                        try:
                            percentage = int(line.split("%")[0].strip())
                            file_progress = percentage / 100.0
                            total_progress = start_progress + file_progress * file_progress_range
                            update_progress(
                                int(total_progress),
                                f"Extrayendo juego... {percentage}%",
                                log_message=None  # No agregar al log durante el progreso
                            )
                        except ValueError:
                            pass
                process.wait()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args)
            else:
                # Extracción anidada sin monitoreo de progreso
                subprocess.run(["7z", "x", file_path, f"-o{destination_folder}", "-aoa"], check=True, creationflags=CREATE_NO_WINDOW)

            # Buscar archivos comprimidos anidados
            for root, dirs, files in os.walk(destination_folder):
                for file in files:
                    if file.endswith(('.zip', '.rar', '.7z')):
                        nested_archive = os.path.join(root, file)
                        nested_destination = os.path.join(destination_folder, Path(file).stem)
                        extract_recursive(nested_archive, nested_destination, update_progress, is_main=False)
                        if delete_files:
                            os.remove(nested_archive)  # Solo borrar si delete_files es True

        # Recolectar archivos comprimidos
        compressed_files = []
        for root, dirs, files in os.walk(download_folder):
            for file in files:
                if file.endswith(('.zip', '.rar', '.7z')):
                    compressed_files.append(os.path.join(root, file))

        # Calcular el rango de progreso para la extracción (20% a 60%)
        total_extraction_progress = 40  # 60% - 20%
        num_files = len(compressed_files)
        file_progress_range = total_extraction_progress / num_files if num_files > 0 else 0
        progress = 20  # Inicio del rango de extracción

        for file in compressed_files:
            extraction_path = os.path.join(extraction_folder, Path(file).stem)
            if is_excluded(extraction_path):
                continue
            extracted_paths.append(extraction_path)
            # Mensaje único para el log al inicio de la extracción
            update_progress(
                progress,
                f"Iniciando extracción de {os.path.basename(file)}...",
                log_message="Extrayendo juego..."
            )
            extract_recursive(file, extraction_path, progress, file_progress_range, is_main=True)
            progress += file_progress_range
            if delete_files:
                os.remove(file)  # Solo borrar si delete_files es True

        log_message("Archivos extraídos correctamente.")
    except Exception as e:
        error_msg = f"Error durante la extracción: {e}"
        update_progress(0, error_msg, log_message=error_msg)
        print(error_msg)
        log_message(error_msg)
        raise

# Leer manifest.yaml
def load_manifest():
    yaml = YAML(typ="safe")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.load(f)

def handle_crack_files(original_exe_path, crack_exe_path):
    """
    Maneja los archivos de crack:
    1. Identifica la carpeta del crack
    2. Copia todos los archivos de la carpeta del crack a la carpeta original
    """
    try:
        # Obtener la carpeta del crack
        crack_folder = os.path.dirname(crack_exe_path)
        original_folder = os.path.dirname(original_exe_path)
        
        # Archivos de crack comunes
        crack_files = [
            "steam_emu.ini",
            "steam_api64.dll",
            "steam_api64.me",
            os.path.splitext(os.path.basename(original_exe_path))[0] + ".me"
        ]
        
        # Copiar todos los archivos de la carpeta del crack
        for root, _, files in os.walk(crack_folder):
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, crack_folder)
                target_path = os.path.join(original_folder, relative_path)
                
                # Crear directorios necesarios
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Copiar el archivo
                shutil.copy2(source_path, target_path)
                log_message(f"Copiado archivo de crack: {file} a {target_path}")
        
        return True
    except Exception as e:
        error_msg = f"Error al manejar archivos de crack: {e}"
        print(error_msg)
        log_message(error_msg)
        return False

def process_games(update_progress):
    try:
        print("Cargando manifest...")
        update_progress(85, "Cargando base de datos...", log_message="Cargando base de datos...")
        manifest_data = load_manifest()
        log_message("Manifest cargado correctamente.")
        extracted_folders = [
            f.path for f in os.scandir(extraction_folder)
            if f.is_dir() and not is_excluded(f.path)
        ]

        # Diccionario para almacenar ejecutables duplicados
        duplicate_executables = {}

        # Primera pasada: recolectar todos los ejecutables
        for folder in extracted_folders:
            print(f"Procesando carpeta: {folder}")

            for root, dirs, files in os.walk(folder):
                if is_excluded(root):
                    continue
                for file in files:
                    if (
                        file.endswith(".exe")
                        and file not in excluded_executables
                        and "soundtrack" not in file.lower()
                    ):
                        full_path = os.path.join(root, file)
                        if file not in duplicate_executables:
                            duplicate_executables[file] = []
                        duplicate_executables[file].append(full_path)

        # Segunda pasada: procesar ejecutables y manejar cracks
        for folder in extracted_folders:
            print(f"Procesando carpeta: {folder}")

            executables = []  # Lista para almacenar los ejecutables encontrados

            for root, dirs, files in os.walk(folder):
                if is_excluded(root):
                    continue
                for file in files:
                    if (
                        file.endswith(".exe")
                        and file not in excluded_executables
                        and "soundtrack" not in file.lower()
                    ):
                        full_path = os.path.join(root, file)
                        # Verificar si es un ejecutable duplicado
                        if len(duplicate_executables.get(file, [])) > 1:
                            # Verificar si está en una carpeta de crack
                            if "crack" in root.lower():
                                # Encontrar el ejecutable original
                                original_path = next(p for p in duplicate_executables[file] if "crack" not in p.lower())
                                # Manejar los archivos de crack
                                if handle_crack_files(original_path, full_path):
                                    log_message(f"\033[32mArchivos de crack aplicados correctamente para {file}\033[0m")
                                continue
                        executables.append((file, root))

            if not executables:
                no_exec_msg = f"No se encontró ejecutable en: {folder}"
                print(no_exec_msg)
                log_message(no_exec_msg)
                if folder in extracted_paths:
                    extracted_paths.remove(folder)
                continue

            # Procesar cada ejecutable encontrado
            for exe_file, exe_path in executables:
                if process_executable(exe_file, exe_path, manifest_data, update_progress):
                    print(f"Procesamiento exitoso, deteniendo búsqueda en {folder}.")
                    successful_paths.append(folder)
                    break

    except Exception as e:
        error_msg = f"Error procesando juegos: {e}"
        print(error_msg)
        log_message(error_msg)

def save_full_executable_path(target_folder, matching_exe, output_file="full_executable_path.txt"):
    # Usar el directorio temporal del sistema
    output_directory = tempfile.gettempdir()
    output_file_path = os.path.join(output_directory, output_file)

    try:
        # Buscar el ejecutable dentro de target_folder
        for root, _, files in os.walk(target_folder):
            if matching_exe in files:
                full_path = os.path.join(root, matching_exe)
                # Crear el directorio si no existe (normalmente innecesario para temp, pero por seguridad)
                os.makedirs(output_directory, exist_ok=True)
                # Guardar el archivo en la ruta deseada
                with open(output_file_path, "w", encoding="utf-8") as file:
                    file.write(full_path)
                print(f"Ruta completa del ejecutable guardada en {output_file_path}: {full_path}")
                return
        print(f"No se encontró el ejecutable {matching_exe} en {target_folder}.")
    except Exception as e:
        print(f"Error al guardar la ruta completa del ejecutable: {e}")

def process_executable(executable, folder_path, manifest_data, update_progress):
    """
    Procesa un ejecutable:
      1) Busca recursivamente steam_emu.ini, cream_api.ini, steam_appid.txt y CPY.ini
      2) Extrae todos los AppId que encuentre
      3) Si hay al menos 2 coincidencias, las usa. Si hay 1, también.
      4) Si no hay AppId, matching por nombre en el manifest.
      5) Si no encuentra en el manifest, usa el .exe más grande.
    """
    resolved_game = None
    resolved_exe = executable
    resolved_path = folder_path

    # Buscar recursivamente los archivos de AppId
    ini_paths = []
    cream_paths = []
    steam_txt_paths = []
    cpy_paths = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            name = f.lower()
            if name == "steam_emu.ini":
                ini_paths.append(os.path.join(root, f))
            elif name == "cream_api.ini":
                cream_paths.append(os.path.join(root, f))
            elif name == "steam_appid.txt":
                steam_txt_paths.append(os.path.join(root, f))
            elif name == "cpy.ini":
                cpy_paths.append(os.path.join(root, f))

    # Recolectar posibles AppIds
    appid_candidates = []

    # steam_emu.ini
    for ini_path in ini_paths:
        try:
            with open(ini_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(ini_path, "r", encoding="latin-1") as f:
                lines = f.readlines()
        for line in lines:
            if line.strip().startswith("AppId="):
                _, aid = line.strip().split("=", 1)
                appid_candidates.append(aid.strip())
                break

    # cream_api.ini
    for cream_path in cream_paths:
        try:
            with open(cream_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "appid" in line.lower() and "=" in line:
                        aid = line.split("=", 1)[1].strip()
                        if aid.isdigit():
                            appid_candidates.append(aid)
                            break
        except UnicodeDecodeError:
            continue

    # steam_appid.txt
    for txt_path in steam_txt_paths:
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.isdigit():
                    appid_candidates.append(content)
        except UnicodeDecodeError:
            continue

    # CPY.ini
    for cpy_path in cpy_paths:
        try:
            with open(cpy_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("AppID="):
                        aid = line.strip().split("=", 1)[1]
                        if aid.isdigit():
                            appid_candidates.append(aid)
                            break
        except UnicodeDecodeError:
            continue

    # Determinar AppId válido
    from collections import Counter
    counts = Counter(appid_candidates)
    appid = None
    if counts:
        # Preferimos un candidato con >=2 apariciones
        for aid, cnt in counts.items():
            if cnt >= 2:
                appid = aid
                break
        # Si solo hay 1 candidato total, lo aceptamos
        if appid is None and len(counts) == 1:
            appid = next(iter(counts))

    # 1) Si tenemos AppId, intentamos resolver por manifest
    if appid:
        for game_name, game_info in manifest_data.items():
            if str(game_info.get("steam", {}).get("id", "")) == appid:
                launch_paths = game_info.get("launch", {})
                if launch_paths:
                    desired_exe = os.path.basename(next(iter(launch_paths.keys())))
                    for root, _, files in os.walk(folder_path):
                        if desired_exe.lower() in (f.lower() for f in files):
                            resolved_exe = next(f for f in files if f.lower() == desired_exe.lower())
                            resolved_path = root
                            resolved_game = (game_name, game_info)
                            print("Juego encontrado con método 1 (AppId en manifest)")
                            log_message(f"Juego encontrado con método 1 (AppId en manifest): {game_name} (AppID={appid})")
                            break
                break

    # 2) Si no se resolvió vía AppId, matching por nombre de exe
    if not resolved_game and executable.lower() not in ("setup.exe"):
        for game_name, game_info in manifest_data.items():
            for launch_path in game_info.get("launch", {}):
                if os.path.basename(launch_path).lower() == executable.lower():
                    resolved_game = (game_name, game_info)
                    print("Juego encontrado con método 2 (matching por nombre de exe)")
                    log_message(f"Juego encontrado con método 2 (matching por nombre de exe): {game_name}")
                    break
            if resolved_game:
                break

    # 3) Si no se encontró en el manifest, usar el .exe más grande (excluyendo los de la lista)
    fitgirl_found = False
    dodi_found = False
    repack_detected = False
    if not resolved_game:
        largest_exe = None
        largest_size = 0
        for root, _, files in os.walk(folder_path):
            for file in files:
                if (
                    file.lower().endswith('.exe')
                    and file not in excluded_executables
                    and "soundtrack" not in file.lower()
                ):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    if file_size > largest_size:
                        largest_size = file_size
                        largest_exe = file
                        resolved_path = root
        if largest_exe:
            resolved_exe = largest_exe
            # Si el exe encontrado es setup.exe o Setup.exe, buscar repack
            if resolved_exe.lower() == "setup.exe":
                # Buscar indicadores FitGirl
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().startswith("fg-") and file.lower().endswith(".bin"):
                            fitgirl_found = True
                            break
                    if fitgirl_found:
                        break

                # Si no se encontró FitGirl, buscar indicador Dodi
                if not fitgirl_found:
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            if file.lower().endswith(".doi"):
                                dodi_found = True
                                break
                        if dodi_found:
                            break

                # Si no se encontró ninguno, se marca repack
                if not fitgirl_found and not dodi_found:
                    repack_detected = True

                if fitgirl_found:
                    log_message("FitGirl Repack detectado.")
                    with open(executableTXT, "w", encoding="utf-8") as f:
                        f.write("fitgirl")
                    log_message(f"No se encontró información en el manifest ni un ejecutable válido en {folder_path}.")
                    resolved_game = None
                    return False
                elif dodi_found:
                    log_message("Dodi Repack detectado.")
                    with open(executableTXT, "w", encoding="utf-8") as f:
                        f.write("dodi")
                    log_message(f"No se encontró información en el manifest ni un ejecutable válido en {folder_path}.")
                    resolved_game = None
                    return False
                elif repack_detected:
                    log_message("Repack detectado.")
                    with open(executableTXT, "w", encoding="utf-8") as f:
                        f.write("repack")
                    log_message(f"No se encontró información en el manifest ni un ejecutable válido en {folder_path}.")
                    resolved_game = None
                    return False
            else:
                print("Juego encontrado con método 3 (exe más grande)")
                log_message(f"Juego encontrado con método 3 (exe más grande): {resolved_exe}")
    # Si tenemos juego resuelto o ejecutable más grande, movemos/guardamos
    # Solo continuar si NO se detectó fitgirl, dodi o repack
    if (resolved_game or (largest_exe and not (fitgirl_found or dodi_found or repack_detected))):
        if resolved_game:
            game_name, game_info = resolved_game
            install_dir = next(iter(game_info.get("installDir", {}).keys()), game_name)
            app_id = game_info.get("steam", {}).get("id", None)
        else:
            install_dir = os.path.basename(folder_path)
            app_id = None

        target_folder = os.path.join(game_folder, install_dir)
        log_message(f"Ejecutable encontrado: {resolved_exe} (AppID={app_id})")

        with open(executableTXT, "w", encoding="utf-8") as f:
            f.write(resolved_exe)
        with open(gamePathTXT, "w", encoding="utf-8") as f:
            f.write(target_folder)
        save_game_name(install_dir)
        if not os.path.exists(target_folder):
            shutil.move(resolved_path, target_folder)
            log_message(f"Movido {resolved_path} a {target_folder}")
        else:
            log_message(f"La carpeta destino ya existe: {target_folder}")

        # Guardar la ruta del ejecutable independientemente de si hay AppID o no
        save_full_executable_path(target_folder, resolved_exe)
        if app_id:
            log_message(f"AppID encontrado: {app_id}")

            with open(appidTXT, "w", encoding="utf-8") as f:
                f.write(str(app_id))
        else:
            log_message(f"No se encontró AppID para el juego {install_dir}")
        return True

    # Si no encontramos nada
    log_message(f"No se encontró información en el manifest ni un ejecutable válido en {folder_path}.")
    return False

def save_game_name(folder_name):
    try:
        with open(gameNameTXT, "w", encoding="utf-8") as file:
            file.write(folder_name)
        mensaje = f"Nombre del juego guardado en {gameNameTXT}"
        print(mensaje)
    except Exception as e:
        error_msg = f"Error al guardar el nombre del juego: {e}"
        print(error_msg)
        log_message(error_msg)
    
def detect_crack():
    """
    Detecta si existen archivos de crack conocidos en la ruta del juego.
    Busca: steam_api64.rne, steam_api64.cdx, onlinefix64.dll o la carpeta steam_settings.
    Si encuentra onlinefix64.dll, solo considera Online-Fix (ignora RUNE y CODEX).
    Si no, detecta RUNE o CODEX según corresponda.
    Si encuentra steam_settings, detecta Goldberg.
    Guarda el tipo de crack detectado y lo agrega al log.
    """
    crack_folder = "steam_settings"
    result = {
        "steam_api64.rne": False,
        "steam_api64.cdx": False,
        "onlinefix64.dll": False,
        "steam_settings": False
    }
    detected_cracks = []

    # Leer la ruta del juego desde game_path.txt

    if not os.path.exists(gamePathTXT):
        print("No se encontró game_path.txt")
        return result

    with open(gamePathTXT, "r", encoding="utf-8") as f:
        game_path = f.read().strip()

    if not os.path.isdir(game_path):
        print(f"La ruta del juego no existe: {game_path}")
        return result

    found_onlinefix = False
    found_rune = False
    found_codex = False
    found_goldberg = False

    # Buscar archivos de crack
    for root, dirs, files in os.walk(game_path):
        if "onlinefix64.dll" in files:
            result["onlinefix64.dll"] = True
            found_onlinefix = True
        if "steam_api64.rne" in files:
            result["steam_api64.rne"] = True
            found_rune = True
        if "steam_api64.cdx" in files:
            result["steam_api64.cdx"] = True
            found_codex = True
        if crack_folder in dirs:
            result[crack_folder] = True
            found_goldberg = True

    # Lógica de prioridad: Online-Fix > RUNE > CODEX
    if found_onlinefix:
        log_message("Crack usado: Online-Fix")
        detected_cracks.append("Online-Fix")
    else:
        if found_rune:
            log_message("Crack usado: RUNE")
            detected_cracks.append("RUNE")
        elif found_codex:
            log_message("Crack usado: CODEX")
            detected_cracks.append("CODEX")
    if found_goldberg:
        log_message("Crack usado: Goldberg")
        detected_cracks.append("Goldberg")

    if detected_cracks:
        try:
            with open(crackTXT, "w", encoding="utf-8") as f:
                f.write(", ".join(detected_cracks))
        except Exception as e:
            print(f"Error al guardar crack.txt: {e}")

    return result

def apply_crack():
    """
    Aplica el crack usando SteamAutoCrack.CLI.exe solo si se contiene 'RUNE' o 'CODEX'.
    Si es CODEX, primero reemplaza todos los steam_api64.dll por el de la ruta Codex.
    Lee la ruta del juego de game_path.txt y el appid de appid.txt,
    ambos ubicados en el mismo directorio que el script.
    """
    try:
        if not os.path.exists(crackTXT):
            log_message("No se encontró crack.txt, no se aplicará el crack.")
            return False

        with open(crackTXT, "r", encoding="utf-8") as f:
            crack_type = f.read().strip().upper()

        # Solo aplicar si es RUNE o CODEX
        if crack_type not in ("RUNE", "CODEX"):
            log_message(f"El crack detectado es '{crack_type}', no se aplicará SteamAutoCrack.")
            return False

        # Leer la ruta del juego y el appid
        if not os.path.exists(gamePathTXT) or not os.path.exists(appidTXT):
            log_message("No se encontró game_path.txt o appid.txt para aplicar el crack.")
            return False

        with open(gamePathTXT, "r", encoding="utf-8") as f:
            game_path = f.read().strip()
        with open(appidTXT, "r", encoding="utf-8") as f:
            appid = f.read().strip()

        if not game_path or not appid:
            log_message("game_path.txt o appid.txt están vacíos.")
            return False

        # Si el crack es CODEX, reemplazar steam_api64.dll, copiar archivos de assets/steamclient, y modificar archivos de configuración
        if crack_type == "CODEX":
            if getattr(sys, "frozen", False):
                codex_dll = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "assets", "codex", "steam_api64.dll")
            else:
                codex_dll = os.path.join(os.path.dirname(__file__), "assets", "codex", "steam_api64.dll")
            if not os.path.exists(codex_dll):
                log_message("No se encontró el steam_api64.dll de CODEX.")
                return False
            replaced = False
            for root, _, files in os.walk(game_path):
                for file in files:
                    if file.lower() == "steam_api64.dll":
                        target = os.path.join(root, file)
                        try:
                            # Copiar el DLL de CODEX sobre el original
                            shutil.copy2(codex_dll, target)
                            log_message(f"Reemplazado steam_api64.dll en: {target} (CODEX)")
                            replaced = True

                            command = [steamautocrack, "crack", root, "--appid", appid]
                            log_message(f"Ejecutando comando: {' '.join(command)}")
                            result = subprocess.run(command, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                            if result.returncode == 0:
                                log_message("Crack aplicado correctamente con SteamAutoCrack.")
                            else:
                                log_message(f"Error aplicando crack con SteamAutoCrack: {result.stderr.strip()}")
                            try:
                                os.remove(target)
                                bak_path = os.path.join(root, "steam_api64.dll.bak")
                                os.rename(bak_path, target)
                                log_message(f"Restaurado steam_api64.dll original en: {root}")
                            except Exception as e:
                                log_message(f"Error al restaurar steam_api64.dll en {root}: {e}")

                            # Copiar todos los archivos de assets/steamclient al mismo directorio
                            steamclient_dir = resource_path("assets/steamclient")
                            if os.path.isdir(steamclient_dir):
                                for item in os.listdir(steamclient_dir):
                                    source_item = os.path.join(steamclient_dir, item)
                                    dest_item = os.path.join(root, item)
                                    if os.path.isfile(source_item):
                                        shutil.copy2(source_item, dest_item)

                        except Exception as e:
                            log_message(f"Error al reemplazar steam_api64.dll en {target}: {e}")
            if not replaced:
                log_message("No se encontró ningún steam_api64.dll para reemplazar en el juego.")

            
            # Buscar y modificar ColdClientLoader.ini en cualquier subcarpeta del juego
            ini_found = False
            for root, _, files in os.walk(game_path):
                if "ColdClientLoader.ini" in files:
                    ini_path = os.path.join(root, "ColdClientLoader.ini")
                    ini_found = True
                    try:
                        with open(ini_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        # Obtener el nombre del ejecutable desde executableTXT
                        with open(executableTXT, "r", encoding="utf-8") as f:
                            exe_name = f.read().strip()
                        # Obtener el AppId desde appidTXT
                        with open(appidTXT, "r", encoding="utf-8") as f:
                            appid_content = f.read().strip()
                        new_lines = []
                        for line in lines:
                            if line.startswith("Exe="):
                                new_lines.append(f"Exe={exe_name}\n")
                            elif line.startswith("AppId="):
                                new_lines.append(f"AppId={appid_content}\n")
                            else:
                                new_lines.append(line)
                        with open(ini_path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        log_message(f"Modificado ColdClientLoader.ini.")
                    except Exception as e:
                        log_message(f"Error al modificar ColdClientLoader.ini en {ini_path}: {e}")
            if not ini_found:
                log_message("ColdClientLoader.ini no encontrado en la ruta del juego.")

            # Modificar full_executable_path: reemplazar el nombre del ejecutable por steamclient_loader_x64.exe
            try:
                if os.path.exists(fullExecutablePathTXT):
                    with open(fullExecutablePathTXT, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        dir_part = os.path.dirname(content)
                        new_path = os.path.join(dir_part, "steamclient_loader_x64.exe")
                        with open(fullExecutablePathTXT, "w", encoding="utf-8") as f:
                            f.write(new_path)
                        log_message(f"Aplicado SteamClient correctamente.")
                else:
                    log_message("El archivo full_executable_path.txt no existe.")
            except Exception as e:
                log_message(f"Error al modificar full_executable_path.txt: {e}")

            return True

        # Si el crack es RUNE, ejecutar SteamAutoCrack sin modificaciones adicionales
        else:
            command = [steamautocrack, "crack", game_path, "--appid", appid]
            log_message(f"Ejecutando comando: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            if result.returncode == 0:
                log_message("Crack aplicado correctamente con SteamAutoCrack.")
                return True
            else:
                log_message(f"Error al aplicar el crack: {result.stderr}")
                return False
    except Exception as e:
        log_message(f"Excepción al aplicar el crack: {e}")
        return False

def cleanup_extraction_paths_and_crack(update_progress):
    """
    Elimina las carpetas de extracción exitosas.
    Si se detecta un crack, guarda el tipo de crack y lo agrega al log.
    Por último renombra el archivo de log con el nombre del juego.
    """
    try:
        for path in successful_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Eliminada carpeta de extracción: {path}")
        detect_crack()
        if achievements:
            apply_crack()
        try:
            logs_dir = os.path.join(script_dir, "logs")
            old_log = os.path.join(logs_dir, "logs.txt")
            if os.path.exists(gameNameTXT) and os.path.exists(old_log):
                with open(gameNameTXT, "r", encoding="utf-8") as f:
                    game_name = f.read().strip()
                if game_name:
                    # Limpiar el nombre del juego para usarlo como nombre de archivo
                    safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
                    new_log = os.path.join(logs_dir, f"{safe_game_name}.txt")
                    if not os.path.exists(new_log):
                        os.rename(old_log, new_log)
        except Exception as e:
            print(f"Error al renombrar el archivo de log: {e}")
    except Exception as e:
        update_progress(0, f"Error al limpiar las carpetas: {e}", log_message=f"Error al limpiar las carpetas: {e}")

def success_installation_status(update_progress):
    """
    Reporta el estado de la instalación.
    Si log_message es proporcionado, lo agrega al log.
    """
    update_progress(100, "Instalación completada.", log_message="Instalación completada.")

def config_flags():
    log_message(f"Achievements: {achievements}")
    print(f"Achievements: {achievements}")
    log_message(f"Delete files: {delete_files}")
    print(f"Delete files: {delete_files}")

class GameInstallationThread(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(tuple)
    installation_complete = pyqtSignal()
    installation_canceled = pyqtSignal()

    def run(self):
        try:
            def update_progress(progress, message, log_message=None):
                self.status_update.emit((message, log_message))
                self.progress_update.emit(progress)

            config_flags()
            download_manifest(update_progress)
            extract_archives(update_progress)
            process_games(update_progress)
            if not os.path.exists(executableTXT) or not os.path.exists(gamePathTXT):
                update_progress(100, "No se encontró ejecutable.", log_message="No se encontró ejecutable.")
                self.installation_canceled.emit()
            else:
                with open(executableTXT, "r", encoding="utf-8") as f:
                    exe_name = f.read().strip()
                if exe_name.lower() == "fitgirl":
                    update_progress(100, "FitGirl no tiene soporte.", log_message="FitGirl no tiene soporte.")
                    self.installation_canceled.emit()
                elif exe_name.lower() == "dodi":
                    update_progress(100, "Dodi no tiene soporte.", log_message="Dodi no tiene soporte.")
                    self.installation_canceled.emit()
                elif exe_name.lower() == "repack":
                    update_progress(100, "Repack no tiene soporte.", log_message="Repack no tiene soporte.")
                    self.installation_canceled.emit()
                else:
                    cleanup_extraction_paths_and_crack(update_progress)
                    success_installation_status(update_progress)
                    self.installation_complete.emit()
        except Exception as e:
            self.status_update.emit((f"Error crítico: {str(e)}", f"Error crítico: {str(e)}"))

class GameInstallationProgress(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instalación de Juego")
        self.setFixedSize(255, 255)  # Tamaño fijo de 255x255 píxeles
        
        # Quitar barra de ventana
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Centrar la ventana en la pantalla
        screen = QDesktopWidget().screenGeometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

        # Crear un contenedor central personalizado
        central_widget = QWidget()
        central_widget.setObjectName("central_container")
        central_widget.setStyleSheet("""
            #central_container {
                background-color: #202020; 
                border-radius: 6px;
                border: 1px solid #F3F3F3;
            }
        """)
        
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Aplicar paleta de colores
        self.setStyleSheet("""
            QMainWindow {
                background-color: #202020; /* Fondo oscuro */
                border-radius: 6px; /* Redondeo de bordes */
            }
            QLabel {
                color: #D8DEE9; /* Texto claro */
            }
            QProgressBar {
                background-color: #2D2D2D; /* Fondo de la barra */
                color: #88C0D0; /* Texto */
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #F3F3F3; /* Color del progreso */
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #2D2D2D; /* Fondo de texto */
                color: #D8DEE9; /* Texto */
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                border: 1px solid #202020;
                border-radius: 6px;
            }
        """)

        self.setAttribute(Qt.WA_StyledBackground)

        # Título estilizado
        self.title = QLabel("Instalando...")
        self.title.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        
        # Estado del progreso
        self.status_label = QLabel("Iniciando instalación...")
        self.status_label.setFont(QFont('Segoe UI', 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Barra de progreso estilizada
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Área de log de mensajes estilizada
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        def create_button(text, visible=False, on_click=None):
            button = QPushButton(text)
            button.setFixedHeight(30)
            button.setStyleSheet("""
            QPushButton {
                background-color: #F3F3F3;
                color: #202020;
                border-radius: 6px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D8DEE9;
            }
            """)
            if on_click:
                button.clicked.connect(on_click)
                button.setVisible(visible)
                layout.addWidget(button)
            return button

        self.cancelar_button = create_button("Cancelar", visible=True, on_click=lambda: sys.exit(0))
        self.finish_button = create_button("Finalizar", visible=False, on_click=lambda: sys.exit(0))
        self.close_button = create_button("Cerrar", visible=False, on_click=lambda: sys.exit(0))

        self.is_dragging = False
        self.drag_position = QPoint()
        
        # Hilo de instalación
        self.installation_thread = GameInstallationThread()
        self.installation_thread.progress_update.connect(self.update_progress)
        self.installation_thread.status_update.connect(self.update_status)
        self.installation_thread.installation_complete.connect(self.on_installation_complete)
        self.installation_thread.installation_canceled.connect(self.on_installation_canceled)
        
        self.installation_thread.start()

        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)

        self.tray_icon = None
        if show_tray:
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(resource_path("zerokey.ico")))

            tray_menu = QMenu()
            tray_menu.setStyleSheet("""
            QMenu {
            background-color: #202020;
            color: #D8DEE9;
            border: 1px solid #444;
            border-radius: 6px;
            }
            QMenu::item {
            background-color: transparent;
            color: #D8DEE9;
            padding: 6px 20px;
            }
            QMenu::item:selected {
            background-color: #2D2D2D;
            color: #88C0D0;
            border-radius: 4px;
            }
            QMenu::separator {
            height: 1px;
            background: #444;
            margin: 4px 0;
            }
            """)

            show_action = QAction("Mostrar", self)
            show_action.triggered.connect(self.showNormal)
            tray_menu.addAction(show_action)

            hide_action = QAction("Minimizar", self)
            hide_action.triggered.connect(self.hide)
            tray_menu.addAction(hide_action)

            exit_action = QAction("Salir", self)
            exit_action.triggered.connect(lambda: sys.exit(0))
            tray_menu.addAction(exit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("Zerokey")
            self.tray_icon.show()

            self.tray_icon.activated.connect(self.on_tray_activated)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        # self.tray_icon.showMessage(
        #     "Zerokey",
        #     "El programa sigue ejecutándose en el área de notificación.",
        #     QSystemTrayIcon.Information,
        #     2000
        # )

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.activateWindow()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, status_tuple):
        message, log_message = status_tuple
        self.status_label.setText(message)
        if log_message:
            self.log_text.append(log_message)
    
    def on_installation_complete(self):
        # Texto por defecto
        status_text = "Instalación completada"

        try:
            with open(gameNameTXT, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    status_text = content
        except Exception as e:
            # Opcional: loguear el error
            print(f"Error al leer {gameNameTXT}: {e}")

        self.status_label.setText(status_text)
        self.progress_bar.setValue(100)
        self.title.setText("Instalado")
        self.cancelar_button.setVisible(False)
        self.finish_button.setVisible(True)
        # Iniciar el temporizador para cerrar la ventana después de 5 segundos
        # self.close_timer.start(5000)

    def on_installation_canceled(self):
        self.status_label.setText("Instalación cancelada")
        self.progress_bar.setValue(0)
        self.title.setText("Cancelada")
        self.cancelar_button.setVisible(False)
        self.close_button.setVisible(True)
        # Iniciar el temporizador para cerrar la ventana después de 5 segundos
        # self.close_timer.start(5000)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_position)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

if __name__ == "__main__":
    create_default_config()
    app = QApplication(sys.argv)
    icon = QIcon(resource_path("icon.png"))
    app.setWindowIcon(icon)

    window = GameInstallationProgress()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec_())