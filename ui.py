import os
import sys
import requests
import shutil
import time
import subprocess
from pathlib import Path
from ruamel.yaml import YAML
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QLabel, 
                             QProgressBar, QWidget, QTextEdit, QDesktopWidget, QPushButton)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QIcon

script_dir = os.path.dirname(os.path.abspath(__file__))

# Variables globales
download_folder = "E:\\Descargas"
extraction_folder = "D:\\Extracciones"
game_folder = "D:\\Juegos"
manifest_url = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/refs/heads/master/data/manifest.yaml"
manifest_path = os.path.join(script_dir, "manifest.yaml")

excluded_folders = [
    r"D:\Extracciones\Drive Cache",
    r"D:\Extracciones\Free Download Manager",
    r"D:\Extracciones\IDM Temporal",
    r"E:\Descargas\TempDownload",
    r"E:\Descargas\TempDownload\DwnlData",
    r"E:\Descargas\TempDownload\DwnlData\Alex"
]

log_messages = []
extracted_paths = []
successful_paths = []

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona tanto para desarrollo como para el ejecutable"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def log_message(msg):
    """Agrega el mensaje al log en memoria y lo guarda en logs/logs.txt."""
    global log_messages
    log_messages.append(msg)
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "logs.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

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
                    text=True
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
                subprocess.run(["7z", "x", file_path, f"-o{destination_folder}", "-aoa"], check=True)

            # Buscar archivos comprimidos anidados
            for root, dirs, files in os.walk(destination_folder):
                for file in files:
                    if file.endswith(('.zip', '.rar', '.7z')):
                        nested_archive = os.path.join(root, file)
                        nested_destination = os.path.join(destination_folder, Path(file).stem)
                        extract_recursive(nested_archive, nested_destination, update_progress, is_main=False)
                        os.remove(nested_archive)  # Descomentar al finalizar desarrollo si es exitoso

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
            os.remove(file)  # Descomentar al finalizar desarrollo si es exitoso

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
                log_message(f"\033[32mCopiado archivo de crack: {file} a {target_path}\033[0m")
        
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
        log_message("\033[32mManifest cargado correctamente.\033[0m")
        extracted_folders = [
            f.path for f in os.scandir(extraction_folder)
            if f.is_dir() and not is_excluded(f.path)
        ]
        excluded_executables = [
        "dotNetFx40_Full_setup.exe",
        "dxwebsetup.exe",
        "oalinst.exe",
        "vcredist_2015-2019_x64.exe",
        "vcredist_2015-2019_x86.exe",
        "vcredist_x64.exe",
        "vcredist_x86.exe",
        "UnityCrashHandler64.exe",
        "xnafx40_redist.msi",
        "Setup.exe",
        "setup.exe",
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
        "Cleanup.exe"
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
                    if file.endswith(".exe") and file not in excluded_executables:
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
                    if file.endswith(".exe") and file not in excluded_executables:
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
    # Ruta específica donde quieres guardar el archivo
    output_directory = r"D:\Programacion\Python\Automatic Game Instalation"
    output_file_path = os.path.join(output_directory, output_file)

    try:
        # Buscar el ejecutable dentro de target_folder
        for root, _, files in os.walk(target_folder):
            if matching_exe in files:
                full_path = os.path.join(root, matching_exe)
                # Crear el directorio si no existe
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
                            print("Juego encontrado con método 4 (AppId en manifest)")
                            log_message(f"Juego encontrado: {game_name} (AppID={appid})")
                            break
                break

    # 2) Si no se resolvió vía AppId, matching por nombre de exe
    if not resolved_game:
        for game_name, game_info in manifest_data.items():
            for launch_path in game_info.get("launch", {}):
                if os.path.basename(launch_path).lower() == executable.lower():
                    resolved_game = (game_name, game_info)
                    print("Juego encontrado con método 5 (matching por nombre de exe)")
                    log_message(f"Juego encontrado con método 5 (matching por nombre de exe): {game_name} (exe={executable})")
                    break
            if resolved_game:
                break

    # 3) Si no se encontró en el manifest, usar el .exe más grande
    if not resolved_game:
        largest_exe = None
        largest_size = 0
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.exe'):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    if file_size > largest_size:
                        largest_size = file_size
                        largest_exe = file
                        resolved_path = root
        if largest_exe:
            resolved_exe = largest_exe
            print("Juego encontrado con método 6 (exe más grande)")
            log_message(f"Juego encontrado con método 6 (exe más grande): {resolved_exe}")

    # Si tenemos juego resuelto o ejecutable más grande, movemos/guardamos
    if resolved_game or largest_exe:
        if resolved_game:
            game_name, game_info = resolved_game
            install_dir = next(iter(game_info.get("installDir", {}).keys()), game_name)
            app_id = game_info.get("steam", {}).get("id", None)
        else:
            install_dir = os.path.basename(folder_path)
            app_id = None

        target_folder = os.path.join(game_folder, install_dir)
        log_message(f"Ejecutable encontrado: {resolved_exe} (AppID={app_id})")

        out_dir = r"D:\Programacion\Python\Automatic Game Instalation"
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "executable.txt"), "w", encoding="utf-8") as f:
            f.write(resolved_exe)
        with open(os.path.join(out_dir, "game_path.txt"), "w", encoding="utf-8") as f:
            f.write(target_folder)

        if not os.path.exists(target_folder):
            save_game_name(install_dir)
            shutil.move(resolved_path, target_folder)
            log_message(f"Movido {resolved_path} a {target_folder}")
        else:
            log_message(f"La carpeta destino ya existe: {target_folder}")

        # Guardar la ruta del ejecutable independientemente de si hay AppID o no
        save_full_executable_path(target_folder, resolved_exe)
        if app_id:
            log_message(f"AppID encontrado: {app_id}")
        else:
            log_message(f"No se encontró AppID para el juego {install_dir}")

        return True

    # Si no encontramos nada
    log_message(f"No se encontró información en el manifest ni un ejecutable válido en {folder_path}.")
    return False


