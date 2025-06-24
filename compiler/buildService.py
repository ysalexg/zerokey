import PyInstaller.__main__
import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_path = os.path.join(root_dir, 'service.py')
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zerokey.ico')

# Buscar el archivo PowerShell correcto
powershell_files = [
    os.path.join(root_dir, 'hydraService.ps1'),
    os.path.join(root_dir, 'hydra.ps1')
]

powershell_path = None
for ps_file in powershell_files:
    if os.path.exists(ps_file):
        powershell_path = ps_file
        break

if not powershell_path:
    print("Error: No se encontró ningún archivo PowerShell (hydraService.ps1 o hydra.ps1)")
    print(f"Buscando en: {root_dir}")
    print("Archivos disponibles:")
    for file in os.listdir(root_dir):
        if file.endswith('.ps1'):
            print(f"  - {file}")
    exit(1)

print(f"Usando archivo PowerShell: {powershell_path}")

releases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'releases')
os.makedirs(releases_dir, exist_ok=True)

# Determinar el nombre del archivo en el ejecutable
ps_filename = os.path.basename(powershell_path)

PyInstaller.__main__.run([
    service_path,
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    '--name=zerokeyService',
    '--noconsole',
    '--clean',
    f'--distpath={releases_dir}',
    f'--add-data={icon_path};.',
    f'--add-data={powershell_path};.',  # Esto empaqueta el archivo PS1
    # Agregar módulos ocultos necesarios para pywin32
    '--hidden-import=win32timezone',
    '--hidden-import=win32service',
    '--hidden-import=win32serviceutil',
    '--hidden-import=win32event',
    '--hidden-import=servicemanager',
    '--hidden-import=win32api',
    '--hidden-import=win32con',
    '--hidden-import=pywintypes',
    '--hidden-import=win32security',
    '--hidden-import=ntsecuritycon'
])

build_dir = os.path.join(root_dir, 'build')
if os.path.isdir(build_dir):
    shutil.rmtree(build_dir)

spec_file = os.path.join(root_dir, 'zerokeyService.spec')
if os.path.isfile(spec_file):
    os.remove(spec_file)

print(f"Compilación completada. El archivo PowerShell '{ps_filename}' ha sido empaquetado.")
print(f"Ejecutable creado en: {releases_dir}")