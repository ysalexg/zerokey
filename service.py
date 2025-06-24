import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os
import sys
import threading
import yaml
import time

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona tanto para desarrollo como para el ejecutable"""
    try:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class Zerokey(win32serviceutil.ServiceFramework):
    _svc_name_ = "zerokey"
    _svc_display_name_ = "Zerokey"
    _svc_description_ = "Servicio de monitorización de Zerokey"

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.monitor_thread = None
        # Variables de configuración
        self.download_folder = None
        self.excluded_folder = None
        self.handle_path = None
        self.ui_script = None

    def SvcStop(self):
        # Señalar al sistema que el servicio está deteniéndose
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STOPPED,
                              (self._svc_name_, 'Service stop pending...'))
        # Señalar al hilo de monitor que pare
        self.running = False
        win32event.SetEvent(self.hWaitStop)
        # Esperar que el hilo termine
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STOPPED,
                              (self._svc_name_, 'Service stopped.'))

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, 'Service starting...'))
        try:
            self.main()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Exception in main: {e}")
            # En caso de excepción, esperar señal de stop para no terminar abruptamente
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def main(self):
        """
        Carga config y arranca lógica de monitor sin PowerShell.
        """
        # 1) Cargar configuración
        if not self.load_config():
            servicemanager.LogErrorMsg("No se pudo cargar la configuración. El servicio finalizará.")
            return

        # 2) Determinar rutas:
        # handle.exe
        self.handle_path = resource_path(os.path.join("assets", "handle.exe"))
        if not os.path.exists(self.handle_path):
            # Intentar si está en PATH
            self.handle_path = "handle.exe"
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, f'Usando handle.exe en: {self.handle_path}'))

        # zerokey.exe
        self.ui_script = resource_path("zerokey.exe")
        if not os.path.exists(self.ui_script):
            servicemanager.LogErrorMsg(f"zerokey.exe no encontrado en: {self.ui_script}. Asegúrate de empacarlo junto al servicio.")
        else:
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f'Encontrado zerokey.exe en: {self.ui_script}'))

        # 3) Arrancar hilo de monitor
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 4) Esperar señal de parada
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def load_config(self):
        """
        Lee config.yaml y extrae download_folder y excluded_folder.
        Devuelve True si se carga correctamente.
        """
        try:
            config_path = resource_path("config.yaml")
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f'Leyendo configuración en: {config_path}'))
            if not os.path.exists(config_path):
                servicemanager.LogErrorMsg(f"config.yaml no encontrado en: {config_path}")
                return False
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            download_folder = cfg.get("paths", {}).get("download_folder")
            if not download_folder:
                servicemanager.LogErrorMsg("En config.yaml no se encontró paths.download_folder")
                return False
            download_folder = os.path.normpath(download_folder)
            self.download_folder = download_folder
            self.excluded_folder = os.path.join(self.download_folder, "TempDownload")
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f'Download folder: {self.download_folder}, Excluded: {self.excluded_folder}'))
            return True
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error al leer config.yaml: {e}")
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
                errors='ignore'
            )
            if "No tasks" in output or "No se encuentra" in output:
                return False
            return f"{name}.exe" in output
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error comprobando proceso {name}: {e}")
            return False

    def is_file_in_use_by_hydra(self, file_path):
        """
        Invoca handle.exe para saber si file_path está abierto por el proceso de descarga.
        Busca "aria2c.exe" por defecto.
        """
        try:
            cmd = [self.handle_path, "-accepteula", file_path]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, encoding='utf-8', errors='ignore')
            if "aria2c.exe" in output.lower():
                return True
            return False
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error invocando handle.exe para {file_path}: {e}")
            return False

    def monitor_loop(self):
        """
        Bucle principal: espera archivo en uso o proceso Hydra, procesa archivos, espera reinicio.
        Sólo verifica Hydra, no IDMan.
        """
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, "Hilo de monitor arrancado."))

        while self.running:
            try:
                servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                      servicemanager.PYS_SERVICE_STARTED,
                                      (self._svc_name_, "Esperando a que un archivo esté en uso por Hydra..."))
                # Esperar hasta que detecte Hydra en ejecución o algún archivo en uso
                while self.running:
                    hydra_running = self.is_process_running("Hydra")
                    in_use_found = False
                    for root, dirs, files in os.walk(self.download_folder):
                        # Saltar carpeta excluida
                        try:
                            if os.path.commonpath([root, self.excluded_folder]) == self.excluded_folder:
                                continue
                        except ValueError:
                            # Paths en diferentes drives, skip check
                            pass
                        for fname in files:
                            if not fname.lower().endswith((".rar", ".zip", ".7z")):
                                continue
                            fullpath = os.path.join(root, fname)
                            if self.is_file_in_use_by_hydra(fullpath):
                                in_use_found = True
                                break
                        if in_use_found:
                            break
                    if hydra_running or in_use_found:
                        break
                    time.sleep(3)
                if not self.running:
                    break

                servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                      servicemanager.PYS_SERVICE_STARTED,
                                      (self._svc_name_, "Detección de Hydra o archivo en uso. Verificando archivos..."))
                # Verificar archivos .rar/.zip/.7z
                files_to_process = []
                for root, dirs, files in os.walk(self.download_folder):
                    try:
                        if os.path.commonpath([root, self.excluded_folder]) == self.excluded_folder:
                            continue
                    except ValueError:
                        pass
                    for fname in files:
                        if fname.lower().endswith((".rar", ".zip", ".7z")):
                            files_to_process.append(os.path.join(root, fname))

                if files_to_process:
                    self.process_archives(files_to_process)
                    servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                          servicemanager.PYS_SERVICE_STARTED,
                                          (self._svc_name_, "Esperando a que Hydra se reinicie para siguiente ciclo..."))
                    # Esperar reinicio de Hydra
                    while self.running:
                        if self.is_process_running("Hydra"):
                            break
                        time.sleep(3)
                    servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                          servicemanager.PYS_SERVICE_STARTED,
                                          (self._svc_name_, "Hydra detectado de nuevo. Volviendo a esperar archivos..."))
                else:
                    servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                          servicemanager.PYS_SERVICE_STARTED,
                                          (self._svc_name_, "No hay archivos .rar/.zip/.7z en download_folder."))
                time.sleep(3)
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error en monitor_loop: {e}")
                time.sleep(5)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, "Hilo de monitor finalizado."))

    def process_archives(self, files_list):
        """
        Procesa cada archivo: espera a que no esté en uso y ejecuta zerokey.exe
        """
        for archive_path in files_list:
            if not self.running:
                break
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f"Verificando si {archive_path} está en uso por Hydra..."))
            while self.running and self.is_file_in_use_by_hydra(archive_path):
                servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                      servicemanager.PYS_SERVICE_STARTED,
                                      (self._svc_name_, f"Archivo en uso por Hydra. Esperando: {archive_path}"))
                time.sleep(5)
            if not self.running:
                break
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, f"Archivo libre: {archive_path}. Ejecutando zerokey.exe..."))
            try:
                if os.path.exists(self.ui_script):
                    proc = subprocess.Popen(
                        [self.ui_script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=0,
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    out, err = proc.communicate()
                    if proc.returncode == 0:
                        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                              servicemanager.PYS_SERVICE_STARTED,
                                              (self._svc_name_, f"zerokey.exe ejecutado correctamente para {archive_path}"))
                    else:
                        servicemanager.LogErrorMsg(f"zerokey.exe retornó código {proc.returncode} para {archive_path}. STDERR: {err.strip()}")
                else:
                    servicemanager.LogErrorMsg(f"No existe zerokey.exe en: {self.ui_script}. No se puede ejecutar instalador.")
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error ejecutando zerokey.exe para {archive_path}: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(Zerokey)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(Zerokey)
