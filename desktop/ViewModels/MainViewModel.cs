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
    /// <summary>Set true by Ctrl+F so BooksPage focuses its search box on load.</summary>
    [ObservableProperty] private bool _focusSearchRequested;

    [ObservableProperty] private double _audioTemperature = 0.3;
    [ObservableProperty] private int _audioTopK = 10;

    [ObservableProperty] private string _selectedProvider = "deepseek";
    [ObservableProperty] private string _apiKeyInput = "";
    [ObservableProperty] private string _modelInput = "";
    [ObservableProperty] private string _baseUrlInput = "";
    [ObservableProperty] private ObservableCollection<string> _availableModels = new();

    // Pipeline properties
    [ObservableProperty] private int _pipelineFromStep = 1;
    [ObservableProperty] private int _pipelineToStep = 10;
    [ObservableProperty] private string _selectedLang = "auto";
    [ObservableProperty] private string _epubAuthor = "";
    [ObservableProperty] private string _epubTitle = "";
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsBusyAny))]
    private bool _isPipelineBusy;
    [ObservableProperty] private string _busyMessage = "";

    // Voice properties
    [ObservableProperty] private ObservableCollection<string> _voiceList = new();
    [ObservableProperty] private string _selectedVoice = "";
    [ObservableProperty] private string _voiceName = "";
    [ObservableProperty] private string _voiceGender = "";
    [ObservableProperty] private string _voiceDescription = "";
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsBusyAny))]
    private bool _isVoiceBusy;
    [ObservableProperty] private string _voicePreviewText = "Xin chào, đây là đoạn đọc thử giọng.";

    // QA properties
    [ObservableProperty] private string _qaReport = "";
    [ObservableProperty] private bool _hasQaReport;
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsBusyAny))]
    private bool _isQaBusy;
    [ObservableProperty] private bool _showQaReport;

    // Audiobook extra properties
    [ObservableProperty] private string _audioBitrate = "128k";
    [ObservableProperty] private bool _audioReadTitles = true;
    [ObservableProperty] private bool _audioMergeChapters;
    [ObservableProperty] private bool _audioForceRegenerate;
    [ObservableProperty] private string _audioChapterInput = "";
    [ObservableProperty] private bool _audioUseGpu = true;
    [ObservableProperty] private int _audioBatchSize = 16;
    [ObservableProperty] private bool _audioMusicAuto = true;
    [ObservableProperty] private double _audioMusicVolume = 0.15;

    private const int MaxLogLines = 2000;
    private CancellationTokenSource? _currentCts;
    private readonly DispatcherTimer _progressTimer;

    /// <summary>Structured log entries so the UI can color and filter them.</summary>
    public readonly record struct LogEntry(string Text, string Level);
    public event Action<LogEntry>? LogEntryAdded;
    public event Action? LogCleared;

    public ObservableCollection<BookStatus> InputBooks { get; } = new();
    public ObservableCollection<BookStatus> OutputBooks { get; } = new();

    /// <summary>True when any long-running operation is active — drives the busy overlay.</summary>
    public bool IsBusyAny => IsPipelineBusy || IsVoiceBusy || IsQaBusy || IsSampleBusy
        || InputBooks.Any(b => b.IsBusy) || OutputBooks.Any(b => b.IsBusy);

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
            {
                App.Current.Dispatcher.Invoke(() =>
                {
                    var isRealError = msg.Contains("Error") || msg.Contains("Exception") || msg.Contains("Traceback") || msg.Contains("Failed");
                    var isWarning = msg.Contains("Warning") || msg.Contains("WARN") || msg.Contains("warning");
                    var level = isRealError ? "error" : isWarning ? "warning" : "info";
                    AppendLog(msg, level);
                });
            }
        };

        // Keep the global busy overlay in sync with per-book busy states.
        Models.BookStatus.AnyBusyChanged += OnAnyBookBusyChanged;

        _progressTimer = new DispatcherTimer();
        _progressTimer.Interval = TimeSpan.FromSeconds(3);
        _progressTimer.Tick += (s, e) => RefreshBookProgress();
        _progressTimer.Start();

        LoadBooks();
        LoadApiStatus();
        _ = LoadVoicesAsync();
    }

    private void OnAnyBookBusyChanged() => OnPropertyChanged(nameof(IsBusyAny));

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
                var title = Path.GetFileName(d);
                OutputBooks.Add(GetBookStatus(_projectRoot, d, title, "output"));
            }
        }

        if (Directory.Exists(inputDir))
        {
            // input/ giờ chia thư mục con (chua-lam/, da-dich/, da-audio/) — quét đệ quy
            foreach (var f in Directory.GetFiles(inputDir, "*", SearchOption.AllDirectories).OrderBy(x => x))
            {
                var ext = Path.GetExtension(f).ToLower();
                if (ext is ".pdf" or ".epub" or ".docx")
                {
                    var name = Path.GetFileName(f);
                    var relDir = Path.GetRelativePath(inputDir, Path.GetDirectoryName(f) ?? inputDir);
                    var category = relDir.Replace("\\", "/").Split('/')[0];
                    if (string.IsNullOrEmpty(category) || category == ".") category = "chua-lam";

                    var rawTitle = Path.GetFileNameWithoutExtension(f);
                    // Tìm xem đã có thư mục output tương ứng để lấy slug chuẩn chưa
                    var slug = SanitizeFileName(rawTitle);
                    var candidateOutputDir = Path.Combine(_projectRoot, "output", "books", rawTitle);
                    if (Directory.Exists(candidateOutputDir))
                    {
                        var metaPath = Path.Combine(candidateOutputDir, "metadata.json");
                        if (File.Exists(metaPath))
                        {
                            try
                            {
                                using var doc = JsonDocument.Parse(File.ReadAllText(metaPath));
                                if (doc.RootElement.TryGetProperty("slug", out var sp) && !string.IsNullOrEmpty(sp.GetString()))
                                    slug = sp.GetString()!;
                            }
                            catch { }
                        }
                    }

                    var book = new BookStatus
                    {
                        Slug = slug,
                        Title = rawTitle,
                        Source = "input",
                        FilePath = f,
                        FolderPath = Path.GetDirectoryName(f) ?? inputDir,
                        InputCategory = category,
                        EpubTitle = rawTitle
                    };

                    // Nạp sẵn danh sách chương để Dropdown luôn có sẵn dữ liệu chọn
                    var chunksDir = Path.Combine(_projectRoot, "working", "chunks", slug);
                    if (Directory.Exists(chunksDir))
                    {
                        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                        foreach (var chunkFile in Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(x => x))
                        {
                            try
                            {
                                using var doc = JsonDocument.Parse(File.ReadAllText(chunkFile));
                                if (doc.RootElement.TryGetProperty("chapter", out var ch))
                                {
                                    var chName = ch.GetString();
                                    if (!string.IsNullOrWhiteSpace(chName) && seen.Add(chName))
                                        book.AvailableChapters.Add(chName);
                                }
                            }
                            catch { }
                        }
                    }

                    if (book.AvailableChapters.Count == 0)
                    {
                        book.AvailableChapters.Add("Chương 1 (Mặc định)");
                        book.AvailableChapters.Add("Chương 2");
                        book.AvailableChapters.Add("Chương 3");
                        book.AvailableChapters.Add("Chương 4");
                        book.AvailableChapters.Add("Chương 5");
                    }
                    book.SelectedSampleChapter = book.AvailableChapters[0];

                    InputBooks.Add(book);
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
    private void OpenBookFolder(BookStatus? book)
    {
        if (book == null) return;
        var path = !string.IsNullOrEmpty(book.FolderPath) && Directory.Exists(book.FolderPath)
            ? book.FolderPath
            : (!string.IsNullOrEmpty(book.FilePath) && File.Exists(book.FilePath)
                ? Path.GetDirectoryName(book.FilePath)
                : Path.Combine(_projectRoot, "output", "books", book.Title));

        if (!string.IsNullOrEmpty(path) && Directory.Exists(path))
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = path,
                UseShellExecute = true
            });
        }
        else
        {
            AppendLog($"[Lỗi] Thư mục không tồn tại: {path}", "warning");
        }
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
        BusyMessage = $"Đang dịch: {book.Slug}...";
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
            BusyMessage = "";
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

    // ==================== SAMPLE TRANSLATION (DỊCH MẪU 1 CHƯƠNG) ====================

    [ObservableProperty] private string _selectedSampleChapter = "";
    [ObservableProperty] private bool _isSampleBusy;
    [ObservableProperty] private string _lastSampleMdPath = "";

    /// <summary>
    /// Tải danh sách các chương của 1 cuốn sách từ thư mục working/chunks/<slug>/
    /// để người dùng chọn chương muốn dịch thử riêng cho cuốn sách đó.
    /// </summary>
    [RelayCommand]
    private async Task LoadChaptersAsync(BookStatus book)
    {
        if (book == null) return;
        book.AvailableChapters.Clear();
        book.SelectedSampleChapter = "";

        var chapters = await _pipeline.GetChapterListAsync(book.Slug);
        foreach (var c in chapters)
            book.AvailableChapters.Add(c);

        if (book.AvailableChapters.Count > 0)
        {
            book.SelectedSampleChapter = book.AvailableChapters[0];
        }
    }

    [RelayCommand]
    private async Task SampleTranslateAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        book.IsBusy = true;
        IsSampleBusy = true;
        BusyMessage = $"Đang chuẩn bị dịch thử: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        try
        {
            var chunksDir = Path.Combine(_projectRoot, "working", "chunks", book.Slug);
            if (!Directory.Exists(chunksDir) || Directory.GetFiles(chunksDir, "chunk-*.json").Length == 0)
            {
                AppendLog($"[Dịch thử] Sách '{book.Slug}' chưa có dữ liệu chunk. Đang tự động trích xuất nội dung (Extract & Chunk)...");
                BusyMessage = $"Đang trích xuất nội dung: {book.Slug}...";

                // Chạy extract
                var okExtract = await _pipeline.RunExtractAsync(book.FilePath, book.Slug, string.IsNullOrWhiteSpace(book.PipelineLang) ? "auto" : book.PipelineLang, ct);
                if (!okExtract)
                {
                    AppendLog($"[Lỗi] Không thể trích xuất file: {book.FilePath}", "error");
                    return;
                }

                // Chạy chunk
                var rawMdPath = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw.md");
                if (!File.Exists(rawMdPath))
                {
                    AppendLog($"[Lỗi] Không tìm thấy raw.md sau khi extract: {rawMdPath}", "error");
                    return;
                }

                var okChunk = await _pipeline.RunChunkAsync(rawMdPath, chunksDir, ct);
                if (!okChunk)
                {
                    AppendLog($"[Lỗi] Không thể chia chunk: {rawMdPath}", "error");
                    return;
                }

                await LoadChaptersAsync(book);
            }

            if (book.AvailableChapters.Count == 0)
            {
                await LoadChaptersAsync(book);
            }

            var chosenChapter = book.SelectedSampleChapter;
            if (string.IsNullOrWhiteSpace(chosenChapter) && book.AvailableChapters.Count > 0)
            {
                chosenChapter = book.AvailableChapters[0];
                book.SelectedSampleChapter = chosenChapter;
            }

            if (string.IsNullOrWhiteSpace(chosenChapter))
            {
                chosenChapter = "Chương 1";
            }

            // Kiểm tra xem đã có skeleton (original_text dòng-đối-dòng) chưa
            var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
            if (!Directory.Exists(progressDir))
            {
                await _pipeline.RunSkeletonAsync(chunksDir, progressDir, ct);
            }

            // Lấy danh sách chunk thuộc chương đã chọn
            var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(f => f).ToArray();
            var targetChunks = new List<(int chunkId, string text, string chapter, string originalText, string pinyinText, bool isTrilingual)>();

            foreach (var chunkFile in chunkFiles)
            {
                try
                {
                    var json = await File.ReadAllTextAsync(chunkFile, ct);
                    using var doc = System.Text.Json.JsonDocument.Parse(json);
                    var c = doc.RootElement;
                    var chapter = c.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : "";
                    if (chapter != chosenChapter) continue;

                    int chunkId = c.TryGetProperty("chunk_id", out var cid) ? cid.GetInt32() : -1;
                    var text = c.TryGetProperty("text", out var tp) ? tp.GetString() ?? "" : "";
                    bool isTrilingual = c.TryGetProperty("text", out var t2) && ContainsChinese(t2.GetString() ?? "");

                    // Nếu có skeleton, ưu tiên lấy original_text chuẩn dòng-đối-dòng của init_trilingual_skeleton.py
                    var origText = text;
                    var progChunkFile = Path.Combine(progressDir, $"chunk_{chunkId:D3}.json");
                    if (File.Exists(progChunkFile))
                    {
                        try
                        {
                            using var pdoc = JsonDocument.Parse(File.ReadAllText(progChunkFile));
                            if (pdoc.RootElement.TryGetProperty("original_text", out var ot) && !string.IsNullOrWhiteSpace(ot.GetString()))
                            {
                                origText = ot.GetString()!;
                            }
                        }
                        catch { }
                    }

                    targetChunks.Add((chunkId, origText, chapter, origText, "", isTrilingual));
                }
                catch { }
            }

            // Nếu chương không khớp tên cụ thể (hoặc sách chỉ có 1 file), lấy 1-2 chunk đầu tiên làm mẫu
            if (targetChunks.Count == 0 && chunkFiles.Length > 0)
            {
                for (int idx = 0; idx < Math.Min(2, chunkFiles.Length); idx++)
                {
                    try
                    {
                        var json = await File.ReadAllTextAsync(chunkFiles[idx], ct);
                        using var doc = System.Text.Json.JsonDocument.Parse(json);
                        var c = doc.RootElement;
                        var chapter = c.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : $"Chunk {idx + 1}";
                        int chunkId = c.TryGetProperty("chunk_id", out var cid) ? cid.GetInt32() : idx + 1;
                        var text = c.TryGetProperty("text", out var tp) ? tp.GetString() ?? "" : "";
                        bool isTrilingual = c.TryGetProperty("text", out var t2) && ContainsChinese(t2.GetString() ?? "");

                        var origText = text;
                        var progChunkFile = Path.Combine(progressDir, $"chunk_{chunkId:D3}.json");
                        if (File.Exists(progChunkFile))
                        {
                            try
                            {
                                using var pdoc = JsonDocument.Parse(File.ReadAllText(progChunkFile));
                                if (pdoc.RootElement.TryGetProperty("original_text", out var ot) && !string.IsNullOrWhiteSpace(ot.GetString()))
                                {
                                    origText = ot.GetString()!;
                                }
                            }
                            catch { }
                        }

                        targetChunks.Add((chunkId, origText, chapter, origText, "", isTrilingual));
                    }
                    catch { }
                }
            }

            if (targetChunks.Count == 0)
            {
                AppendLog($"[Lỗi] Không tìm thấy nội dung để dịch mẫu cho: {book.Slug}", "error");
                return;
            }

            var glossary = ApiTranslationService.LoadGlossary(book.Slug, _projectRoot);
            AppendLog($"Bắt đầu dịch thử: {book.Slug} (Chương: '{chosenChapter}', {targetChunks.Count} chunk)");
            var translatedResults = new List<(int chunkId, string translated, string originalText, string pinyinText, bool isTrilingual)>();

            for (int i = 0; i < targetChunks.Count; i++)
            {
                ct.ThrowIfCancellationRequested();
                var (chunkId, text, chapter, originalText, _, isTrilingual) = targetChunks[i];
                if (string.IsNullOrWhiteSpace(text))
                {
                    AppendLog($"  [Bỏ qua] Chunk {chunkId} rỗng", "warning");
                    continue;
                }

                var sourceLang = isTrilingual ? "Chinese" : "English";
                AppendLog($"  → [{i + 1}/{targetChunks.Count}] Dịch chunk {chunkId}");

                var result = await _apiService.TranslateAsync(
                    text, ActiveProvider, glossary,
                    sourceLang: sourceLang, targetLang: "Vietnamese",
                    trilingual: isTrilingual, ct: ct);

                translatedResults.Add((chunkId, result.Text, text, "", isTrilingual));
                AppendLog($"    ✅ Chunk {chunkId} xong ({result.Text.Length} ký tự)");
            }

            if (translatedResults.Count == 0)
            {
                AppendLog("[Lỗi] Không dịch được chunk nào.", "error");
                return;
            }

            // Build file preview tạm (markdown)
            var previewDir = Path.Combine(_projectRoot, "output", "preview");
            Directory.CreateDirectory(previewDir);
            var safeChapter = SanitizeFileName(chosenChapter);
            var previewPath = Path.Combine(previewDir, $"{book.Slug}-sample-{safeChapter}.md");
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"# 📖 {book.DisplayTitle}");
            sb.AppendLine();
            sb.AppendLine($"**Chương mẫu:** {chosenChapter}");
            sb.AppendLine($"**Ngày dịch:** {DateTime.Now:yyyy-MM-dd HH:mm}");
            sb.AppendLine($"**Số chunk đã dịch:** {translatedResults.Count}");
            sb.AppendLine();
            sb.AppendLine("---");
            sb.AppendLine();
            sb.AppendLine($"## {chosenChapter}");
            sb.AppendLine();

            // Gom source + vi (cho trường hợp sách Trung) hoặc chỉ vi
            bool isFirst = true;
            foreach (var (_, translated, _, _, _) in translatedResults.OrderBy(x => x.chunkId))
            {
                if (!isFirst) sb.AppendLine();
                sb.AppendLine(translated.Trim());
                isFirst = false;
            }

            File.WriteAllText(previewPath, sb.ToString(), new System.Text.UTF8Encoding(false));
            LastSampleMdPath = previewPath;
            AppendLog($"✅ Đã lưu preview mẫu: {previewPath}");

            // Nếu có bản gốc → lưu kèm file song ngữ / tam ngữ
            if (translatedResults.Any(r => r.isTrilingual))
            {
                // Tìm raw.md để lấy pinyin
                var pinyinMap = TryLoadPinyinForSample(book.Slug, translatedResults);
                var trilingualPath = Path.Combine(previewDir, $"{book.Slug}-sample-{safeChapter}-trilingual.md");
                var tsb = new System.Text.StringBuilder();
                tsb.AppendLine($"# 📖 {book.DisplayTitle} (Tam ngữ: Gốc + Pinyin + Việt)");
                tsb.AppendLine();
                tsb.AppendLine($"**Chương mẫu:** {chosenChapter}");
                tsb.AppendLine();
                tsb.AppendLine("---");
                tsb.AppendLine();
                foreach (var (cid, trans, orig, pin, _) in translatedResults.OrderBy(x => x.chunkId))
                {
                    var pinyin = pinyinMap.GetValueOrDefault(cid, pin);
                    var origLines = (orig ?? "").Split('\n').Select(l => l.TrimEnd()).Where(l => !string.IsNullOrWhiteSpace(l)).ToList();
                    var pinyinLines = (pinyin ?? "").Split('\n').Select(l => l.TrimEnd()).Where(l => !string.IsNullOrWhiteSpace(l)).ToList();
                    var viLines = (trans ?? "").Split('\n').Select(l => l.TrimEnd()).Where(l => !string.IsNullOrWhiteSpace(l)).ToList();
                    int maxLines = Math.Max(origLines.Count, Math.Max(pinyinLines.Count, viLines.Count));
                    for (int j = 0; j < maxLines; j++)
                    {
                        var o = j < origLines.Count ? origLines[j] : "";
                        var p = j < pinyinLines.Count ? pinyinLines[j] : "";
                        var v = j < viLines.Count ? viLines[j] : "";
                        if (!string.IsNullOrWhiteSpace(o)) tsb.AppendLine(o);
                        if (!string.IsNullOrWhiteSpace(p)) tsb.AppendLine($"*{p}*");
                        if (!string.IsNullOrWhiteSpace(v)) tsb.AppendLine(v);
                        tsb.AppendLine();
                    }
                }
                File.WriteAllText(trilingualPath, tsb.ToString(), new System.Text.UTF8Encoding(false));
                AppendLog($"✅ Đã lưu preview tam ngữ: {trilingualPath}");

                // Mở preview với dữ liệu tam ngữ
                await OpenMdPreviewAsync(previewPath, book, trilingualPath, translatedResults, pinyinMap);
            }
            else
            {
                // Sách EN: chỉ bản Việt
                await OpenMdPreviewAsync(previewPath, book, null, translatedResults, new Dictionary<int, string>());
            }
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy dịch mẫu: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            IsSampleBusy = false;
            BusyMessage = "";
            _currentCts = null;
        }
    }

    private static string SanitizeFileName(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return "sample";
        foreach (var c in Path.GetInvalidFileNameChars())
            name = name.Replace(c, '_');
        // Giới hạn độ dài
        if (name.Length > 50) name = name.Substring(0, 50);
        return name;
    }

    /// <summary>Đọc working/progress/<slug>/chunk_NNN.json để lấy pinyin_text (nếu có).</summary>
    private Dictionary<int, string> TryLoadPinyinForSample(string slug,
        List<(int chunkId, string translated, string originalText, string pinyinText, bool isTrilingual)> results)
    {
        var map = new Dictionary<int, string>();
        var progressDir = Path.Combine(_projectRoot, "working", "progress", slug);
        if (!Directory.Exists(progressDir)) return map;

        foreach (var (cid, _, _, _, _) in results)
        {
            var pf = Path.Combine(progressDir, $"chunk_{cid:000}.json");
            if (!File.Exists(pf)) continue;
            try
            {
                var json = File.ReadAllText(pf);
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("pinyin_text", out var pin))
                    map[cid] = pin.GetString() ?? "";
            }
            catch { }
        }
        return map;
    }

    private async Task OpenMdPreviewAsync(string viPreviewPath, BookStatus book, string? trilingualPath,
        List<(int chunkId, string translated, string originalText, string pinyinText, bool isTrilingual)> results,
        Dictionary<int, string> pinyinMap)
    {
        var app = Application.Current;
        if (app == null)
        {
            AppendLog("[Lỗi] Application.Current == null, không thể mở preview.", "error");
            return;
        }
        await app.Dispatcher.InvokeAsync(() =>
        {
            try
            {
                // Ưu tiên file tam ngữ nếu có (đẹp hơn, có cả gốc + pinyin + vi)
                var mainPath = trilingualPath ?? viPreviewPath;
                var window = new MdPreviewWindow(mainPath, book.DisplayTitle, book.Slug);
                if (app.MainWindow != null) window.Owner = app.MainWindow;

                // Truyền dữ liệu gốc/pinyin để toggle được các mode
                var srcCombined = string.Join("\n\n",
                    results.OrderBy(x => x.chunkId)
                           .Select(x => x.originalText ?? ""));
                var pinCombined = string.Join("\n\n",
                    pinyinMap.OrderBy(x => x.Key)
                             .Select(x => x.Value));
                window.SetSourceContent(srcCombined, pinCombined);

                window.Show();
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Không thể mở cửa sổ preview: {ex.Message}", "error");
            }
        });
    }

    [RelayCommand]
    private void OpenLastSamplePreview()
    {
        if (string.IsNullOrEmpty(LastSampleMdPath) || !File.Exists(LastSampleMdPath))
        {
            AppendLog("[Lỗi] Chưa có file preview mẫu nào.", "error");
            return;
        }
        var app = Application.Current;
        if (app == null) return;
        app.Dispatcher.InvokeAsync(() =>
        {
            try
            {
                var window = new MdPreviewWindow(LastSampleMdPath, SelectedBook?.DisplayTitle ?? "Preview", SelectedBook?.Slug ?? "");
                if (app.MainWindow != null) window.Owner = app.MainWindow;
                window.Show();
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Mở preview: {ex.Message}", "error");
            }
        });
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
        IsVoiceBusy = true;
        BusyMessage = $"Đang tạo audio: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Bắt đầu tạo audio: {book.Slug} (GPU={AudioUseGpu}, batch={AudioBatchSize}, music={AudioMusicAuto} v={AudioMusicVolume:0.00}, nhiệt độ={AudioTemperature}, top_k={AudioTopK}, bitrate={AudioBitrate})");
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
                book.ChapterInput,
                AudioUseGpu,
                AudioBatchSize,
                AudioMusicAuto,
                AudioMusicVolume,
                isSample: false,
                sampleChars: 400,
                ct: ct);
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
            IsVoiceBusy = false;
            BusyMessage = "";
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    [RelayCommand]
    private async Task GenerateSampleAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        book.IsBusy = true;
        IsVoiceBusy = true;
        BusyMessage = $"Đang tạo mẫu audio: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"Bắt đầu tạo audio mẫu (~30s test): {book.Slug} (GPU={AudioUseGpu}, music={AudioMusicAuto})");
        try
        {
            var ok = await _pipeline.RunAudiobookAsync(
                book.Slug,
                AudioTemperature.ToString("0.0"),
                AudioTopK.ToString(),
                AudioBitrate,
                AudioReadTitles,
                false,
                true,
                "",
                AudioUseGpu,
                AudioBatchSize,
                AudioMusicAuto,
                AudioMusicVolume,
                isSample: true,
                sampleChars: 400,
                ct: ct);

            if (ok)
            {
                AppendLog($"Tạo audio mẫu hoàn tất: {book.Slug}");
                var samplePath = Path.Combine(_projectRoot, "output", "samples", $"{book.Slug}-sample.wav");
                if (File.Exists(samplePath))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = samplePath,
                        UseShellExecute = true,
                    });
                }
            }
            else
            {
                AppendLog($"[Lỗi] Tạo audio mẫu thất bại: {book.Slug}", "error");
            }
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy bỏ tạo audio mẫu: {book.Slug}");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            IsVoiceBusy = false;
            BusyMessage = "";
            _currentCts = null;
        }
    }

    [RelayCommand]
    private void OpenAudioFolder(BookStatus? book)
    {
        if (book == null) return;
        var baseDir = !string.IsNullOrEmpty(book.FolderPath) && Directory.Exists(book.FolderPath)
            ? book.FolderPath
            : Path.Combine(_projectRoot, "output", "books", book.Title);

        var audioDir = Path.Combine(baseDir, "audiobook");
        if (!Directory.Exists(audioDir))
            audioDir = baseDir;

        if (Directory.Exists(audioDir))
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = audioDir,
                UseShellExecute = true,
            });
        }
        else
        {
            AppendLog($"[Lỗi] Thư mục audiobook chưa tồn tại: {audioDir}", "warning");
        }
    }

    private async void RefreshBookProgress()
    {
        var outputBooksList = OutputBooks.ToList();
        var root = _projectRoot;
        if (string.IsNullOrEmpty(root)) return;

        // Run heavy Disk I/O on background thread to prevent UI freezing/lagging
        var updates = await Task.Run(() =>
        {
            var results = new List<(BookStatus book, int progress)>();
            foreach (var book in outputBooksList)
            {
                var progressDir = Path.Combine(root, "working", "progress", book.Slug);
                if (!Directory.Exists(progressDir)) continue;

                var translated = 0;
                try
                {
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
                }
                catch { }

                if (translated != book.ProgressCount)
                {
                    results.Add((book, translated));
                }
            }
            return results;
        });

        foreach (var (book, progress) in updates)
        {
            book.ProgressCount = progress;
        }

        // Check if any output book has a QA report
        if (!HasQaReport)
        {
            foreach (var book in outputBooksList)
            {
                var reportPath = Path.Combine(root, "working", "qa", $"{book.Slug}_report.md");
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
        // Thư mục output đặt theo tên gốc (Title); nếu là input thì tìm theo slug
        var bookDir = string.IsNullOrEmpty(book.Title)
            ? Path.Combine(_projectRoot, "output", "books", book.Slug)
            : Path.Combine(_projectRoot, "output", "books", book.Title);
        if (!Directory.Exists(bookDir))
            bookDir = Path.Combine(_projectRoot, "output", "books", book.Slug);
        var updated = GetBookStatus(_projectRoot, bookDir, Path.GetFileName(bookDir), book.Source);
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
    /// 1. <tên sách input>.epub (từ metadata.json source_file — file trilingual gốc)
    /// 2. final/vi.epub (EN books, Vietnamese-only file)
    /// 3. any other *.epub under the book folder
    /// Returns null when no EPUB exists for the book.
    /// </summary>
    private static string? FindPreviewEpub(string bookDir)
    {
        // 1. Tên EPUB theo tên sách input (từ metadata.json)
        var metaPath = Path.Combine(bookDir, "metadata.json");
        if (File.Exists(metaPath))
        {
            try
            {
                var meta = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(metaPath));
                if (meta != null && meta.TryGetValue("source_file", out var src) && !string.IsNullOrEmpty(src))
                {
                    var epubName = Path.GetFileNameWithoutExtension(src) + ".epub";
                    var named = Path.Combine(bookDir, epubName);
                    if (File.Exists(named)) return named;
                }
            }
            catch { /* fallback tiếp */ }
        }

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

    private static BookStatus GetBookStatus(string projectRoot, string bookDir, string displayTitle, string source)
    {
        // slug gốc: từ metadata.json (thư mục đặt tên theo tên sách gốc)
        var slug = displayTitle;
        var metaPath = Path.Combine(bookDir, "metadata.json");
        if (File.Exists(metaPath))
        {
            try
            {
                var meta = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(metaPath));
                if (meta != null && meta.TryGetValue("slug", out var s) && !string.IsNullOrEmpty(s))
                    slug = s;
            }
            catch { /* fallback tên thư mục */ }
        }

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

        var cover = FindCoverImage(bookDir);

        return new BookStatus
        {
            Slug = slug,
            Title = displayTitle,
            Source = source,
            FolderPath = bookDir,
            HasViMd = File.Exists(viMd),
            HasEpub = File.Exists(epub),
            Mp3Count = mp3Count,
            TotalChapters = totalChapters,
            ProgressCount = progressCount,
            TotalChunks = totalChunks,
            CoverPath = cover,
            AudioDone = mp3Count,
            AudioTotal = totalChapters,
        };
    }

    /// <summary>
    /// Finds a cover image for a book: prefers an image named like a cover,
    /// otherwise the first image under the book's images/ folder. Returns "" if none.
    /// </summary>
    private static string FindCoverImage(string bookDir)
    {
        var imagesDir = Path.Combine(bookDir, "images");
        if (!Directory.Exists(imagesDir)) return "";

        var candidates = Directory.GetFiles(imagesDir, "*.jpg")
            .Concat(Directory.GetFiles(imagesDir, "*.png"))
            .Concat(Directory.GetFiles(imagesDir, "*.jpeg"))
            .OrderBy(p => p) // stable
            .ToList();
        if (candidates.Count == 0) return "";

        // Prefer a filename that suggests a cover (front/cover/0/1 often the cover).
        var coverish = candidates.FirstOrDefault(p =>
        {
            var name = Path.GetFileNameWithoutExtension(p).ToLowerInvariant();
            return name.Contains("cover") || name.Contains("front") || name == "0" || name == "1" || name.StartsWith("cover");
        });
        return coverish ?? candidates[0];
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

            AvailableModels.Clear();
            if (SelectedProvider == "gemini")
            {
                AvailableModels.Add("gemini-3.6-flash");
                AvailableModels.Add("gemini-2.5-pro");
                AvailableModels.Add("gemini-2.0-flash");
            }
            else if (SelectedProvider == "deepseek")
            {
                AvailableModels.Add("deepseek-chat");
                AvailableModels.Add("deepseek-reasoner");
            }
            else
            {
                AvailableModels.Add("gpt-4o-mini");
                AvailableModels.Add("gpt-4o");
                AvailableModels.Add("claude-3-5-sonnet-20241022");
                AvailableModels.Add("qwen-plus");
            }

            if (string.IsNullOrWhiteSpace(ModelInput) && AvailableModels.Count > 0)
                ModelInput = AvailableModels[0];
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

    // ==================== PIPELINE COMMANDS (DỊCH TOÀN BỘ SÁCH QUA API) ====================

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
        BusyMessage = $"Đang chuẩn bị dịch: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"🚀 BẮT ĐẦU DỊCH TOÀN BỘ CUỐN SÁCH: {book.DisplayTitle} ({book.Slug})");
        try
        {
            // === BƯỚC 1: TRÍCH XUẤT (EXTRACT) ===
            var rawMdPath = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw.md");
            BusyMessage = $"[1/6] Đang trích xuất nội dung: {book.Slug}...";
            AppendLog($"[Bước 1/6] Trích xuất file gốc ({Path.GetFileName(book.FilePath)})...");
            var okExtract = await _pipeline.RunExtractAsync(book.FilePath, book.Slug, string.IsNullOrWhiteSpace(book.PipelineLang) ? "auto" : book.PipelineLang, ct);
            if (!okExtract || !File.Exists(rawMdPath))
            {
                AppendLog($"[Lỗi] Trích xuất nội dung thất bại: {book.FilePath}", "error");
                return;
            }
            AppendLog("  ✅ Trích xuất nội dung hoàn tất.");

            // === BƯỚC 2: CHIA CHUNK (SMART CHUNKING) ===
            var chunksDir = Path.Combine(_projectRoot, "working", "chunks", book.Slug);
            BusyMessage = $"[2/6] Đang chia chunk: {book.Slug}...";
            AppendLog($"[Bước 2/6] Phân đoạn văn bản (Chunking)...");
            var okChunk = await _pipeline.RunChunkAsync(rawMdPath, chunksDir, ct);
            if (!okChunk)
            {
                AppendLog($"[Lỗi] Chia chunk thất bại: {rawMdPath}", "error");
                return;
            }
            AppendLog("  ✅ Phân đoạn văn bản hoàn tất.");

            // === BƯỚC 3: KHỞI TẠO SKELETON PROGRESS ===
            var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
            BusyMessage = $"[3/6] Đang tạo khung dịch (Skeleton)...";
            AppendLog($"[Bước 3/6] Khởi tạo khung tiến trình (Skeleton progress)...");
            await _pipeline.RunSkeletonAsync(chunksDir, progressDir, ct);
            AppendLog("  ✅ Tạo khung dịch hoàn tất.");

            // === BƯỚC 4: NẠP GLOSSARY MASTER & HỒ SƠ VĂN CHƯƠNG (BOOK PROFILE) ===
            var glossary = ApiTranslationService.LoadGlossary(book.Slug, _projectRoot);
            if (!string.IsNullOrWhiteSpace(glossary))
            {
                AppendLog($"[Bước 4/6] Đã nạp thuật ngữ từ glossary/master.csv ({glossary.Split('\n').Length} mục)");
            }

            var profilePath = Path.Combine(_projectRoot, "working", "profile", $"{book.Slug}.md");
            string bookProfile = "";
            try
            {
                if (!File.Exists(profilePath))
                {
                    await _pipeline.RunBookProfileAsync(chunksDir, progressDir, ct);
                }
                if (File.Exists(profilePath))
                {
                    bookProfile = await File.ReadAllTextAsync(profilePath, ct);
                    AppendLog($"[Bước 4/6] Đã nạp hồ sơ văn chương (Book Profile) cho {book.Slug}");
                }
            }
            catch { }

            // === BƯỚC 5: VÒNG LẶP DỊCH TỰ ĐỘNG TỪNG CHUNK QUA API ===
            var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(f => f).ToArray();
            book.TotalChunks = chunkFiles.Length;
            AppendLog($"[Bước 5/6] Bắt đầu dịch tự động {chunkFiles.Length} chunk qua API ({ActiveProvider})...");

            int successCount = 0;
            for (int i = 0; i < chunkFiles.Length; i++)
            {
                ct.ThrowIfCancellationRequested();
                var chunkFile = chunkFiles[i];

                int chunkId = i;
                string text = "";
                string chapter = "";
                try
                {
                    var json = await File.ReadAllTextAsync(chunkFile, ct);
                    using var doc = JsonDocument.Parse(json);
                    var c = doc.RootElement;
                    chunkId = c.TryGetProperty("chunk_id", out var cid) ? cid.GetInt32() : i;
                    text = c.TryGetProperty("text", out var tp) ? tp.GetString() ?? "" : "";
                    chapter = c.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : "";
                }
                catch { }

                var progChunkFile = Path.Combine(progressDir, $"chunk_{chunkId:D3}.json");
                string origText = text;
                string pinyinText = "";
                string existingTrans = "";
                bool isTrilingual = ContainsChinese(text);

                Dictionary<string, object> progObj = new();
                if (File.Exists(progChunkFile))
                {
                    try
                    {
                        using var pdoc = JsonDocument.Parse(File.ReadAllText(progChunkFile));
                        foreach (var prop in pdoc.RootElement.EnumerateObject())
                        {
                            if (prop.Value.ValueKind == JsonValueKind.String)
                                progObj[prop.Name] = prop.Value.GetString()!;
                            else if (prop.Value.ValueKind == JsonValueKind.Number)
                                progObj[prop.Name] = prop.Value.GetInt32();
                            else if (prop.Value.ValueKind == JsonValueKind.True || prop.Value.ValueKind == JsonValueKind.False)
                                progObj[prop.Name] = prop.Value.GetBoolean();
                        }

                        if (progObj.TryGetValue("original_text", out var ot) && !string.IsNullOrWhiteSpace(ot?.ToString()))
                            origText = ot.ToString()!;
                        if (progObj.TryGetValue("pinyin_text", out var pt) && !string.IsNullOrWhiteSpace(pt?.ToString()))
                            pinyinText = pt.ToString()!;
                    }
                    catch { }
                }

                if (string.IsNullOrWhiteSpace(origText))
                {
                    continue;
                }

                // Lấy ngữ cảnh chunk trước (prev) để giữ mạch văn nhất quán giống Agent
                var contextSb = new System.Text.StringBuilder();
                if (!string.IsNullOrWhiteSpace(bookProfile))
                {
                    contextSb.AppendLine("### HỒ SƠ VĂN CHƯƠNG CUỐN SÁCH (BẮT BUỘC BÁM SÁT):");
                    contextSb.AppendLine(bookProfile);
                    contextSb.AppendLine();
                }

                BusyMessage = $"Đang dịch: [{i + 1}/{chunkFiles.Length}] ({book.Slug})...";
                AppendLog($"  → [{i + 1}/{chunkFiles.Length}] Dịch chunk {chunkId} ({chapter})...");

                var sourceLang = isTrilingual ? "Chinese" : "English";
                var result = await _apiService.TranslateAsync(
                    origText, ActiveProvider, glossary,
                    context: contextSb.ToString(),
                    sourceLang: sourceLang, targetLang: "Vietnamese",
                    trilingual: isTrilingual,
                    onStatusLog: msg => AppendLog(msg, "warning"),
                    ct: ct);

                if (string.IsNullOrWhiteSpace(result.Text))
                {
                    AppendLog($"    [Cảnh báo] Chunk {chunkId} dịch trả về rỗng, thử lại lần sau.", "warning");
                    continue;
                }

                // Cập nhật kết quả dịch vào progress JSON giữ nguyên pinyin_text và original_text
                progObj["chunk_id"] = chunkId;
                progObj["total_chunks"] = chunkFiles.Length;
                progObj["chapter"] = chapter;
                progObj["source_text"] = origText;
                progObj["original_text"] = origText;
                progObj["pinyin_text"] = pinyinText;
                progObj["translated_text"] = result.Text.Trim();
                progObj["word_count_source"] = origText.Length;
                progObj["word_count_translated"] = result.Text.Length;
                progObj["mode"] = isTrilingual ? "trilingual" : "bilingual";
                progObj["translated_at"] = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss");

                // Lưu file progress JSON
                var saveJson = JsonSerializer.Serialize(progObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
                await File.WriteAllTextAsync(progChunkFile, saveJson, new System.Text.UTF8Encoding(false), ct);

                // QA nhanh cho chunk vừa dịch theo chuẩn /dich (Bước G.4)
                await _pipeline.RunBatchQaAsync(progressDir, chunkId, ct);

                successCount++;
                book.ProgressCount = successCount;
                AppendLog($"    ✅ Chunk {chunkId} dịch xong ({result.Text.Length} ký tự)");
            }

            AppendLog($"  🎉 Dịch hoàn tất {successCount}/{chunkFiles.Length} chunks!");

            // === BƯỚC 6: MERGE CHUNKS & MAKE EPUB ===
            BusyMessage = $"[6/6] Đang gộp file và tạo EPUB: {book.Slug}...";
            AppendLog("[Bước 6/6] Gộp các bản dịch và tạo sách điện tử (EPUB)...");

            var outputBookDir = Path.Combine(_projectRoot, "output", "books", book.Title);
            var finalDir = Path.Combine(outputBookDir, "final");
            Directory.CreateDirectory(finalDir);

            // Gộp bản dịch tam ngữ và bản dịch thuần Việt
            var isChineseBook = ContainsChinese(File.Exists(rawMdPath) ? File.ReadAllText(rawMdPath) : book.Slug);
            if (isChineseBook)
            {
                await _pipeline.RunMergeAsync(book.Slug, "trilingual", outputDir: finalDir, force: true, ct: ct);
                // Đổi tên file sau merge sang chuẩn tamngu.md
                var rawTrilingual = Path.Combine(finalDir, $"{book.Slug}_trilingual.md");
                var destTamNgu = Path.Combine(finalDir, "tamngu.md");
                if (File.Exists(rawTrilingual))
                {
                    if (File.Exists(destTamNgu)) File.Delete(destTamNgu);
                    File.Move(rawTrilingual, destTamNgu);
                }

                await _pipeline.RunMergeAsync(book.Slug, "bilingual", outputDir: finalDir, force: true, ct: ct);
                var rawVi = Path.Combine(finalDir, $"{book.Slug}_translated.md");
                var destVi = Path.Combine(finalDir, "vi.md");
                if (File.Exists(rawVi))
                {
                    if (File.Exists(destVi)) File.Delete(destVi);
                    File.Move(rawVi, destVi);
                }

                // Gộp câu nối dòng OCR và dọn số trang rác theo chuẩn /dich (mục I)
                if (File.Exists(destTamNgu)) await _pipeline.RunMergeSentencesAsync(destTamNgu, ct);
                if (File.Exists(destVi)) await _pipeline.RunMergeSentencesAsync(destVi, ct);
            }
            else
            {
                await _pipeline.RunMergeAsync(book.Slug, "bilingual", outputDir: finalDir, force: true, ct: ct);
                var rawVi = Path.Combine(finalDir, $"{book.Slug}_translated.md");
                var destVi = Path.Combine(finalDir, "vi.md");
                if (File.Exists(rawVi))
                {
                    if (File.Exists(destVi)) File.Delete(destVi);
                    File.Move(rawVi, destVi);
                }

                if (File.Exists(destVi)) await _pipeline.RunMergeSentencesAsync(destVi, ct);
            }

            // Tạo metadata.json đầy đủ theo checklist bắt buộc của /dich
            var metaFile = Path.Combine(outputBookDir, "metadata.json");
            var metaObj = new Dictionary<string, object>
            {
                ["slug"] = book.Slug,
                ["title"] = book.Title,
                ["source_file"] = Path.GetFileName(book.FilePath),
                ["author"] = book.EpubAuthor ?? "",
                ["language"] = isChineseBook ? "zh" : "en",
                ["genre"] = "",
                ["has_audio"] = false,
                ["has_epub"] = true,
                ["epub_file"] = $"{book.Title}.epub",
                ["created"] = DateTime.Now.ToString("yyyy-MM-dd")
            };
            await File.WriteAllTextAsync(metaFile, JsonSerializer.Serialize(metaObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }), ct);

            // Copy ảnh từ working/extracted/<slug> sang output/books/<title>/images và final/images
            try
            {
                var targetImagesDir = Path.Combine(outputBookDir, "images");
                var finalImagesDir = Path.Combine(finalDir, "images");
                Directory.CreateDirectory(targetImagesDir);
                Directory.CreateDirectory(finalImagesDir);

                var extractedBase = Path.Combine(_projectRoot, "working", "extracted", book.Slug);
                if (Directory.Exists(extractedBase))
                {
                    var imgFiles = Directory.GetFiles(extractedBase, "*.*", SearchOption.AllDirectories)
                        .Where(f => f.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) ||
                                    f.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) ||
                                    f.EndsWith(".png", StringComparison.OrdinalIgnoreCase));
                    foreach (var img in imgFiles)
                    {
                        var destImg1 = Path.Combine(targetImagesDir, Path.GetFileName(img));
                        var destImg2 = Path.Combine(finalImagesDir, Path.GetFileName(img));
                        if (!File.Exists(destImg1)) File.Copy(img, destImg1, true);
                        if (!File.Exists(destImg2)) File.Copy(img, destImg2, true);
                    }
                }
            }
            catch { }

            // Tạo file EPUB thành phẩm
            var sourceMdForEpub = isChineseBook && File.Exists(Path.Combine(finalDir, "tamngu.md"))
                ? Path.Combine(finalDir, "tamngu.md")
                : Path.Combine(finalDir, "vi.md");

            if (File.Exists(sourceMdForEpub))
            {
                var resourcePath = $"{Path.Combine(outputBookDir, "images")};{Path.Combine(_projectRoot, "working", "extracted", book.Slug)}";
                await _pipeline.RunMakeEpubAsync(sourceMdForEpub, book.Title, book.EpubAuthor ?? "", resourcePath, ct);
                var generatedEpub = Path.ChangeExtension(sourceMdForEpub, ".epub");
                var targetEpub = Path.Combine(outputBookDir, $"{book.Title}.epub");
                if (File.Exists(generatedEpub))
                {
                    if (File.Exists(targetEpub)) File.Delete(targetEpub);
                    File.Move(generatedEpub, targetEpub);
                }
            }

            // Chuyển file nguồn sang input/da-dich/ theo checklist mục K của /dich
            try
            {
                var daDichDir = Path.Combine(_projectRoot, "input", "da-dich");
                Directory.CreateDirectory(daDichDir);
                var destInputFile = Path.Combine(daDichDir, Path.GetFileName(book.FilePath));
                if (File.Exists(book.FilePath) && book.FilePath != destInputFile)
                {
                    if (File.Exists(destInputFile)) File.Delete(destInputFile);
                    File.Move(book.FilePath, destInputFile);
                }
            }
            catch { }

            AppendLog($"✨ HOÀN TẤT TOÀN BỘ SÁCH: {book.DisplayTitle}!");
            AppendLog($"📂 Thư mục sản phẩm: {outputBookDir}");

            // Tự động load lại danh sách sách
            LoadBooks();
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy pipeline: {book.Slug}", "warning");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi Pipeline] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            IsPipelineBusy = false;
            BusyMessage = "";
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    [RelayCommand]
    private async Task RepairBookAsync(BookStatus book)
    {
        if (book == null || string.IsNullOrWhiteSpace(book.Slug)) return;
        if (IsPipelineBusy)
        {
            AppendLog("⚠️ Đang có tiến trình khác chạy, vui lòng đợi!", "warning");
            return;
        }

        // Tìm internal slug chuẩn từ metadata.json (nếu có)
        var actualSlug = book.Slug;
        var bookDir = Path.Combine(_projectRoot, "output", "books", book.Title);
        var metaPath = Path.Combine(bookDir, "metadata.json");
        if (File.Exists(metaPath))
        {
            try
            {
                using var mdoc = JsonDocument.Parse(File.ReadAllText(metaPath));
                if (mdoc.RootElement.TryGetProperty("slug", out var s) && !string.IsNullOrWhiteSpace(s.GetString()))
                {
                    actualSlug = s.GetString()!;
                }
            }
            catch { }
        }

        IsPipelineBusy = true;
        book.IsBusy = true;
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"🔧 BẮT ĐẦU RÀ SOÁT & SỬA CHỮA THÔNG MINH: {book.DisplayTitle} ({actualSlug})");
        try
        {
            // 1. Kiểm tra raw.md
            var rawMdPath = Path.Combine(_projectRoot, "working", "extracted", actualSlug, "raw.md");
            if (!File.Exists(rawMdPath) && File.Exists(book.FilePath))
            {
                BusyMessage = $"Trích xuất file gốc: {actualSlug}...";
                AppendLog($"[Rà soát] Trích xuất file gốc ({Path.GetFileName(book.FilePath)})...");
                await _pipeline.RunExtractAsync(book.FilePath, actualSlug, string.IsNullOrWhiteSpace(book.PipelineLang) ? "auto" : book.PipelineLang, ct);
            }

            // 2. Kiểm tra Chunks
            var chunksDir = Path.Combine(_projectRoot, "working", "chunks", actualSlug);
            if (!Directory.Exists(chunksDir) || Directory.GetFiles(chunksDir, "chunk-*.json").Length == 0)
            {
                BusyMessage = $"Phân đoạn chunk: {actualSlug}...";
                AppendLog($"[Rà soát] Chia chunk văn bản...");
                await _pipeline.RunChunkAsync(rawMdPath, chunksDir, ct);
            }

            // 3. Kiểm tra Skeleton
            var progressDir = Path.Combine(_projectRoot, "working", "progress", actualSlug);
            if (!Directory.Exists(progressDir) || Directory.GetFiles(progressDir, "chunk_*.json").Length == 0)
            {
                BusyMessage = $"Tạo khung dịch (Skeleton): {actualSlug}...";
                AppendLog($"[Rà soát] Tạo khung tiến trình (Skeleton)...");
                await _pipeline.RunSkeletonAsync(chunksDir, progressDir, ct);
            }

            // 4. Nạp Glossary Master & Book Profile
            var glossary = ApiTranslationService.LoadGlossary(actualSlug, _projectRoot);
            var profilePath = Path.Combine(_projectRoot, "working", "profile", $"{actualSlug}.md");
            string bookProfile = "";
            if (File.Exists(profilePath))
            {
                try { bookProfile = await File.ReadAllTextAsync(profilePath, ct); } catch { }
            }

            var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(f => f).ToArray();
            book.TotalChunks = chunkFiles.Length;

            // 0. Tự động dọn dẹp các chunk thừa / chunk rác vượt quá total_chunks chuẩn
            try
            {
                var existingProgFiles = Directory.GetFiles(progressDir, "chunk_*.json");
                int cleanedPhantom = 0;
                foreach (var pf in existingProgFiles)
                {
                    var fn = Path.GetFileNameWithoutExtension(pf); // chunk_055
                    if (fn.StartsWith("chunk_") && int.TryParse(fn.Substring(6), out int cid))
                    {
                        if (cid >= chunkFiles.Length)
                        {
                            File.Delete(pf);
                            cleanedPhantom++;
                        }
                    }
                }
                if (cleanedPhantom > 0)
                {
                    AppendLog($"  🧹 Đã dọn dẹp {cleanedPhantom} chunk rác/thừa không thuộc sách.");
                }
            }
            catch { }

            AppendLog($"🔍 Đang quét và kiểm tra chất lượng đa tầng ({chunkFiles.Length} chunks)...");

            int repairedCount = 0;
            int validCount = 0;
            int offlineFixedCount = 0;

            for (int i = 0; i < chunkFiles.Length; i++)
            {
                ct.ThrowIfCancellationRequested();
                var chunkFile = chunkFiles[i];

                int chunkId = i;
                string text = "";
                string chapter = "";
                try
                {
                    var json = await File.ReadAllTextAsync(chunkFile, ct);
                    using var doc = JsonDocument.Parse(json);
                    var c = doc.RootElement;
                    chunkId = c.TryGetProperty("chunk_id", out var cid) ? cid.GetInt32() : i;
                    text = c.TryGetProperty("text", out var tp) ? tp.GetString() ?? "" : "";
                    chapter = c.TryGetProperty("chapter", out var ch) ? ch.GetString() ?? "" : "";
                }
                catch { }

                var progChunkFile = Path.Combine(progressDir, $"chunk_{chunkId:D3}.json");
                string origText = text;
                string pinyinText = "";
                string currentTrans = "";
                bool isTrilingual = ContainsChinese(text);

                Dictionary<string, object> progObj = new();
                if (File.Exists(progChunkFile))
                {
                    try
                    {
                        using var pdoc = JsonDocument.Parse(File.ReadAllText(progChunkFile));
                        foreach (var prop in pdoc.RootElement.EnumerateObject())
                        {
                            if (prop.Value.ValueKind == JsonValueKind.String)
                                progObj[prop.Name] = prop.Value.GetString()!;
                            else if (prop.Value.ValueKind == JsonValueKind.Number)
                                progObj[prop.Name] = prop.Value.GetInt32();
                            else if (prop.Value.ValueKind == JsonValueKind.True || prop.Value.ValueKind == JsonValueKind.False)
                                progObj[prop.Name] = prop.Value.GetBoolean();
                        }

                        if (progObj.TryGetValue("original_text", out var ot) && !string.IsNullOrWhiteSpace(ot?.ToString()))
                            origText = ot.ToString()!;
                        if (progObj.TryGetValue("pinyin_text", out var pt) && !string.IsNullOrWhiteSpace(pt?.ToString()))
                            pinyinText = pt.ToString()!;
                        if (progObj.TryGetValue("translated_text", out var tt) && !string.IsNullOrWhiteSpace(tt?.ToString()))
                            currentTrans = tt.ToString()!;
                    }
                    catch { }
                }

                // KIỂM TRA ĐA TẦNG THÔNG MINH
                bool needApiTranslate = false;
                bool modifiedOffline = false;

                if (string.IsNullOrWhiteSpace(currentTrans))
                {
                    needApiTranslate = true;
                    AppendLog($"  ⚠️ Chunk {chunkId}: Chưa có bản dịch -> Đang dịch mới...");
                }
                else
                {
                    // Tầng 1: Kiểm tra Mojibake / hỏng font dấu hỏi
                    bool hasMojibake = System.Text.RegularExpressions.Regex.IsMatch(currentTrans, @"[a-zA-ZÀ-ỹ]\?(?=[a-zA-ZÀ-ỹ])");
                    if (hasMojibake)
                    {
                        needApiTranslate = true;
                        AppendLog($"  ⚠️ Chunk {chunkId}: Phát hiện lỗi vỡ font/dấu hỏi (Mojibake) -> Cần dịch lại...");
                    }

                    // Tầng 2: Kiểm tra Hán sót và Lệch dòng
                    if (!needApiTranslate && isTrilingual)
                    {
                        var origLines = origText.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
                        var transLines = currentTrans.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);

                        int hanChars = currentTrans.Count(c => c >= 0x4E00 && c <= 0x9FFF);
                        double hanRatio = currentTrans.Length > 0 ? (double)hanChars / currentTrans.Length : 0;

                        if (hanRatio > 0.15 && currentTrans.Length > 50)
                        {
                            needApiTranslate = true;
                            AppendLog($"  ⚠️ Chunk {chunkId}: Sót chữ Hán cao ({hanRatio:P0}) -> Đang dịch lại...");
                        }
                        else if (origLines.Length != transLines.Length)
                        {
                            // Thử tự động sửa lỗi lệch dòng nhỏ nếu chỉ do khoảng trắng thừa ở cuối
                            if (origLines.Length > 0 && transLines.Length > origLines.Length && string.IsNullOrWhiteSpace(transLines.Last()))
                            {
                                currentTrans = string.Join("\n", transLines.Take(origLines.Length));
                                modifiedOffline = true;
                                offlineFixedCount++;
                            }
                            else
                            {
                                needApiTranslate = true;
                                AppendLog($"  ⚠️ Chunk {chunkId}: Lệch cấu trúc dòng ({transLines.Length}/{origLines.Length}) -> Đang dịch lại...");
                            }
                        }
                    }
                    // Tầng 3: Kiểm tra lặp dòng / ảo giác AI (AI Hallucination / Loops)
                    if (!needApiTranslate)
                    {
                        var transLinesForLoopCheck = currentTrans.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.RemoveEmptyEntries);
                        int repeatCount = 0;
                        for (int li = 1; li < transLinesForLoopCheck.Length; li++)
                        {
                            if (transLinesForLoopCheck[li].Length > 15 && transLinesForLoopCheck[li] == transLinesForLoopCheck[li - 1])
                            {
                                repeatCount++;
                            }
                        }
                        if (repeatCount >= 3)
                        {
                            needApiTranslate = true;
                            AppendLog($"  ⚠️ Chunk {chunkId}: Phát hiện lỗi lặp câu AI (AI Loop {repeatCount} lần) -> Đang dịch lại...");
                        }
                    }

                    // Tầng 4: Tự làm sạch ký tự rác OCR "///" nếu có
                    if (!needApiTranslate && currentTrans.Contains("///"))
                    {
                        currentTrans = currentTrans.Replace("///", "").Trim();
                        modifiedOffline = true;
                        offlineFixedCount++;
                    }
                }

                // Cập nhật total_chunks chuẩn trong file nếu bị lệch
                if (progObj.TryGetValue("total_chunks", out var tcVal) && Convert.ToInt32(tcVal) != chunkFiles.Length)
                {
                    progObj["total_chunks"] = chunkFiles.Length;
                    modifiedOffline = true;
                }

                if (needApiTranslate)
                {
                    BusyMessage = $"Đang sửa chunk: [{i + 1}/{chunkFiles.Length}] ({book.Slug})...";
                    AppendLog($"  🔄 Dịch sửa chunk {chunkId} ({chapter})...");

                    var contextSb = new System.Text.StringBuilder();
                    if (!string.IsNullOrWhiteSpace(bookProfile))
                    {
                        contextSb.AppendLine("### HỒ SƠ VĂN CHƯƠNG CUỐN SÁCH (BẮT BUỘC BÁM SÁT):");
                        contextSb.AppendLine(bookProfile);
                        contextSb.AppendLine();
                    }

                    var sourceLang = isTrilingual ? "Chinese" : "English";
                    var result = await _apiService.TranslateAsync(
                        origText, ActiveProvider, glossary,
                        context: contextSb.ToString(),
                        sourceLang: sourceLang, targetLang: "Vietnamese",
                        trilingual: isTrilingual,
                        onStatusLog: msg => AppendLog(msg, "warning"),
                        ct: ct);

                    if (!string.IsNullOrWhiteSpace(result.Text))
                    {
                        progObj["chunk_id"] = chunkId;
                        progObj["total_chunks"] = chunkFiles.Length;
                        progObj["chapter"] = chapter;
                        progObj["source_text"] = origText;
                        progObj["original_text"] = origText;
                        progObj["pinyin_text"] = pinyinText;
                        progObj["translated_text"] = result.Text.Trim();
                        progObj["word_count_source"] = origText.Length;
                        progObj["word_count_translated"] = result.Text.Length;
                        progObj["mode"] = isTrilingual ? "trilingual" : "bilingual";
                        progObj["translated_at"] = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss");

                        var saveJson = JsonSerializer.Serialize(progObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
                        await File.WriteAllTextAsync(progChunkFile, saveJson, new System.Text.UTF8Encoding(false), ct);
                        await _pipeline.RunBatchQaAsync(progressDir, chunkId, ct);
                        repairedCount++;
                        AppendLog($"    ✅ Đã sửa xong chunk {chunkId}");
                    }
                }
                else
                {
                    if (modifiedOffline)
                    {
                        progObj["translated_text"] = currentTrans;
                        var saveJson = JsonSerializer.Serialize(progObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
                        await File.WriteAllTextAsync(progChunkFile, saveJson, new System.Text.UTF8Encoding(false), ct);
                    }
                    validCount++;
                }

                book.ProgressCount = i + 1;
            }

            if (repairedCount == 0 && offlineFixedCount == 0)
            {
                AppendLog($"✨ [RÀ SOÁT HOÀN TẤT] Toàn bộ {validCount} chunk đều chuẩn xác 100%, không phát hiện lỗi nào!");
            }
            else
            {
                AppendLog($"✨ [SỬA CHỮA HOÀN TẤT] Đã sửa chữa thành công {repairedCount} chunk qua API, {offlineFixedCount} sửa nhanh offline, {validCount} chunk chuẩn được giữ nguyên.");
            }

            // 5. Gộp file & tạo lại EPUB hoàn chỉnh
            BusyMessage = $"Gộp file và cập nhật EPUB: {actualSlug}...";
            AppendLog("🔨 Đang gộp lại bản dịch và đóng gói EPUB...");

            var outputBookDir = Path.Combine(_projectRoot, "output", "books", book.Title);
            var finalDir = Path.Combine(outputBookDir, "final");
            Directory.CreateDirectory(finalDir);

            var isChineseBook = ContainsChinese(File.Exists(rawMdPath) ? File.ReadAllText(rawMdPath) : actualSlug);
            if (isChineseBook)
            {
                await _pipeline.RunMergeAsync(actualSlug, "trilingual", outputDir: finalDir, force: true, ct: ct);
                var rawTrilingual = Path.Combine(finalDir, $"{actualSlug}_trilingual.md");
                var destTamNgu = Path.Combine(finalDir, "tamngu.md");
                if (File.Exists(rawTrilingual))
                {
                    if (File.Exists(destTamNgu)) File.Delete(destTamNgu);
                    File.Move(rawTrilingual, destTamNgu);
                }

                await _pipeline.RunMergeAsync(actualSlug, "bilingual", outputDir: finalDir, force: true, ct: ct);
                var rawVi = Path.Combine(finalDir, $"{actualSlug}_translated.md");
                var destVi = Path.Combine(finalDir, "vi.md");
                if (File.Exists(rawVi))
                {
                    if (File.Exists(destVi)) File.Delete(destVi);
                    File.Move(rawVi, destVi);
                }

                if (File.Exists(destTamNgu)) await _pipeline.RunMergeSentencesAsync(destTamNgu, ct);
                if (File.Exists(destVi)) await _pipeline.RunMergeSentencesAsync(destVi, ct);
            }
            else
            {
                await _pipeline.RunMergeAsync(actualSlug, "bilingual", outputDir: finalDir, force: true, ct: ct);
                var rawVi = Path.Combine(finalDir, $"{actualSlug}_translated.md");
                var destVi = Path.Combine(finalDir, "vi.md");
                if (File.Exists(rawVi))
                {
                    if (File.Exists(destVi)) File.Delete(destVi);
                    File.Move(rawVi, destVi);
                }

                if (File.Exists(destVi)) await _pipeline.RunMergeSentencesAsync(destVi, ct);
            }

            // Tạo metadata.json
            var metaFile = Path.Combine(outputBookDir, "metadata.json");
            var metaObj = new Dictionary<string, object>
            {
                ["slug"] = actualSlug,
                ["title"] = book.Title,
                ["source_file"] = Path.GetFileName(book.FilePath),
                ["author"] = book.EpubAuthor ?? "",
                ["language"] = isChineseBook ? "zh" : "en",
                ["genre"] = "",
                ["has_audio"] = false,
                ["has_epub"] = true,
                ["epub_file"] = $"{book.Title}.epub",
                ["created"] = DateTime.Now.ToString("yyyy-MM-dd")
            };
            await File.WriteAllTextAsync(metaFile, JsonSerializer.Serialize(metaObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }), ct);

            // Copy ảnh từ working/extracted/<slug> sang output/books/<title>/images và final/images
            try
            {
                var targetImagesDir = Path.Combine(outputBookDir, "images");
                var finalImagesDir = Path.Combine(finalDir, "images");
                Directory.CreateDirectory(targetImagesDir);
                Directory.CreateDirectory(finalImagesDir);

                var extractedBase = Path.Combine(_projectRoot, "working", "extracted", actualSlug);
                if (Directory.Exists(extractedBase))
                {
                    var imgFiles = Directory.GetFiles(extractedBase, "*.*", SearchOption.AllDirectories)
                        .Where(f => f.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) ||
                                    f.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) ||
                                    f.EndsWith(".png", StringComparison.OrdinalIgnoreCase));
                    foreach (var img in imgFiles)
                    {
                        var destImg1 = Path.Combine(targetImagesDir, Path.GetFileName(img));
                        var destImg2 = Path.Combine(finalImagesDir, Path.GetFileName(img));
                        if (!File.Exists(destImg1)) File.Copy(img, destImg1, true);
                        if (!File.Exists(destImg2)) File.Copy(img, destImg2, true);
                    }
                }
            }
            catch { }

            // Tạo lại duy nhất 1 file EPUB chuẩn ở gốc thư mục (<Tên Sách>.epub) theo đúng quy chuẩn dự án
            var viMd = Path.Combine(finalDir, "vi.md");
            var tamNguMd = Path.Combine(finalDir, "tamngu.md");
            var sourceMdForEpub = isChineseBook && File.Exists(tamNguMd) ? tamNguMd : (File.Exists(viMd) ? viMd : tamNguMd);
            var resourcePath = $"{Path.Combine(outputBookDir, "images")};{Path.Combine(_projectRoot, "working", "extracted", actualSlug)}";

            if (File.Exists(sourceMdForEpub))
            {
                await _pipeline.RunMakeEpubAsync(sourceMdForEpub, book.Title, book.EpubAuthor ?? "", resourcePath, ct);
                var generatedEpub = Path.ChangeExtension(sourceMdForEpub, ".epub");
                var targetEpub = Path.Combine(outputBookDir, $"{book.Title}.epub");
                if (File.Exists(generatedEpub))
                {
                    if (File.Exists(targetEpub)) File.Delete(targetEpub);
                    File.Move(generatedEpub, targetEpub);
                }
            }

            AppendLog($"✨ HOÀN TẤT RÀ SOÁT & SỬA CHỮA THÀNH CÔNG: {book.DisplayTitle}!");
            LoadBooks();
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy sửa chữa: {book.Slug}", "warning");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi Sửa chữa] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            IsPipelineBusy = false;
            BusyMessage = "";
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
        BusyMessage = $"Đang trích xuất: {book.Slug}...";
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
            BusyMessage = "";
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
        BusyMessage = $"Đang tạo glossary: {book.Slug}...";
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
            BusyMessage = "";
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
            var ok = await _pipeline.RunMergeAsync(book.Slug, lang, outputDir: "", force: true, ct: ct);
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

        var title = string.IsNullOrWhiteSpace(book.EpubTitle) ? book.DisplayTitle : book.EpubTitle;
        AppendLog($"Bắt đầu tạo EPUB: {book.Slug} (title={title}, author={book.EpubAuthor})");
        try
        {
            var ok = await _pipeline.RunMakeEpubAsync(book.Slug, title, book.EpubAuthor ?? "", "", ct);
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
        BusyMessage = $"Đang chạy QA: {book.Slug}...";
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
            BusyMessage = "";
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
        FocusSearchRequested = true;
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

    [RelayCommand]
    private void ResetAudioConfig()
    {
        AudioUseGpu = true;
        AudioBatchSize = 16;
        AudioTemperature = 0.3;
        AudioTopK = 10;
        AudioMusicAuto = true;
        AudioMusicVolume = 0.15;
        AudioBitrate = "128k";
        AudioReadTitles = true;
        AudioMergeChapters = false;
        AudioForceRegenerate = false;
        AppendLog("Đã khôi phục toàn bộ Cấu hình Audiobook về chuẩn dự án (GPU RTX, Batch 16, Nhạc nền AI 15%, Temp 0.3, Top-K 10).");
    }
}
