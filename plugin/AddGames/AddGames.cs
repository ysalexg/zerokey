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
            string nameFile = @"D:\Programacion\Python\zerokey\assets\game_name.txt";
            string executableFile = @"D:\Programacion\Python\zerokey\assets\full_executable_path.txt";
            string pathFile = @"D:\Programacion\Python\zerokey\assets\game_path.txt";

            // Validar que los archivos existen
            if (!File.Exists(nameFile) || !File.Exists(executableFile) || !File.Exists(pathFile))
            {
                logger.Error("Uno o más archivos necesarios no existen.");
                return new List<GameMetadata>();
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
            string extra1 = @"D:\Programacion\Python\zerokey\assets\executable.txt";
            string extra2 = @"D:\Programacion\Python\zerokey\assets\crack.txt";
            string extra3 = @"D:\Programacion\Python\zerokey\assets\appid.txt";

            if (File.Exists(extra1)) File.Delete(extra1);
            if (File.Exists(extra2)) File.Delete(extra2);
            if (File.Exists(extra3)) File.Delete(extra3);

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
