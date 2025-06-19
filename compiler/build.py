import PyInstaller.__main__
import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_py_path = os.path.join(root_dir, 'ui.py')
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zerokey.ico')
releases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'releases')
os.makedirs(releases_dir, exist_ok=True)

PyInstaller.__main__.run([
    ui_py_path,
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    '--name=zerokey',
    '--noconsole',
    '--clean',
    f'--distpath={releases_dir}'
])

build_dir = os.path.join(root_dir, 'build')
if os.path.isdir(build_dir):
    shutil.rmtree(build_dir)

spec_file = os.path.join(root_dir, 'zerokey.spec')
if os.path.isfile(spec_file):
    os.remove(spec_file)

src_plugin_dir = os.path.join(root_dir, 'plugin', 'AddGames', 'bin', 'Debug')
dst_plugin_dir = os.path.join(releases_dir, 'plugin')
if os.path.isdir(src_plugin_dir):
    if os.path.exists(dst_plugin_dir):
        shutil.rmtree(dst_plugin_dir)
    shutil.copytree(src_plugin_dir, dst_plugin_dir)

src_assets_dir = os.path.join(root_dir, 'assets')
dst_assets_dir = os.path.join(releases_dir, 'assets')
if os.path.isdir(src_assets_dir):
    if os.path.exists(dst_assets_dir):
        shutil.rmtree(dst_assets_dir)
    shutil.copytree(src_assets_dir, dst_assets_dir)