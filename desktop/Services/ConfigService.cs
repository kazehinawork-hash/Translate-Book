using System.IO;
using System.Text.Json;
using TranslateBook.Models;

namespace TranslateBook.Services;

public static class ConfigService
{
    private static readonly string ConfigDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".translate_book");
    private static readonly string ConfigFile = Path.Combine(ConfigDir, "config.json");

    public static ApiConfig Load()
    {
        Directory.CreateDirectory(ConfigDir);
        if (File.Exists(ConfigFile))
        {
            var json = File.ReadAllText(ConfigFile);
            return JsonSerializer.Deserialize<ApiConfig>(json) ?? new ApiConfig();
        }
        return new ApiConfig();
    }

    public static void Save(ApiConfig config)
    {
        Directory.CreateDirectory(ConfigDir);
        var json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(ConfigFile, json);
    }

    public static ProviderConfig? GetProvider(string name)
    {
        var config = Load();
        return config.Providers.GetValueOrDefault(name);
    }
}
