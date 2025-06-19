import PyInstaller.__main__
import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_py_path = os.path.join(root_dir, 'ui.py')
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zerokey.ico')
dist_path = os.path.dirname(os.path.abspath(__file__)) 

PyInstaller.__main__.run([
    ui_py_path,
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    '--name=zerokey',
    '--noconsole',
    '--clean',
    f'--distpath={dist_path}'
])

# Borrar la carpeta "build" dentro de root_dir
build_dir = os.path.join(root_dir, 'build')
if os.path.isdir(build_dir):
    shutil.rmtree(build_dir)

# Borrar el archivo .spec en root_dir
spec_file = os.path.join(root_dir, 'zerokey.spec')
if os.path.isfile(spec_file):
    os.remove(spec_file)
