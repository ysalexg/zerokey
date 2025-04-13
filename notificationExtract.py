import os
from win11toast import toast

# Ruta de la carpeta
folder_path = r"D:\Extracciones"

# Listar archivos y carpetas
entries = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
entries = [e for e in entries if os.path.exists(e)]  # Evitar rutas inválidas

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
