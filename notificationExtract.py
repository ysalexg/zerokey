import os
from win11toast import toast

# Ruta de la carpeta
folder_path = r"D:\Extracciones"

# Extensiones a ignorar
ignored_extensions = ('.tmp', '.temp', '.aria2')

# Listar archivos y carpetas, ignorando archivos con extensiones no deseadas
entries = [
    os.path.join(folder_path, f)
    for f in os.listdir(folder_path)
    if not f.lower().endswith(ignored_extensions)
]

# Filtrar entradas válidas
entries = [e for e in entries if os.path.exists(e)]

if entries:
    # Obtener el más reciente
    latest = max(entries, key=os.path.getmtime)
    file = os.path.basename(latest)
else:
    file = "vacío"

buttons = [
    {'activationType': 'protocol', 'arguments': folder_path, 'content': 'Abrir carpeta'}
]

toast('Descarga completada', file, buttons=buttons, scenario='alarm', audio={'silent': 'true'})
