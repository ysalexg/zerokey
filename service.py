import os
import sys
import threading
import subprocess
import time
import yaml
import logging
import signal

CREATE_NO_WINDOW = 0x08000000

if getattr(sys, 'frozen', False):
    # Ejecutable compilado
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    log_path = os.path.join(base_path, "assets", "zerokey.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
else:
    # En desarrollo
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona tanto para desarrollo como para el ejecutable"""
    try:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class ZerokeyMonitor:
    def __init__(self, config_file='config.yaml'):
        self.running = False
        self.monitor_thread = None
        self.download_folder = None
        self.excluded_folder = None
        self.handle_path = None
        self.ui_script = None
        self.config_file = config_file

    def load_config(self):
        """
        Lee config.yaml y extrae download_folder.
        Devuelve True si se carga correctamente.
        """
        try:
            config_path = resource_path(self.config_file)
            logging.info(f'Leyendo configuración en: {config_path}')
            if not os.path.exists(config_path):
                logging.error(f'config.yaml no encontrado en: {config_path}')
                return False
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            download_folder = cfg.get("paths", {}).get("download_folder")
            if not download_folder:
                logging.error("En config.yaml no se encontró paths.download_folder")
                return False
            download_folder = os.path.normpath(download_folder)
            self.download_folder = download_folder
            self.excluded_folder = os.path.join(self.download_folder, "TempDownload")
            logging.info(f'Download folder: {self.download_folder}, Excluded: {self.excluded_folder}')
            return True
        except Exception as e:
            logging.error(f"Error al leer config.yaml: {e}")
            return False

    def is_process_running(self, name):
        """
        Comprueba si existe un proceso con nombre name.exe.
        """
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {name}.exe"],
                stderr=subprocess.DEVNULL,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=CREATE_NO_WINDOW
            )
            if "No tasks" in output or "No se encuentra" in output:
                return False
            return f"{name}.exe" in output
        except Exception as e:
            logging.error(f"Error comprobando proceso {name}: {e}")
            return False

    def is_file_in_use_by_hydra(self, file_path):
        """
        Invoca handle.exe para saber si file_path está abierto por el proceso de descarga.
        Busca "aria2c.exe", "hydra-python-rpc.exe" o "7z.exe".
        """
        try:
            cmd = [self.handle_path, "-accepteula", file_path]
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=CREATE_NO_WINDOW
            )
            output_lower = output.lower()
            if (
                "aria2c.exe" in output_lower or
                "hydra-python-rpc.exe" in output_lower or
                "7z.exe" in output_lower
            ):
                return True
            return False
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            logging.error(f"Error invocando handle.exe para {file_path}: {e}")
            return False

    def monitor_loop(self):
        """Bucle principal de monitorización"""
        logging.info("Hilo de monitor arrancado.")
        prev_in_use = set()
        while self.running:
            try:
                # logging.info("Esperando a que un archivo esté en uso por Hydra o proceso Hydra corriendo...")
                # Esperar hasta que Hydra corra o algún archivo en uso
                while self.running:
                    hydra_running = self.is_process_running("Hydra")
                    in_use_now = set()
                    for root, dirs, files in os.walk(self.download_folder):
                        try:
                            if os.path.commonpath([root, self.excluded_folder]) == self.excluded_folder:
                                continue
                        except ValueError:
                            pass
                        for fname in files:
                            if not fname.lower().endswith((".rar", ".zip", ".7z")):
                                continue
                            fullpath = os.path.join(root, fname)
                            if self.is_file_in_use_by_hydra(fullpath):
                                in_use_now.add(fullpath)
                    if hydra_running or in_use_now:
                        break
                    time.sleep(3)
                if not self.running:
                    break

                # logging.info("Detección de Hydra o archivo en uso. Verificando archivos...")

                # Esperar a que archivos dejen de estar en uso
                while self.running:
                    in_use_now = set()
                    candidates = []
                    for root, dirs, files in os.walk(self.download_folder):
                        try:
                            if os.path.commonpath([root, self.excluded_folder]) == self.excluded_folder:
                                continue
                        except ValueError:
                            pass
                        for fname in files:
                            if not fname.lower().endswith((".rar", ".zip", ".7z")):
                                continue
                            fullpath = os.path.join(root, fname)
                            if self.is_file_in_use_by_hydra(fullpath):
                                in_use_now.add(fullpath)
                            elif fullpath in prev_in_use:
                                candidates.append(fullpath)
                    if candidates:
                        self.process_archives(candidates)
                        prev_in_use -= set(candidates)
                    prev_in_use = in_use_now
                    if not in_use_now:
                        break
                    time.sleep(3)

                # logging.info("Esperando reinicio de Hydra para siguiente ciclo...")
                while self.running:
                    if self.is_process_running("Hydra"):
                        break
                    time.sleep(3)
                # logging.info("Hydra detectado de nuevo. Volviendo a esperar archivos...")
                time.sleep(3)
            except Exception as e:
                logging.error(f"Error en monitor_loop: {e}")
                time.sleep(5)
        logging.info("Hilo de monitor finalizado.")

    def process_archives(self, files_list):
        """Procesa cada archivo: espera a que no esté en uso y ejecuta zerokey.exe o ui.py"""
        for archive_path in files_list:
            if not self.running:
                break
            logging.info(f"Verificando si {archive_path} está en uso por Hydra...")
            while self.running and self.is_file_in_use_by_hydra(archive_path):
                logging.info(f"Archivo en uso por Hydra. Esperando: {archive_path}")
                time.sleep(5)
            if not self.running:
                break
            logging.info(f"Archivo libre: {archive_path}. Ejecutando zerokey...")
            try:
                if os.path.exists(self.ui_script):
                    proc = subprocess.Popen(
                        [self.ui_script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=0,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        creationflags=CREATE_NO_WINDOW
                    )
                    out, err = proc.communicate()
                    if proc.returncode == 0:
                        logging.info(f"zerokey.exe ejecutado correctamente para {archive_path}")
                    else:
                        logging.error(f"zerokey.exe retornó código {proc.returncode} para {archive_path}. STDERR: {err.strip()}")
                else:
                    # Ejecutar ui.py si zerokey.exe no existe
                    ui_py_path = resource_path("ui.py")
                    if os.path.exists(ui_py_path):
                        proc = subprocess.Popen(
                            [sys.executable, ui_py_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            bufsize=0,
                            text=True,
                            encoding='utf-8',
                            errors='ignore',
                            creationflags=CREATE_NO_WINDOW
                        )
                        out, err = proc.communicate()
                        if proc.returncode == 0:
                            logging.info(f"ui.py ejecutado correctamente para {archive_path}")
                        else:
                            logging.error(f"ui.py retornó código {proc.returncode} para {archive_path}. STDERR: {err.strip()}")
                    else:
                        logging.error(f"No existe zerokey.exe en: {self.ui_script} ni ui.py en: {ui_py_path}. No se puede ejecutar instalador.")
            except Exception as e:
                logging.error(f"Error ejecutando instalador para {archive_path}: {e}")

    def start(self):
        if not self.load_config():
            logging.error("No se pudo cargar la configuración. El monitor finalizará.")
            return
        # Determinar rutas:
        self.handle_path = resource_path(os.path.join("assets", "handle.exe"))
        if not os.path.exists(self.handle_path):
            self.handle_path = "handle.exe"
        logging.info(f'Usando handle.exe en: {self.handle_path}')

        self.ui_script = resource_path("zerokey.exe")
        if not os.path.exists(self.ui_script):
            logging.warning(f"zerokey.exe no encontrado en: {self.ui_script}. Asegúrate de empacarlo junto al script.")
        else:
            logging.info(f'Encontrado zerokey.exe en: {self.ui_script}')

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        logging.info("Señal de parada recibida. Deteniendo monitor...")
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        logging.info("Monitor detenido.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor Zerokey")
    parser.add_argument('-c', '--config', default='config.yaml', help='Ruta al archivo de configuración YAML')
    args = parser.parse_args()

    monitor = ZerokeyMonitor(config_file=args.config)

    # Manejo de señales para parada limpia
    def handle_signal(sig, frame):
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    monitor.start()
    # Mantener el hilo principal vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == '__main__':
    main()