def save_game_name(folder_name, output_file="game_name.txt"):
    # Definir el directorio de salida
    output_directory = r"D:\Programacion\Python\Automatic Game Instalation"
    output_file_path = os.path.join(output_directory, output_file)

    try:
        # Crear el directorio si no existe
        os.makedirs(output_directory, exist_ok=True)
        
        # Guardar el nombre del juego en la ruta especificada
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(folder_name)
        # Agregar mensaje al log además de imprimirlo
        mensaje = f"Nombre del juego guardado en {output_file_path}"
        print(mensaje)
        log_message(mensaje)
    except Exception as e:
        error_msg = f"Error al guardar el nombre del juego: {e}"
        print(error_msg)
        log_message(error_msg)

# Eliminar las carpetas de extracción específicas   
def cleanup_extraction_paths(update_progress):
    try:
        # Solo eliminamos las carpetas que fueron procesadas exitosamente
        for path in successful_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Eliminada carpeta de extracción: {path}")
        detect_crack()  # Detectar cracks después de la limpieza
        update_progress(100, "Instalación completada.", log_message="Instalación completada.")
        # Renombrar el archivo de log con el nombre del juego
        try:
            game_name_file = os.path.join(script_dir, "game_name.txt")
            logs_dir = os.path.join(script_dir, "logs")
            old_log = os.path.join(logs_dir, "logs.txt")
            if os.path.exists(game_name_file) and os.path.exists(old_log):
                with open(game_name_file, "r", encoding="utf-8") as f:
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
    
