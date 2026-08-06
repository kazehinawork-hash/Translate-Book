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
            try
            {
                var json = File.ReadAllText(ConfigFile);
                return JsonSerializer.Deserialize<ApiConfig>(json) ?? new ApiConfig();
            }
            catch
            {
                var backup = ConfigFile + ".bak." + DateTime.Now.ToString("yyyyMMdd-HHmmss");
                try { File.Copy(ConfigFile, backup, overwrite: true); } catch { }
                File.Delete(ConfigFile);
                File.WriteAllText(ConfigFile, JsonSerializer.Serialize(new ApiConfig(), new JsonSerializerOptions { WriteIndented = true }));
                return new ApiConfig();
            }
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
