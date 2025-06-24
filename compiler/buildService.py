import PyInstaller.__main__
import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_path = os.path.join(root_dir, 'service.py')
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zerokey.ico')

releases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'releases')
os.makedirs(releases_dir, exist_ok=True)

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
    # '--hidden-import=win32timezone',
    # '--hidden-import=win32service',
    # '--hidden-import=win32serviceutil',
    # '--hidden-import=win32event',
    # '--hidden-import=servicemanager',
    # '--hidden-import=win32api',
    # '--hidden-import=win32con',
    # '--hidden-import=pywintypes',
    # '--hidden-import=win32security',
    # '--hidden-import=ntsecuritycon'
])

build_dir = os.path.join(root_dir, 'build')
if os.path.isdir(build_dir):
    shutil.rmtree(build_dir)

spec_file = os.path.join(root_dir, 'zerokeyService.spec')
if os.path.isfile(spec_file):
    os.remove(spec_file)

print(f"Ejecutable creado en: {releases_dir}")