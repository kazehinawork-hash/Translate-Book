using System.IO;

namespace TranslateBook.Services;

public static class ProjectHelper
{
    public static string FindProjectRoot()
    {
        var dir = System.AppContext.BaseDirectory;
        while (dir != null)
        {
            if (File.Exists(Path.Combine(dir, "TranslateBook.csproj")))
                return Path.GetDirectoryName(dir)!;
            dir = Path.GetDirectoryName(dir);
        }
        return Path.GetFullPath(Path.Combine(System.AppContext.BaseDirectory, "..", "..", ".."));
    }
}
