import os
import sys
import requests
import shutil
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
    r"D:\Extracciones\IDM Temporal"
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

# Descargar manifest.yaml
def download_manifest(update_progress):
    try:
        update_progress(10, "Descargando base de datos...", log_message="Descargando base de datos...")
        print("Descargando manifest...")
        response = requests.get(manifest_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        with open(manifest_path, 'wb') as file:
            file.write(response.content)
        print("\033[32mManifest descargado correctamente.\033[0m")
        log_messages.append("\033[32mManifest descargado correctamente.\033[0m")
    except Exception as e:
        error_msg = f"Error al descargar el manifest: {e}"
        update_progress(0, f"Error al descargar el manifest: {e}", log_message=f"Error al descargar el manifest: {e}")
        print(error_msg)
        log_messages.append(error_msg)
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

        log_messages.append("\033[32mArchivos extraídos correctamente.\033[0m")
    except Exception as e:
        error_msg = f"Error durante la extracción: {e}"
        update_progress(0, error_msg, log_message=error_msg)
        print(error_msg)
        log_messages.append(error_msg)
        raise

# Eliminar las carpetas de extracción específicas   
def cleanup_extraction_paths(update_progress):
    try:
        # Solo eliminamos las carpetas que fueron procesadas exitosamente
        for path in successful_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Eliminada carpeta de extracción: {path}")
        update_progress(100, "Instalación completada.", log_message="Instalación completada.")
    except Exception as e:
        update_progress(0, f"Error al limpiar las carpetas: {e}", log_message=f"Error al limpiar las carpetas: {e}")

# Leer manifest.yaml
def load_manifest():
    yaml = YAML(typ="safe")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.load(f)

def process_games(update_progress):
    try:
        print("Cargando manifest...")
        update_progress(85, "Cargando base de datos...", log_message="Cargando base de datos...")
        manifest_data = load_manifest()
        log_messages.append("\033[32mManifest cargado correctamente.\033[0m")
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
        "xnafx40_redist.msi",
        "Setup.exe",
        "setup.exe"
        ]

        for folder in extracted_folders:
            print(f"Procesando carpeta: {folder}")

            executables = []  # Lista para almacenar los ejecutables encontrados

            for root, dirs, files in os.walk(folder):
                if is_excluded(root):
                    continue
                for file in files:
                    if file.endswith(".exe") and file not in excluded_executables:
                        executables.append((file, root))

            if not executables:
                no_exec_msg = f"No se encontró ejecutable en: {folder}"
                print(no_exec_msg)
                log_messages.append(no_exec_msg)
                # No agregamos esta carpeta a la lista de successful_paths
                # Y la removemos de extracted_paths si está ahí
                if folder in extracted_paths:
                    extracted_paths.remove(folder)
                continue

            # Procesar cada ejecutable encontrado
            for exe_file, exe_path in executables:
                # Si process_executable devuelve True, detener el procesamiento de más ejecutables
                if process_executable(exe_file, exe_path, manifest_data, update_progress):
                    print(f"Procesamiento exitoso, deteniendo búsqueda en {folder}.")
                    successful_paths.append(folder)  # Agregar a la lista de éxito
                    break  # Salir del bucle de ejecutables
    except Exception as e:
        error_msg = f"Error procesando juegos: {e}"
        print(error_msg)
        log_messages.append(error_msg)

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
      1) Busca recursivamente steam_emu.ini, cream_api.ini y steam_appid.txt
      2) Extrae todos los AppId que encuentre
      3) Si hay al menos 2 coincidencias, las usa. Si hay 1, también.
      4) Si no hay AppId, matching por nombre en el manifest.
    """
    resolved_game = None
    resolved_exe = executable
    resolved_path = folder_path

    # 1) Buscar recursivamente los archivos de AppId
    ini_paths = []
    cream_paths = []
    steam_txt_paths = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            name = f.lower()
            if name == "steam_emu.ini":
                ini_paths.append(os.path.join(root, f))
            elif name == "cream_api.ini":
                cream_paths.append(os.path.join(root, f))
            elif name == "steam_appid.txt":
                steam_txt_paths.append(os.path.join(root, f))

    # 2) Recolectar posibles AppIds
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

    # 3) Determinar AppId válido
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

    # 4) Si tenemos AppId, intentamos resolver por manifest
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
                            break
                break

    # 5) Si no se resolvió vía AppId, matching por nombre de exe
    if not resolved_game:
        for game_name, game_info in manifest_data.items():
            for launch_path in game_info.get("launch", {}):
                if os.path.basename(launch_path).lower() == executable.lower():
                    resolved_game = (game_name, game_info)
                    break
            if resolved_game:
                break

    # 6) Si tenemos juego resuelto, movemos/guardamos
    if resolved_game:
        game_name, game_info = resolved_game
        install_dir = next(iter(game_info.get("installDir", {}).keys()), game_name)
        app_id = game_info.get("steam", {}).get("id", None)

        target_folder = os.path.join(game_folder, install_dir)
        log_messages.append(f"\033[32mEjecutable encontrado: {resolved_exe} (AppID={app_id})\033[0m")

        out_dir = r"D:\Programacion\Python\Automatic Game Instalation"
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "executable.txt"), "w", encoding="utf-8") as f:
            f.write(resolved_exe)
        with open(os.path.join(out_dir, "game_path.txt"), "w", encoding="utf-8") as f:
            f.write(target_folder)

        if not os.path.exists(target_folder):
            save_game_name(install_dir)
            shutil.move(resolved_path, target_folder)
            log_messages.append(f"\033[32mMovido {resolved_path} a {target_folder}\033[0m")
        else:
            log_messages.append(f"La carpeta destino ya existe: {target_folder}")

        if app_id:
            save_full_executable_path(target_folder, resolved_exe)
        else:
            log_messages.append(f"No se encontró AppID para el juego {game_name}")

        return True

    # 7) Si no encontramos nada en el manifest
    log_messages.append(f"No se encontró información en el manifest para ningún ejecutable en {folder_path}.")
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
        mensaje = f"\033[32mNombre del juego guardado en {output_file_path}.\033[0m"
        print(mensaje)
        log_messages.append(mensaje)
    except Exception as e:
        error_msg = f"Error al guardar el nombre del juego: {e}"
        print(error_msg)
        log_messages.append(error_msg)


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
        self.status_label.setText("Instalación completada")
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