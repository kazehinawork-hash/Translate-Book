using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TranslateBook.Models;
using TranslateBook.Services;

namespace TranslateBook.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly PythonPipelineService _pipeline;
    private readonly ApiTranslationService _apiService = new();
    private readonly string _projectRoot;

    [ObservableProperty] private BookStatus? _selectedBook;
    [ObservableProperty] private int _selectedTabIndex;
    [ObservableProperty] private string _logText = "";
    [ObservableProperty] private string _activeProvider = "";
    [ObservableProperty] private bool _isApiOk;

    [ObservableProperty] private double _audioTemperature = 0.3;
    [ObservableProperty] private int _audioTopK = 10;

    [ObservableProperty] private string _selectedProvider = "deepseek";
    [ObservableProperty] private string _apiKeyInput = "";
    [ObservableProperty] private string _modelInput = "";
    [ObservableProperty] private string _baseUrlInput = "";

    private const int MaxLogLines = 2000;
    private CancellationTokenSource? _currentCts;
    private readonly DispatcherTimer _progressTimer;

    public ObservableCollection<BookStatus> InputBooks { get; } = new();
    public ObservableCollection<BookStatus> OutputBooks { get; } = new();

    partial void OnSelectedProviderChanged(string value)
    {
        LoadApiConfigForSelectedProvider();
    }

    public MainViewModel()
    {
        _projectRoot = ProjectHelper.FindProjectRoot();
        _pipeline = new PythonPipelineService(_projectRoot);
        _pipeline.OutputReceived += msg =>
        {
            if (App.Current != null)
                App.Current.Dispatcher.Invoke(() => AppendLog(msg));
        };
        _pipeline.ErrorReceived += msg =>
        {
            if (App.Current != null)
                App.Current.Dispatcher.Invoke(() => AppendLog(msg, "error"));
        };

        _progressTimer = new DispatcherTimer();
        _progressTimer.Interval = TimeSpan.FromSeconds(3);
        _progressTimer.Tick += (s, e) => RefreshBookProgress();
        _progressTimer.Start();

        LoadBooks();
        LoadApiStatus();
    }

    public void LoadBooks()
    {
        InputBooks.Clear();
        OutputBooks.Clear();

        var booksDir = Path.Combine(_projectRoot, "output", "books");
        var inputDir = Path.Combine(_projectRoot, "input");

        if (Directory.Exists(booksDir))
        {
            foreach (var d in Directory.GetDirectories(booksDir).OrderBy(x => x))
            {
                var slug = Path.GetFileName(d);
                OutputBooks.Add(GetBookStatus(_projectRoot, slug, "output"));
            }
        }

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

        AppendLog($"Đã tải {InputBooks.Count} input, {OutputBooks.Count} output");
    }

    [RelayCommand]
    private void RefreshBooks()
    {
        LoadBooks();
    }

    [RelayCommand]
    private void Cancel()
    {
        _currentCts?.Cancel();
        KillCurrentProcess();
        AppendLog("Đang hủy...");
    }

    public void KillCurrentProcess()
    {
        _currentCts?.Cancel();
        _pipeline.KillCurrentProcess();
    }

    [RelayCommand]
    private async Task TestApiConnectionAsync(string provider)
    {
        AppendLog($"Đang kiểm tra {provider}...");
        var (ok, msg) = await _apiService.TestConnectionAsync(provider);
        if (ok)
        {
            IsApiOk = true;
            ActiveProvider = provider;
            AppendLog($"Kết nối OK — {provider}: {msg}");
        }
        else
        {
            IsApiOk = false;
            AppendLog($"Lỗi — {provider}: {msg}", "error");
        }
    }

    [RelayCommand]
    private async Task StartTranslateAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        var chunksDir = Path.Combine(_projectRoot, "working", "chunks", book.Slug);
        if (!Directory.Exists(chunksDir))
        {
            AppendLog($"[Lỗi] Không tìm thấy thư mục chunks cho: {book.Slug}", "error");
            return;
        }

        book.IsBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Bắt đầu dịch: {book.Slug}");
        try
        {
            await TranslateBookInAppAsync(book, chunksDir, ct);
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy bỏ dịch: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    private async Task TranslateBookInAppAsync(BookStatus book, string chunksDir, CancellationToken ct)
    {
        var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
        var glossary = ApiTranslationService.LoadGlossary(book.Slug, _projectRoot);

        Directory.CreateDirectory(progressDir);

        var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json")
            .OrderBy(f => f).ToArray();
        var totalChunks = chunkFiles.Length;
        book.TotalChunks = totalChunks;

        if (totalChunks == 0)
        {
            AppendLog($"[Lỗi] Không có chunk nào trong {chunksDir}", "error");
            return;
        }

        int doneCount = 0;
        AppendLog($"Tìm thấy {totalChunks} chunk, bắt đầu dịch...");

        foreach (var chunkFile in chunkFiles)
        {
            ct.ThrowIfCancellationRequested();

            var chunkJson = await File.ReadAllTextAsync(chunkFile, ct);
            using var chunkDoc = JsonDocument.Parse(chunkJson);
            var chunk = chunkDoc.RootElement;

            var chunkId = chunk.GetProperty("chunk_id").GetInt32();
            var progressFile = Path.Combine(progressDir, $"chunk_{chunkId:03d}.json");

            // Check if already translated
            if (File.Exists(progressFile))
            {
                var existingJson = await File.ReadAllTextAsync(progressFile, ct);
                using var existingDoc = JsonDocument.Parse(existingJson);
                var existing = existingDoc.RootElement;

                if (existing.TryGetProperty("translated_text", out var transProp)
                    && !string.IsNullOrWhiteSpace(transProp.GetString()))
                {
                    doneCount++;
                    book.ProgressCount = doneCount;
                    continue;
                }
            }

            // Determine source text and mode
            string sourceText;
            string chapter = "";
            bool isTrilingual = false;
            int totalFromData = 0;
            int wordCountSrc = 0;
            string originalText = "";
            string pinyinText = "";

            if (File.Exists(progressFile))
            {
                // Skeleton exists — read original_text from it
                var progJson = await File.ReadAllTextAsync(progressFile, ct);
                using var progDoc = JsonDocument.Parse(progJson);
                var prog = progDoc.RootElement;

                originalText = prog.TryGetProperty("original_text", out var ot) ? ot.GetString() ?? "" : "";
                pinyinText = prog.TryGetProperty("pinyin_text", out var pt2) ? pt2.GetString() ?? "" : "";
                sourceText = !string.IsNullOrEmpty(originalText) ? originalText :
                             (prog.TryGetProperty("source_text", out var st) ? st.GetString() ?? "" : "");
                chapter = prog.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : "";
                isTrilingual = prog.TryGetProperty("mode", out var md) && md.GetString() == "trilingual";
                totalFromData = prog.TryGetProperty("total_chunks", out var tc) ? tc.GetInt32() : 0;
                wordCountSrc = prog.TryGetProperty("word_count_source", out var wc) ? wc.GetInt32() : 0;
            }
            else
            {
                // No skeleton — use chunk text directly
                sourceText = chunk.TryGetProperty("text", out var tp) ? tp.GetString() ?? "" : "";
                chapter = chunk.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : "";
                totalFromData = chunk.TryGetProperty("total_chunks", out var tc) ? tc.GetInt32() : 0;
                wordCountSrc = chunk.TryGetProperty("word_count", out var wc) ? wc.GetInt32() : 0;
                isTrilingual = ContainsChinese(sourceText);
            }

            if (string.IsNullOrWhiteSpace(sourceText))
            {
                AppendLog($"  [Bỏ qua] Chunk {chunkId} rỗng", "warning");
                continue;
            }

            var sourceLang = isTrilingual ? "Chinese" : "English";
            AppendLog($"→ [{doneCount + 1}/{totalChunks}] Dịch chunk {chunkId}: {chapter}");

            var result = await _apiService.TranslateAsync(
                sourceText, ActiveProvider, glossary,
                sourceLang: sourceLang, targetLang: "Vietnamese",
                trilingual: isTrilingual, ct: ct);

            // Save progress JSON
            var progressData = new Dictionary<string, object>
            {
                ["chunk_id"] = chunkId,
                ["total_chunks"] = totalFromData > 0 ? totalFromData : totalChunks,
                ["chapter"] = chapter,
                ["source_text"] = sourceText,
                ["translated_text"] = result.Text,
                ["translated_at"] = DateTime.Now.ToString("o"),
                ["word_count_source"] = wordCountSrc,
                ["word_count_translated"] = result.Text.Split().Length,
            };

            if (isTrilingual)
            {
                progressData["mode"] = "trilingual";
                progressData["original_text"] = string.IsNullOrEmpty(originalText) ? sourceText : originalText;
                progressData["pinyin_text"] = pinyinText;
            }

            var progressJson = JsonSerializer.Serialize(progressData,
                new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
            await File.WriteAllTextAsync(progressFile, progressJson, ct);

            doneCount++;
            book.ProgressCount = doneCount;
            var pct = (double)doneCount / totalChunks * 100;
            AppendLog($"  ✅ Chunk {chunkId} đã lưu ({doneCount}/{totalChunks} - {pct:F0}%)");
        }

        AppendLog($"Hoàn thành: {book.Slug} ({doneCount}/{totalChunks} chunk)");
    }

    [RelayCommand]
    private async Task GenerateAudiobookAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        book.IsBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Bắt đầu tạo audio: {book.Slug} (nhiệt độ={AudioTemperature}, top_k={AudioTopK})");
        try
        {
            var ok = await _pipeline.RunAudiobookAsync(
                book.Slug,
                AudioTemperature.ToString("0.0"),
                AudioTopK.ToString(),
                ct);
            if (ok) AppendLog($"Audio hoàn thành: {book.Slug}");
            else AppendLog($"[Lỗi] Tạo audio thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy bỏ tạo audio: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    private void RefreshBookProgress()
    {
        foreach (var book in OutputBooks)
        {
            var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
            if (!Directory.Exists(progressDir)) continue;

            var translated = 0;
            foreach (var f in Directory.GetFiles(progressDir, "chunk_*.json"))
            {
                try
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(f));
                    if (doc.RootElement.TryGetProperty("translated_text", out var t)
                        && !string.IsNullOrWhiteSpace(t.GetString()))
                        translated++;
                }
                catch { }
            }
            if (translated != book.ProgressCount)
                book.ProgressCount = translated;
        }
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

        // Prevent unbounded growth — trim to last ~2000 lines
        if (LogText.Length > 80_000)
        {
            var lines = LogText.Split('\n');
            if (lines.Length > MaxLogLines)
            {
                LogText = string.Join("\n", lines[^MaxLogLines..]);
            }
        }
    }

    private void UpdateBookStatus(BookStatus book)
    {
        var updated = GetBookStatus(_projectRoot, book.Slug, book.Source);
        book.HasViMd = updated.HasViMd;
        book.HasEpub = updated.HasEpub;
        book.Mp3Count = updated.Mp3Count;
        book.TotalChapters = updated.TotalChapters;
        book.ProgressCount = updated.ProgressCount;
        book.TotalChunks = updated.TotalChunks;
    }

    private static bool ContainsChinese(string text)
    {
        return text.Any(c => (c >= 0x3400 && c <= 0x9FFF) || (c >= 0xFF00 && c <= 0xFFEF));
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
            SelectedProvider = ActiveProvider;
            var providerConfig = ConfigService.GetProvider(config.ActiveProvider);
            IsApiOk = !string.IsNullOrEmpty(providerConfig?.ApiKey);
        }
        catch { }
    }

    private void LoadApiConfigForSelectedProvider()
    {
        try
        {
            var config = ConfigService.GetProvider(SelectedProvider);
            ModelInput = config?.Model ?? "";
            BaseUrlInput = config?.BaseUrl ?? "";
            ApiKeyInput = "";
        }
        catch { }
    }

    [RelayCommand]
    private async Task SaveApiConfigAsync()
    {
        AppendLog($"Đang lưu cấu hình API cho provider {SelectedProvider}...");
        try
        {
            var config = ConfigService.Load();
            if (!config.Providers.ContainsKey(SelectedProvider))
            {
                config.Providers[SelectedProvider] = new ProviderConfig();
            }

            var p = config.Providers[SelectedProvider];

            if (!string.IsNullOrWhiteSpace(ApiKeyInput))
            {
                p.ApiKey = ApiKeyInput;
            }

            p.Model = ModelInput;
            p.BaseUrl = BaseUrlInput;
            config.ActiveProvider = SelectedProvider;

            ConfigService.Save(config);

            LoadApiStatus();
            AppendLog($"Đã lưu cấu hình {SelectedProvider}");
        }
        catch (Exception ex)
        {
            AppendLog($"Lỗi lưu cấu hình: {ex.Message}", "error");
        }
    }
}
