import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os
import sys
import threading

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class Zerokey(win32serviceutil.ServiceFramework):
    _svc_name_ = "zerokey"
    _svc_display_name_ = "Zerokey"
    _svc_description_ = "Servicio de monitorización de Zerokey"

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.process = None
        self.monitor_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)
        
        # Wait for monitor thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, 'Service starting...')
        )
        self.main()

    def main(self):
        # Get the PowerShell script path
        ps1_path = self.find_powershell_script()
        if not ps1_path:
            return
        
        # Start the PowerShell process
        if not self.start_powershell_process(ps1_path):
            return
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_process, args=(ps1_path,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Wait for stop signal - this is the main optimization
        # Instead of polling every 5 seconds, we wait indefinitely until signaled
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
        # Cleanup
        self.cleanup_process()

    def find_powershell_script(self):
        """Find the PowerShell script with improved error handling"""
        ps1_path = get_resource_path("hydraService.ps1")
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, f'Looking for PowerShell script at: {ps1_path}')
        )
        
        if os.path.exists(ps1_path):
            return ps1_path
        
        # Try alternative locations
        alternative_paths = [
            get_resource_path("hydra.ps1"),
            os.path.join(os.path.dirname(sys.executable), "hydraService.ps1"),
            os.path.join(os.path.dirname(sys.executable), "hydra.ps1")
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, f'Found PowerShell script at: {alt_path}')
                )
                return alt_path
        
        # Log available files for debugging
        try:
            resource_dir = get_resource_path(".")
            files = os.listdir(resource_dir)
            servicemanager.LogErrorMsg(f"PowerShell script not found. Available files: {', '.join(files)}")
        except Exception as e:
            servicemanager.LogErrorMsg(f"PowerShell script not found and cannot list directory: {str(e)}")
        
        return None

    def start_powershell_process(self, ps1_path):
        """Start the PowerShell process"""
        try:
            self.process = subprocess.Popen(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered for immediate output
            )
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, f'PowerShell process started with PID: {self.process.pid}')
            )
            return True
        except Exception as e:
            servicemanager.LogErrorMsg(f"Failed to start PowerShell process: {str(e)}")
            return False

    def monitor_process(self, ps1_path):
        """Monitor the PowerShell process in a separate thread"""
        restart_count = 0
        max_restarts = 10
        
        while self.running:
            if not self.process:
                break
                
            try:
                # Wait for process to terminate with a reasonable timeout
                # This is much more efficient than polling
                exit_code = self.process.wait(timeout=30)
                
                if not self.running:
                    break
                    
                restart_count += 1
                if restart_count > max_restarts:
                    servicemanager.LogErrorMsg(f"PowerShell process restarted {max_restarts} times. Stopping service.")
                    self.SvcStop()
                    break
                
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_WARNING_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, f'PowerShell process terminated with code {exit_code} (restart #{restart_count}), restarting...')
                )
                
                if self.running:
                    self.start_powershell_process(ps1_path)
                    
            except subprocess.TimeoutExpired:
                # Process is still running, continue monitoring
                continue
            except Exception as e:
                if self.running:
                    servicemanager.LogErrorMsg(f"Error monitoring process: {str(e)}")
                break

    def cleanup_process(self):
        """Clean up the PowerShell process"""
        if self.process:
            try:
                # Send terminate signal
                self.process.terminate()
                
                # Wait for graceful termination
                try:
                    self.process.wait(timeout=10)
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_INFORMATION_TYPE,
                        servicemanager.PYS_SERVICE_STARTED,
                        (self._svc_name_, 'PowerShell process terminated gracefully')
                    )
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.process.kill()
                    self.process.wait()
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_WARNING_TYPE,
                        servicemanager.PYS_SERVICE_STARTED,
                        (self._svc_name_, 'PowerShell process force killed')
                    )
                    
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error terminating process: {str(e)}")
            finally:
                self.process = None

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(Zerokey)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(Zerokey)