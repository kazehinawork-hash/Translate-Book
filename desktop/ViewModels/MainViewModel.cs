using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TranslateBook.Models;
using TranslateBook.Services;

namespace TranslateBook.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly PythonPipelineService _pipeline;
    private readonly ApiTranslationService _apiService = new();

    [ObservableProperty] private BookStatus? _selectedBook;
    [ObservableProperty] private int _selectedTabIndex;
    [ObservableProperty] private string _logText = "";
    [ObservableProperty] private string _activeProvider = "";
    [ObservableProperty] private bool _isApiOk;

    public ObservableCollection<BookStatus> InputBooks { get; } = new();
    public ObservableCollection<BookStatus> OutputBooks { get; } = new();

    public MainViewModel()
    {
        var projectRoot = FindProjectRoot();
        _pipeline = new PythonPipelineService(projectRoot);
        _pipeline.OutputReceived += msg => App.Current.Dispatcher.Invoke(() => AppendLog(msg));
        _pipeline.ErrorReceived += msg => App.Current.Dispatcher.Invoke(() => AppendLog(msg, "error"));

        LoadBooks();
        LoadApiStatus();
    }

    public void LoadBooks()
    {
        InputBooks.Clear();
        OutputBooks.Clear();

        var projectRoot = FindProjectRoot();
        var booksDir = Path.Combine(projectRoot, "output", "books");
        var inputDir = Path.Combine(projectRoot, "input");

        // Output books
        if (Directory.Exists(booksDir))
        {
            foreach (var d in Directory.GetDirectories(booksDir).OrderBy(x => x))
            {
                var slug = Path.GetFileName(d);
                OutputBooks.Add(GetBookStatus(projectRoot, slug, "output"));
            }
        }

        // Input files
        if (Directory.Exists(inputDir))
        {
            foreach (var f in Directory.GetFiles(inputDir).OrderBy(x => x))
            {
                var ext = Path.GetExtension(f).ToLower();
                if (ext is ".pdf" or ".epub" or ".docx")
                {
                    var name = Path.GetFileName(f);
                    InputBooks.Add(new BookStatus
                    {
                        Slug = name,
                        Source = "input",
                        FilePath = f,
                    });
                }
            }
        }

        AppendLog($"Da tai {InputBooks.Count} input, {OutputBooks.Count} output");
    }

    [RelayCommand]
    private async Task TestApiConnectionAsync(string provider)
    {
        AppendLog($"Dang test {provider}...");
        var (ok, msg) = await _apiService.TestConnectionAsync(provider);
        if (ok)
        {
            IsApiOk = true;
            ActiveProvider = provider;
            AppendLog($"OK — {provider}: {msg}");
        }
        else
        {
            IsApiOk = false;
            AppendLog($"Loi — {provider}: {msg}", "error");
        }
    }

    [RelayCommand]
    private async Task StartTranslateAsync(BookStatus book)
    {
        if (book == null) return;
        AppendLog($"Bat dau dich: {book.Slug}");
        var ok = await _pipeline.RunTranslateHelperAsync(
            $"working/chunks/{book.Slug}",
            $"working/progress/{book.Slug}",
            $"glossary/{book.Slug}.csv");
        if (ok) AppendLog($"Hoan thanh: {book.Slug}");
    }

    [RelayCommand]
    private async Task GenerateAudiobookAsync(BookStatus book)
    {
        if (book == null) return;
        AppendLog($"Tao audio: {book.Slug}");
        var ok = await _pipeline.RunAudiobookAsync(book.Slug);
        if (ok) AppendLog($"Audio hoan thanh: {book.Slug}");
    }

    [RelayCommand]
    private async Task GitCommitAsync()
    {
        AppendLog("Dang git add...");
        await _pipeline.RunGitCommandAsync("add -A");
        await _pipeline.RunGitCommandAsync($"commit -m \"update from desktop app\"");
        AppendLog("Da commit");
    }

    private void AppendLog(string msg, string level = "info")
    {
        var time = DateTime.Now.ToString("HH:mm:ss");
        var prefix = level switch
        {
            "error" => "[ERR]",
            "warning" => "[WARN]",
            _ => "[INFO]"
        };
        LogText += $"[{time}] {prefix} {msg}\n";
    }

    private static BookStatus GetBookStatus(string projectRoot, string slug, string source)
    {
        var bookDir = Path.Combine(projectRoot, "output", "books", slug);
        var viMd = Path.Combine(bookDir, "final", "vi.md");
        var epub = Path.Combine(bookDir, "trilingual.epub");
        var audiobookDir = Path.Combine(bookDir, "audiobook");

        var mp3Count = Directory.Exists(audiobookDir)
            ? Directory.GetFiles(audiobookDir, "ch*.mp3").Length : 0;

        var progressDir = Path.Combine(projectRoot, "working", "progress", slug);
        var progressCount = Directory.Exists(progressDir)
            ? Directory.GetFiles(progressDir, "chunk_*.json").Length : 0;

        var chunksDir = Path.Combine(projectRoot, "working", "chunks", slug);
        var totalChunks = Directory.Exists(chunksDir)
            ? Directory.GetFiles(chunksDir, "chunk-*.json").Length : 0;

        var totalChapters = 0;
        if (File.Exists(viMd))
        {
            var content = File.ReadAllText(viMd);
            totalChapters = Regex.Matches(content, @"^# ", RegexOptions.Multiline).Count;
        }

        return new BookStatus
        {
            Slug = slug,
            Source = source,
            HasViMd = File.Exists(viMd),
            HasEpub = File.Exists(epub),
            Mp3Count = mp3Count,
            TotalChapters = totalChapters,
            ProgressCount = progressCount,
            TotalChunks = totalChunks,
        };
    }

    private void LoadApiStatus()
    {
        try
        {
            var config = ConfigService.Load();
            ActiveProvider = config.ActiveProvider;
            var providerConfig = ConfigService.GetProvider(config.ActiveProvider);
            IsApiOk = !string.IsNullOrEmpty(providerConfig?.ApiKey);
        }
        catch { }
    }

    private static string FindProjectRoot()
    {
        // Tim project root tu vi tri executable
        var dir = AppDomain.CurrentDomain.BaseDirectory;
        while (dir != null)
        {
            if (File.Exists(Path.Combine(dir, "TranslateBook.csproj")))
                return Path.GetDirectoryName(dir)!;
            dir = Path.GetDirectoryName(dir);
        }
        // Fallback
        return Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", ".."));
    }
}
