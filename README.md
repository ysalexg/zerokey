<h1 align="center">Zerokey</h1>
<p align="center">Instalación automática de juegos con Hydra. <br> Integración con Playnite. Soporta únicamente juegos portables.</p>

<p align="center">
  <img src="https://github.com/ysalexg/zerokey/blob/main/screenshots/2.png?raw=true" alt="Imagen" />
</p>

## Descargas
[Descargar la última versión](https://github.com/ysalexg/zerokey/releases/latest)

## Características
- Puede iniciar de manera manual, o automática: detecta cuando finaliza una descarga y se inicia a través de un servicio en segundo plano (liviano, 13 mb y 0% de cpu en reposo).
- Extracción automática de archivos comprimidos y detección del juego.
- Mueve los archivos extraídos a una ruta especifica.
- Cambia el nombre de la carpeta por el nombre del juego para una mejor organización.
- Añade logros si así se específica.
- Añade el juego a Playnite con todo lo necesario: nombre, ruta de instalación y ruta de ejecutable.
- Actualmente no soporta repacks (FitGirl, DODI, etc.)

## Requisitos
7zip/Nanazip (Necesario para la extracción). Playnite (Opcional)

## Cómo usar
<p> En el archivo "config.yaml", especificar: </p>
<p>"download_folder" esta va a ser la ruta donde se van a leer los archivos comprimidos/carpeta del juego.</p>
<p>"extraction_folder" la carpeta a donde se van a extraer, puede ser la misma que "download_folder".</p>
<p>"game_folder" la carpeta donde se van a instalar los juegos.</p>
<p>Opcionalmente, se pueden añadir carpetas para excluir.</p>
<p>achievements: true/false, si se quiere tener logros del juego o no, para esto utilizará Goldberg (Fork de Denaup01).</p>
<p>delete_files: true/false, si quiere que se borren los archivos comprimidos luego de extraerlos.</p>

## Integración con Playnite
Ir a Playnite > Configuración > Para desarrolladores > Añadir > Agregar la ruta donde se encuentra la carpeta "plugin".
Luego de instalarse un juego, al refrescar la biblioteca (F5) se va a añadir automaticamente.
