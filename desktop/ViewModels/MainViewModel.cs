using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TranslateBook.Models;
using TranslateBook.Services;
using TranslateBook.Views;

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
    [ObservableProperty] private bool _logExpanded = true;
    [ObservableProperty] private string _logFilter = "";
    [ObservableProperty] private string _globalSearchQuery = "";

    [ObservableProperty] private double _audioTemperature = 0.3;
    [ObservableProperty] private int _audioTopK = 10;

    [ObservableProperty] private string _selectedProvider = "deepseek";
    [ObservableProperty] private string _apiKeyInput = "";
    [ObservableProperty] private string _modelInput = "";
    [ObservableProperty] private string _baseUrlInput = "";

    // Pipeline properties
    [ObservableProperty] private int _pipelineFromStep = 1;
    [ObservableProperty] private int _pipelineToStep = 10;
    [ObservableProperty] private string _selectedLang = "auto";
    [ObservableProperty] private string _epubAuthor = "";
    [ObservableProperty] private string _epubTitle = "";
    [ObservableProperty] private bool _isPipelineBusy;

    // Voice properties
    [ObservableProperty] private ObservableCollection<string> _voiceList = new();
    [ObservableProperty] private string _selectedVoice = "";
    [ObservableProperty] private string _voiceName = "";
    [ObservableProperty] private string _voiceGender = "";
    [ObservableProperty] private string _voiceDescription = "";
    [ObservableProperty] private bool _isVoiceBusy;
    [ObservableProperty] private string _voicePreviewText = "Xin chào, đây là đoạn đọc thử giọng.";

    // QA properties
    [ObservableProperty] private string _qaReport = "";
    [ObservableProperty] private bool _hasQaReport;
    [ObservableProperty] private bool _isQaBusy;
    [ObservableProperty] private bool _showQaReport;

    // Audiobook extra properties
    [ObservableProperty] private string _audioBitrate = "128k";
    [ObservableProperty] private bool _audioReadTitles = true;
    [ObservableProperty] private bool _audioMergeChapters;
    [ObservableProperty] private bool _audioForceRegenerate;
    [ObservableProperty] private string _audioChapterInput = "";

    private const int MaxLogLines = 2000;
    private CancellationTokenSource? _currentCts;
    private readonly DispatcherTimer _progressTimer;

    /// <summary>Structured log entries so the UI can color and filter them.</summary>
    public readonly record struct LogEntry(string Text, string Level);
    public event Action<LogEntry>? LogEntryAdded;
    public event Action? LogCleared;

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

        AppendLog($"Bắt đầu tạo audio: {book.Slug} (nhiệt độ={AudioTemperature}, top_k={AudioTopK}, bitrate={AudioBitrate})");
        try
        {
            var ok = await _pipeline.RunAudiobookAsync(
                book.Slug,
                AudioTemperature.ToString("0.0"),
                AudioTopK.ToString(),
                AudioBitrate,
                AudioReadTitles,
                AudioMergeChapters,
                AudioForceRegenerate,
                AudioChapterInput,
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

        // Check if any output book has a QA report
        if (!HasQaReport)
        {
            foreach (var book in OutputBooks)
            {
                var reportPath = Path.Combine(_projectRoot, "working", "qa", $"{book.Slug}_report.md");
                if (File.Exists(reportPath))
                {
                    HasQaReport = true;
                    QaReport = File.ReadAllText(reportPath);
                    break;
                }
            }
        }
    }

    private void AppendLog(string msg, string level = "info")
    {
        var time = DateTime.Now.ToString("HH:mm:ss");
        // ANSI-style color markers for parsing in RichTextBox later
        var colorTag = level switch
        {
            "error" => "[ERR]",
            "warning" => "[WARN]",
            _ => "[INFO]"
        };
        string line = $"[{time}] {colorTag} {msg}";
        LogText += line + "\n";

        if (LogText.Length > 80_000)
        {
            var lines = LogText.Split('\n');
            if (lines.Length > MaxLogLines)
            {
                LogText = string.Join("\n", lines[^MaxLogLines..]);
            }
        }

        LogEntryAdded?.Invoke(new LogEntry(line, level));
    }

    /// <summary>Clears the on-screen log and notifies the UI to drop colored entries.</summary>
    public void ClearLog()
    {
        LogText = "";
        LogCleared?.Invoke();
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

    /// <summary>
    /// Locates the EPUB used for the "Đọc thử" preview. Priority:
    /// 1. trilingual.epub (ZH books, trilingual root file)
    /// 2. final/vi.epub (EN books, Vietnamese-only file)
    /// 3. any other *.epub under the book folder
    /// Returns null when no EPUB exists for the book.
    /// </summary>
    private static string? FindPreviewEpub(string bookDir)
    {
        var trilingual = Path.Combine(bookDir, "trilingual.epub");
        if (File.Exists(trilingual)) return trilingual;

        var viEpub = Path.Combine(bookDir, "final", "vi.epub");
        if (File.Exists(viEpub)) return viEpub;

        var anyEpub = Directory.Exists(bookDir)
            ? Directory.GetFiles(bookDir, "*.epub", SearchOption.AllDirectories)
                  .OrderBy(p => p.Length) // prefer closest to root
                  .FirstOrDefault()
            : null;
        return anyEpub;
    }

    private static BookStatus GetBookStatus(string projectRoot, string slug, string source)
    {
        var bookDir = Path.Combine(projectRoot, "output", "books", slug);
        var viMd = Path.Combine(bookDir, "final", "vi.md");
        var epub = FindPreviewEpub(bookDir);
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

    // ==================== PIPELINE COMMANDS ====================

    [RelayCommand]
    private async Task RunPipelineAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        book.IsBusy = true;
        IsPipelineBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Bắt đầu chạy pipeline: {book.Slug} (bước {PipelineFromStep}→{PipelineToStep}, ngôn ngữ={SelectedLang})");
        try
        {
            var ok = await _pipeline.RunPipelineAsync(
                book.FilePath, book.Slug, SelectedLang,
                PipelineFromStep, PipelineToStep, force: false,
                author: EpubAuthor, ct: ct);

            if (ok) AppendLog($"Pipeline hoàn thành: {book.Slug}");
            else AppendLog($"[Lỗi] Pipeline thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy pipeline: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            IsPipelineBusy = false;
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    [RelayCommand]
    private async Task ExtractBookAsync(BookStatus book)
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

        AppendLog($"Bắt đầu trích xuất: {book.Slug}");
        try
        {
            var ok = await _pipeline.RunExtractAsync(book.FilePath, book.Slug, SelectedLang, ct);
            if (ok) AppendLog($"Trích xuất thành công: {book.Slug}");
            else AppendLog($"[Lỗi] Trích xuất thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy trích xuất: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            _currentCts = null;
        }
    }

    [RelayCommand]
    private async Task GenerateGlossaryAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        var sourceDir = Path.Combine(_projectRoot, "working", "extracted", book.Slug);
        if (!Directory.Exists(sourceDir))
        {
            AppendLog($"[Lỗi] Không tìm thấy extracted cho: {book.Slug}. Chạy Extract trước.", "error");
            return;
        }

        book.IsBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        var glossaryPath = Path.Combine(_projectRoot, "glossary", $"{book.Slug}.csv");
        AppendLog($"Bắt đầu tạo glossary: {book.Slug}");
        try
        {
            var ok = await _pipeline.RunGlossaryAsync(sourceDir, book.Slug, glossaryPath, ct);
            if (ok) AppendLog($"Glossary đã tạo: {glossaryPath}");
            else AppendLog($"[Lỗi] Tạo glossary thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy tạo glossary: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            _currentCts = null;
        }
    }

    [RelayCommand]
    private async Task MergeChunksAsync(BookStatus book)
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

        var lang = ContainsChinese(File.Exists(book.FilePath) ? File.ReadAllText(book.FilePath) : book.Slug) ? "trilingual" : "bilingual";
        AppendLog($"Bắt đầu gộp chunks: {book.Slug} (format={lang})");
        try
        {
            var ok = await _pipeline.RunMergeAsync(book.Slug, lang, force: true, ct);
            if (ok) AppendLog($"Gộp chunks thành công: {book.Slug}");
            else AppendLog($"[Lỗi] Gộp chunks thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy gộp chunks: {book.Slug}");
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

    [RelayCommand]
    private async Task MakeEpubAsync(BookStatus book)
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

        var title = string.IsNullOrWhiteSpace(EpubTitle) ? book.DisplayTitle : EpubTitle;
        AppendLog($"Bắt đầu tạo EPUB: {book.Slug} (title={title})");
        try
        {
            var ok = await _pipeline.RunMakeEpubAsync(book.Slug, title, EpubAuthor, ct);
            if (ok) AppendLog($"EPUB đã tạo: {book.Slug}");
            else AppendLog($"[Lỗi] Tạo EPUB thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy tạo EPUB: {book.Slug}");
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

    [RelayCommand]
    private async Task OpenEpubPreviewAsync(BookStatus book)
    {
        if (book == null) return;
        if (string.IsNullOrWhiteSpace(_projectRoot))
        {
            AppendLog("[Lỗi] Chưa xác định thư mục dự án, không thể mở xem thử EPUB.", "error");
            return;
        }
        if (string.IsNullOrWhiteSpace(book.Slug))
        {
            AppendLog("[Lỗi] Sách không có slug hợp lệ, không thể mở xem thử EPUB.", "error");
            return;
        }

        var bookDir = Path.Combine(_projectRoot, "output", "books", book.Slug);
        var epubPath = FindPreviewEpub(bookDir);
        if (string.IsNullOrEmpty(epubPath))
        {
            AppendLog($"[Lỗi] File EPUB preview chưa tồn tại cho sách '{book.Slug}'.", "error");
            return;
        }

        var app = Application.Current;
        if (app == null)
        {
            AppendLog("[Lỗi] Ứng dụng chưa khởi tạo (Application.Current == null), không thể mở cửa sổ xem thử EPUB.", "error");
            return;
        }

        await app.Dispatcher.InvokeAsync(() =>
        {
            try
            {
                var window = new EpubPreviewWindow();
                if (app.MainWindow != null)
                    window.Owner = app.MainWindow;
                window.LoadEpubFile(epubPath);
                window.Show();
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Không thể mở cửa sổ xem thử EPUB: {ex.Message}", "error");
            }
        });
    }

    // ==================== QA COMMAND ====================

    [RelayCommand]
    private async Task RunQaAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        var viMd = Path.Combine(_projectRoot, "output", "books", book.Slug, "final", "vi.md");
        var sourceMd = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw.md");
        if (!File.Exists(viMd))
        {
            AppendLog($"[Lỗi] Chưa có vi.md cho: {book.Slug}", "error");
            return;
        }
        if (!File.Exists(sourceMd))
        {
            AppendLog($"[Lỗi] Chưa có source cho: {book.Slug}", "error");
            return;
        }

        IsQaBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        var reportPath = Path.Combine(_projectRoot, "working", "qa", $"{book.Slug}_report.md");
        Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);

        var lang = ContainsChinese(File.ReadAllText(sourceMd)) ? "zh" : "en";
        var glossaryPath = Path.Combine(_projectRoot, "glossary", $"{book.Slug}.csv");

        AppendLog($"Chạy QA: {book.Slug}");
        try
        {
            var ok = await _pipeline.RunQaAsync(sourceMd, viMd, lang,
                File.Exists(glossaryPath) ? glossaryPath : "",
                threshold: 5.0, reportPath: reportPath, ct);

            if (File.Exists(reportPath))
            {
                QaReport = await File.ReadAllTextAsync(reportPath, ct);
                HasQaReport = true;
            }

            if (ok) AppendLog($"QA OK: {book.Slug}");
            else AppendLog($"QA phát hiện lỗi: {book.Slug} — xem report", "warning");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy QA: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            IsQaBusy = false;
            _currentCts = null;
        }
    }

    [RelayCommand]
    private void ToggleQaReport(BookStatus? book)
    {
        if (ShowQaReport)
        {
            ShowQaReport = false;
            return;
        }

        if (book == null) return;

        // Try to load existing report
        var reportPath = Path.Combine(_projectRoot, "working", "qa", $"{book.Slug}_report.md");
        if (File.Exists(reportPath))
        {
            QaReport = File.ReadAllText(reportPath);
            HasQaReport = true;
        }

        if (HasQaReport)
            ShowQaReport = !ShowQaReport;
    }

    // ==================== VOICE COMMANDS ====================

    [RelayCommand]
    private async Task LoadVoicesAsync()
    {
        var voices = await _pipeline.GetVoiceListAsync();
        VoiceList.Clear();
        foreach (var v in voices) VoiceList.Add(v);
        if (VoiceList.Count > 0 && string.IsNullOrEmpty(SelectedVoice))
            SelectedVoice = VoiceList[0];
        AppendLog($"Đã tải {VoiceList.Count} giọng");
    }

    [RelayCommand]
    private async Task PreviewVoiceAsync()
    {
        if (string.IsNullOrWhiteSpace(SelectedVoice) || IsVoiceBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        IsVoiceBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;
        var previewPath = Path.Combine(_projectRoot, "output", "voice_preview", $"preview_{SelectedVoice}.wav");

        AppendLog($"Đang tạo bản đọc thử: {SelectedVoice}");
        try
        {
            var escapedText = VoicePreviewText.Replace("\\", "\\\\").Replace("\"", "\\\"");
            var args = $"preview \"{SelectedVoice}\" --text \"{escapedText}\"";
            var ok = await _pipeline.RunManageVoiceAsync(args, ct);

            if (!ok || !File.Exists(previewPath))
            {
                AppendLog($"[Lỗi] Không tạo được file đọc thử cho giọng: {SelectedVoice}", "error");
                return;
            }

            AppendLog($"Đã tạo bản đọc thử: {previewPath}");
            Process.Start(new ProcessStartInfo
            {
                FileName = previewPath,
                UseShellExecute = true,
            });
        }
        catch (OperationCanceledException)
        {
            AppendLog("Đã hủy đọc thử giọng.", "warning");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] Đọc thử giọng: {ex.Message}", "error");
        }
        finally
        {
            IsVoiceBusy = false;
            _currentCts = null;
        }
    }

    [RelayCommand]
    private async Task SetActiveVoiceAsync()
    {
        if (string.IsNullOrEmpty(SelectedVoice)) return;
        try
        {
            await _pipeline.RunManageVoiceAsync($"set-active \"{SelectedVoice}\"");
            AppendLog($"Đã set giọng active: {SelectedVoice}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] Set active voice: {ex.Message}", "error");
        }
    }

    [RelayCommand]
    private void ToggleLog()
    {
        LogExpanded = !LogExpanded;
    }

    [RelayCommand]
    private void FocusSearchInBooks()
    {
        // The BooksPage owns the actual search control focus.
    }

    [RelayCommand]
    private async Task RunPipelineFirstBookAsync()
    {
        if (InputBooks.Count == 0) return;
        await RunPipelineCommand.ExecuteAsync(InputBooks[0]);
    }

    [RelayCommand]
    private async Task ExtractVoiceAsync()
    {
        if (string.IsNullOrWhiteSpace(VoiceName)) return;
        IsVoiceBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Trích xuất giọng: {VoiceName}");
        try
        {
            var args = $"extract --name \"{VoiceName}\" --auto";
            if (!string.IsNullOrWhiteSpace(VoiceGender)) args += $" --gender {VoiceGender}";
            if (!string.IsNullOrWhiteSpace(VoiceDescription)) args += $" --description \"{VoiceDescription}\"";
            var ok = await _pipeline.RunManageVoiceAsync(args, ct);
            if (ok)
            {
                AppendLog($"Đã trích xuất giọng: {VoiceName}");
                await LoadVoicesAsync();
            }
            else AppendLog($"[Lỗi] Trích xuất giọng thất bại", "error");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            IsVoiceBusy = false;
            _currentCts = null;
        }
    }
}
