import subprocess
import os

# Ruta de la carpeta a comprimir y nombre del archivo de salida
folder_to_compress = os.path.join(os.path.dirname(__file__), "releases")
output_archive = os.path.join(os.path.dirname(__file__), "zerokey.7z")

# Comando para comprimir usando 7z
command = [
    "7z", "a", output_archive, os.path.join(folder_to_compress, "*")
]

# Ejecutar el comando
result = subprocess.run(command, capture_output=True, text=True)

# Mostrar salida del comando
print(result.stdout)
if result.returncode != 0:
    print("Error:", result.stderr)