def detect_crack():
    """
    Detecta si existen archivos de crack conocidos en la ruta del juego.
    Busca: steam_api64.rne, steam_api64.cdx, onlinefix64.dll o la carpeta steam_settings.
    Retorna un diccionario con los resultados.
    Si encuentra alguno, agrega al log el tipo de crack detectado.
    """
    crack_files = ["steam_api64.rne", "steam_api64.cdx", "onlinefix64.dll"]
    crack_folder = "steam_settings"
    result = {
        "steam_api64.rne": False,
        "steam_api64.cdx": False,
        "onlinefix64.dll": False,
        "steam_settings": False
    }

    # Leer la ruta del juego desde game_path.txt
    game_path_file = os.path.join(script_dir, "game_path.txt")
    if not os.path.exists(game_path_file):
        print("No se encontró game_path.txt")
        return result

    with open(game_path_file, "r", encoding="utf-8") as f:
        game_path = f.read().strip()

    if not os.path.isdir(game_path):
        print(f"La ruta del juego no existe: {game_path}")
        return result

    # Buscar archivos de crack
    for root, dirs, files in os.walk(game_path):
        for crack_file in crack_files:
            if crack_file in files:
                result[crack_file] = True
                if crack_file == "steam_api64.rne":
                    log_message("Crack usado: RUNE")
                elif crack_file == "steam_api64.cdx":
                    log_message("Crack usado: CODEX")
                elif crack_file == "onlinefix64.dll":
                    log_message("Crack usado: Online-Fix")
        if crack_folder in dirs:
            result[crack_folder] = True
            log_message("Crack usado: Goldberg")

    return result

class GameInstallationThread(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(tuple)
    installation_complete = pyqtSignal()

    def run(self):
        try:
            def update_progress(progress, message, log_message=None):
                self.status_update.emit((message, log_message))
                self.progress_update.emit(progress)

            download_manifest(update_progress)
            extract_archives(update_progress)
            process_games(update_progress)
            cleanup_extraction_paths(update_progress)

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

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setFixedHeight(30)
        self.cancelar_button.setStyleSheet("""
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
        self.cancelar_button.clicked.connect(lambda: sys.exit(0))
        self.cancelar_button.setVisible(True)  # Inicialmente oculto
        layout.addWidget(self.cancelar_button) 

        self.finish_button = QPushButton("Finalizar")
        self.finish_button.setFixedHeight(30)
        self.finish_button.setStyleSheet("""
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
        self.finish_button.clicked.connect(lambda: sys.exit(0))
        self.finish_button.setVisible(False)  # Inicialmente oculto
        layout.addWidget(self.finish_button)   

        self.is_dragging = False
        self.drag_position = QPoint()
        
        # Hilo de instalación
        self.installation_thread = GameInstallationThread()
        self.installation_thread.progress_update.connect(self.update_progress)
        self.installation_thread.status_update.connect(self.update_status)
        self.installation_thread.installation_complete.connect(self.on_installation_complete)
        
        
        self.installation_thread.start()

        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, status_tuple):
        message, log_message = status_tuple
        self.status_label.setText(message)
        if log_message:
            self.log_text.append(log_message)
    
    def on_installation_complete(self):
        # Construimos la ruta relativa al directorio del script
        game_name_file = os.path.join(script_dir, "game_name.txt")

        # Texto por defecto
        status_text = "Instalación completada"

        # Intentamos leer el nombre del juego
        try:
            with open(game_name_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    status_text = content
        except Exception as e:
            # Opcional: loguear el error
            print(f"Error al leer {game_name_file}: {e}")

        # ÚNICO cambio: actualizar sólo el status_label
        self.status_label.setText(status_text)

        # El resto de la UI queda igual
        self.progress_bar.setValue(100)
        self.title.setText("Instalado")
        self.cancelar_button.setVisible(False)
        self.finish_button.setVisible(True)
        # Iniciar el temporizador para cerrar la ventana después de 5 segundos
        # self.close_timer.start(5000)  # 5000 milisegundos = 5 segundos

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_position)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

# Inicio del programa
if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon = QIcon(resource_path("icon.png"))
    app.setWindowIcon(icon)

    window = GameInstallationProgress()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec_())