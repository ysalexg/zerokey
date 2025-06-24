import os
import subprocess
import shutil

items = [
    "ui.py",
    "service.py",
    "config.yaml",
    "zerokey.ico",
    "assets",
    "compiler",
    "plugin",
    "screenshots"
]

src_dir = os.path.dirname(os.path.abspath(__file__))
dst_dir = os.path.join(src_dir, "repo")

os.makedirs(dst_dir, exist_ok=True)

for item in items:
    src_path = os.path.join(src_dir, item)
    dst_path = os.path.join(dst_dir, item)
    if os.path.isdir(src_path):
        robocopy_cmd = [
            "robocopy",
            src_path,
            dst_path,
            "/MIR",                # Sincroniza (copia y elimina)
            "/XD", ".git", "releases",  # Excluye carpetas
            "/XF", "manifest.yaml", "zerokeyDark.ico", "coding.txt", "zerokey.7z",  # Excluye archivos
            "/NFL", "/NDL",
            "/NJH", "/NJS",
            "/NC", "/NS", "/NP"
        ]
        subprocess.run(robocopy_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os.path.isfile(src_path):
        shutil.copy2(src_path, dst_path)
