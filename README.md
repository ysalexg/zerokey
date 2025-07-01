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
7zip/Nanazip y [ .NET Runtime 8 ](https://dotnet.microsoft.com/download/dotnet/8.0/runtime?cid=getdotnetcore&runtime=desktop&os=windows&arch=x64). Playnite (Opcional)

## Cómo usar
Para la manera automática, ejecutar zerokeyService.exe. Para usarlo de manera manual, ejecutar zerokey.exe al terminar una descarga.
<br>
En el archivo "config.yaml", especificar: 
<br>
"download_folder" esta va a ser la ruta donde se van a leer los archivos comprimidos/carpeta del juego. Se recomienda que se cree una carpeta donde sólo se vayan a descargar juegos. (En actualizaciones no va a hacer falta)
<br>
"extraction_folder" la carpeta a donde se van a extraer, puede ser la misma que "download_folder".
<br>
"game_folder" la carpeta donde se van a instalar los juegos.
<br>
Opcionalmente, se pueden añadir carpetas para excluir.
<br>
achievements: true/false, si se quiere tener logros del juego o no, para esto utilizará Goldberg (Fork de Denaup01). No se aplica en juegos con Online-Fix.
<br>
delete_files: true/false, si quiere que se borren los archivos comprimidos luego de extraerlos.


## Integración con Playnite
Ir a Playnite > Configuración > Para desarrolladores > Añadir > Agregar la ruta donde se encuentra la carpeta "plugin".
<br>
Luego de instalarse un juego, al refrescar la biblioteca (F5) se va a añadir automaticamente.
<br>
Para ver los logros en Playnite, es necesaria la extensión Success Story https://github.com/eFMann/playnite-successstory-plugin
