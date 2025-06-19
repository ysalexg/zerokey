using Playnite.SDK;
using Playnite.SDK.Models;
using Playnite.SDK.Plugins;
using System;
using System.Collections.Generic;
using System.IO;
using System.Windows.Controls;

namespace AddGames
{
    public class AddGames : LibraryPlugin
    {
        private static readonly ILogger logger = LogManager.GetLogger();

        private AddGamesSettingsViewModel settings { get; set; }

        public override Guid Id { get; } = Guid.Parse("6e5d15ac-c88d-4433-8b49-45b0c1a7ed02");

        public override string Name => "Añadir Juego";

        public override LibraryClient Client { get; } = new AddGamesClient();

        public AddGames(IPlayniteAPI api) : base(api)
        {
            settings = new AddGamesSettingsViewModel(this);
            Properties = new LibraryPluginProperties
            {
                HasSettings = true
            };
        }

        public override IEnumerable<GameMetadata> GetGames(LibraryGetGamesArgs args)
        {
            // Rutas de los archivos
            string pluginDir = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
            string assetsDir = Path.Combine(pluginDir, "..", "assets");
            string fallbackAssetsDir = @"D:\Programacion\Python\zerokey\assets";
            string nameFile = Path.Combine(assetsDir, "game_name.txt");
            string executableFile = Path.Combine(assetsDir, "full_executable_path.txt");
            string pathFile = Path.Combine(assetsDir, "game_path.txt");

            // Si los archivos principales no existen, intentar obtenerlos de la ruta alternativa
            if (!File.Exists(nameFile) || !File.Exists(executableFile) || !File.Exists(pathFile))
            {
                string fallbackNameFile = Path.Combine(fallbackAssetsDir, "game_name.txt");
                string fallbackExecutableFile = Path.Combine(fallbackAssetsDir, "full_executable_path.txt");
                string fallbackPathFile = Path.Combine(fallbackAssetsDir, "game_path.txt");

                if (File.Exists(fallbackNameFile) && File.Exists(fallbackExecutableFile) && File.Exists(fallbackPathFile))
                {
                    nameFile = fallbackNameFile;
                    executableFile = fallbackExecutableFile;
                    pathFile = fallbackPathFile;
                }
                else
                {
                    logger.Error("No se encuentran los archivos necesarios: game_name.txt, full_executable_path.txt o game_path.txt.");
                    // Borrar archivos adicionales si existen
                    string extra1 = Path.Combine(assetsDir, "executable.txt");
                    string extra2 = Path.Combine(assetsDir, "crack.txt");
                    string extra3 = Path.Combine(assetsDir, "appid.txt");
                    if (File.Exists(extra1)) File.Delete(extra1);
                    if (File.Exists(extra2)) File.Delete(extra2);
                    if (File.Exists(extra3)) File.Delete(extra3);
                    return new List<GameMetadata>();
                }
            }

            // Leer datos de los archivos
            string gameName = File.ReadAllText(nameFile).Trim();
            string gameExecutable = File.ReadAllText(executableFile).Trim();
            string installDirectory = File.ReadAllText(pathFile).Trim();

            // Borrar los archivos después de leerlos
            File.Delete(nameFile);
            File.Delete(executableFile);
            File.Delete(pathFile);

            // Borrar archivos adicionales si existen
            string extra1Del = Path.Combine(assetsDir, "executable.txt");
            string extra2Del = Path.Combine(assetsDir, "crack.txt");
            string extra3Del = Path.Combine(assetsDir, "appid.txt");
            if (File.Exists(extra1Del)) File.Delete(extra1Del);
            if (File.Exists(extra2Del)) File.Delete(extra2Del);
            if (File.Exists(extra3Del)) File.Delete(extra3Del);

            // Generar GameId a partir del nombre del juego
            string gameId = gameName.Replace(" ", "").ToLower();

            // Crear y devolver los metadatos del juego
            return new List<GameMetadata>()
            {
                new GameMetadata()
                {
                    Name = gameName,
                    GameId = gameId,
                    InstallDirectory = installDirectory,
                    Platforms = new HashSet<MetadataProperty>
                    {
                        new MetadataNameProperty("Sony Playstation 5")
                    },

                    GameActions = new List<GameAction>

                    {
                        new GameAction()
                        {
                            Type = GameActionType.File,
                            Path = gameExecutable,
                            IsPlayAction = true
                        }
                    },
                    IsInstalled = true,
                    Icon = new MetadataFile(@"Path")


                }
            };
        }

        public override ISettings GetSettings(bool firstRunSettings)
        {
            return settings;
        }

        public override UserControl GetSettingsView(bool firstRunSettings)
        {
            return new AddGamesSettingsView();
        }
    }
}
