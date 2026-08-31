using System.Diagnostics;
using System.IO;

namespace TranslateBook.Services;

/// <summary>
/// Chuyển đổi file sách đa định dạng (PDF/MOBI/AZW/AZW3/DOC/DOCX/TXT/EPUB) sang EPUB
/// bằng Calibre ebook-convert để mở trong EpubPreviewWindow.
/// Kết quả được cache trong working/preview_cache/ để không convert lại mỗi lần xem.
/// </summary>
public static class EbookConvertService
{
    /// <summary>Các định dạng ebook-convert xử lý trực tiếp được (không cần chuyển).</summary>
    private static readonly HashSet<string> _nativeEpubExts = new(StringComparer.OrdinalIgnoreCase)
    {
        ".epub"
    };

    /// <summary>Các định dạng có thể chuyển sang EPUB.</summary>
    private static readonly HashSet<string> _convertibleExts = new(StringComparer.OrdinalIgnoreCase)
    {
        ".pdf", ".mobi", ".azw", ".azw3", ".azw4", ".doc", ".docx", ".txt", ".rtf", ".html", ".htm", ".fb2", ".lit", ".prc", ".pdb", ".chm", ".djvu", ".cbz", ".cbr", ".odt", ".ods", ".zip"
    };

    /// <summary>Kiểm tra xem có thể mở xem file này không.</summary>
    public static bool CanPreview(string filePath)
    {
        if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath)) return false;
        var ext = Path.GetExtension(filePath);
        return _nativeEpubExts.Contains(ext) || _convertibleExts.Contains(ext);
    }

    /// <summary>
    /// Trả về đường dẫn EPUB có thể mở ngay (native) hoặc chuyển đổi (cached).
    /// Trả về null nếu không hỗ trợ hoặc chuyển đổi thất bại.
    /// </summary>
    public static string? GetPreviewEpub(string sourcePath, string projectRoot)
    {
        if (!CanPreview(sourcePath)) return null;

        var ext = Path.GetExtension(sourcePath);
        if (_nativeEpubExts.Contains(ext)) return sourcePath;

        var cacheDir = Path.Combine(projectRoot, "working", "preview_cache");
        Directory.CreateDirectory(cacheDir);

        var cacheKey = $"{Path.GetFileNameWithoutExtension(sourcePath)}_{File.GetLastWriteTimeUtc(sourcePath):yyyyMMddHHmmss}";
        var cachePath = Path.Combine(cacheDir, cacheKey + ".epub");

        if (File.Exists(cachePath)) return cachePath;

        var convertOk = ConvertToEpub(sourcePath, cachePath, out var error);
        if (!convertOk)
        {
            throw new InvalidOperationException($"Không thể chuyển đổi '{Path.GetFileName(sourcePath)}' sang EPUB: {error}");
        }
        return File.Exists(cachePath) ? cachePath : null;
    }

    private static bool ConvertToEpub(string input, string output, out string error)
    {
        error = "";
        var converter = FindEbookConvert();
        if (string.IsNullOrEmpty(converter))
        {
            error = "Không tìm thấy Calibre (ebook-convert). Hãy cài Calibre để đọc định dạng này.";
            return false;
        }

        try
        {
            // Calibre nhận diện format đầu ra qua ĐUÔI FILE — phải là .epub.
            // Ghi đè trực tiếp (Calibre tự xử lý ghi đè); nếu thất bại sẽ không tạo file.
            if (File.Exists(output)) File.Delete(output);

            var psi = new ProcessStartInfo
            {
                FileName = converter,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            // --no-default-epub-cover tránh sinh bìa mặc định
            psi.ArgumentList.Add(input);
            psi.ArgumentList.Add(output);
            psi.ArgumentList.Add("--no-default-epub-cover");

            using var proc = Process.Start(psi);
            if (proc == null)
            {
                error = "Không khởi động được ebook-convert.";
                return false;
            }

            var stdout = proc.StandardOutput.ReadToEnd();
            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit();

            if (proc.ExitCode != 0 || !File.Exists(output))
            {
                error = (string.IsNullOrWhiteSpace(stderr) ? stdout : stderr).Trim();
                if (error.Length > 400) error = error[..400];
                return false;
            }

            return true;
        }
        catch (Exception ex)
        {
            error = ex.Message;
            return false;
        }
    }

    private static string? FindEbookConvert()
    {
        // 1. Biến môi trường / đường dẫn cố định
        var candidates = new List<string>
        {
            Environment.GetEnvironmentVariable("CALIBRE_EBOOK_CONVERT") ?? "",
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Calibre2", "ebook-convert.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Calibre2", "ebook-convert.exe"),
            @"C:\Program Files\Calibre2\ebook-convert.exe",
            @"C:\Program Files (x86)\Calibre2\ebook-convert.exe"
        };

        foreach (var c in candidates)
        {
            if (!string.IsNullOrWhiteSpace(c) && File.Exists(c)) return c;
        }

        // 2. Tìm trong PATH
        try
        {
            var which = Environment.GetEnvironmentVariable("PATH") ?? "";
            foreach (var dir in which.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
            {
                var full = Path.Combine(dir.Trim('"'), "ebook-convert.exe");
                if (File.Exists(full)) return full;
            }
        }
        catch { }

        return null;
    }
}
