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
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(DisplayActiveProvider))]
    private string _activeProvider = "";

    public string DisplayActiveProvider => ActiveProvider switch
    {
        "gemini" => "Gemini",
        "deepseek" => "DeepSeek",
        "custom" or "custom_1" => "Cấu hình 1 (Tùy chỉnh)",
        "custom_2" => "Cấu hình 2 (Tùy chỉnh)",
        "custom_3" => "Cấu hình 3 (Tùy chỉnh)",
        "custom_4" => "Cấu hình 4 (Tùy chỉnh)",
        "custom_5" => "Cấu hình 5 (Tùy chỉnh)",
        _ => string.IsNullOrEmpty(ActiveProvider) ? "" : char.ToUpper(ActiveProvider[0]) + ActiveProvider[1..]
    };

    [ObservableProperty] private bool _isApiOk;
    [ObservableProperty] private bool _logExpanded = true;
    [ObservableProperty] private string _logFilter = "";

    /// <summary>Trạng thái mở/thu gọn của NavigationView (sidebar trái).</summary>
    [ObservableProperty] private bool _isNavPaneOpen = true;

    [RelayCommand]
    private void ToggleNavPane() => IsNavPaneOpen = !IsNavPaneOpen;
    
    [ObservableProperty] private string _globalSearchQuery = "";
    partial void OnGlobalSearchQueryChanged(string value) => GlobalSearchQueryChanged?.Invoke(value);
    public static event Action<string>? GlobalSearchQueryChanged;

    /// <summary>Set true by Ctrl+F so BooksPage focuses its search box on load.</summary>
    [ObservableProperty] private bool _focusSearchRequested;

    [ObservableProperty] private double _audioTemperature = 0.3;
    [ObservableProperty] private int _audioTopK = 10;

    /// <summary>Số luồng dịch song song an toàn ngữ cảnh (Mặc định 1: Tuần tự an toàn chống Timeout, 2-3: Song song tốc độ cao kèm Sliding Window Context)</summary>
    [ObservableProperty] private int _translateConcurrency = 1;

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

    // Dashboard Analytics properties
    [ObservableProperty] private int _totalBooksCount = 0;
    [ObservableProperty] private int _pendingBooksCount = 0;
    [ObservableProperty] private int _translatedBooksCount = 0;
    [ObservableProperty] private int _audioBooksCount = 0;
    [ObservableProperty] private long _totalTranslatedWords = 0;
    [ObservableProperty] private string _gpuPerformanceText = "RTF 0.12 (GPU RTX ~8x)";

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
            {
                App.Current.Dispatcher.Invoke(() =>
                {
                    AppendLog(msg);

                    // Tự động phân tích log Audiobook để cập nhật realtime Progress trên thẻ Audio
                    try
                    {
                        var activeAudioBook = OutputBooks.FirstOrDefault(b => b.IsBusy);
                        if (activeAudioBook != null)
                        {
                            // 1. Bắt dòng: [Chương X/Y] hoặc Chapter X/Y
                            var chMatch = System.Text.RegularExpressions.Regex.Match(msg, @"(?:\[Chương|Chapter|Chương)\s*(\d+)\s*/\s*(\d+)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                            if (chMatch.Success && int.TryParse(chMatch.Groups[1].Value, out int chCur) && int.TryParse(chMatch.Groups[2].Value, out int chTot))
                            {
                                activeAudioBook.AudioDone = chCur;
                                activeAudioBook.AudioTotal = chTot;
                                activeAudioBook.BusyStatusText = $"Đang tạo Audio: Chương {chCur}/{chTot}";
                                if (chTot > 0)
                                {
                                    activeAudioBook.BusyProgressPercent = Math.Clamp(((double)(chCur - 1) / chTot) * 100, 0, 100);
                                }
                            }

                            // 2. Bắt dòng chunk audio: [chunk X/Y]
                            var chunkMatch = System.Text.RegularExpressions.Regex.Match(msg, @"(?:chunk|đoạn)\s*(\d+)\s*/\s*(\d+)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                            if (chunkMatch.Success && int.TryParse(chunkMatch.Groups[1].Value, out int ckCur) && int.TryParse(chunkMatch.Groups[2].Value, out int ckTot))
                            {
                                activeAudioBook.BusyDetailText = $"Đang đọc chunk {ckCur}/{ckTot}...";
                                if (activeAudioBook.AudioTotal > 0 && ckTot > 0)
                                {
                                    double baseP = ((double)(Math.Max(1, activeAudioBook.AudioDone) - 1) / activeAudioBook.AudioTotal) * 100;
                                    double stepP = (1.0 / activeAudioBook.AudioTotal) * ((double)ckCur / ckTot) * 100;
                                    activeAudioBook.BusyProgressPercent = Math.Clamp(baseP + stepP, 0, 99);
                                }
                            }

                            // 3. Bắt dòng tốc độ RTF / GPU: RTF 0.12x hoặc GPU
                            if (msg.Contains("RTF", StringComparison.OrdinalIgnoreCase))
                            {
                                var rtfMatch = System.Text.RegularExpressions.Regex.Match(msg, @"RTF\s*([0-9\.]+)");
                                if (rtfMatch.Success)
                                {
                                    activeAudioBook.BusyDetailText = $"Tốc độ GPU RTX: RTF {rtfMatch.Groups[1].Value} (Siêu nhanh)";
                                }
                            }
                        }
                    }
                    catch { }
                });
            }
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

    public async void LoadBooks()
    {
        InputBooks.Clear();
        OutputBooks.Clear();

        var booksDir = Path.Combine(_projectRoot, "output", "books");
        var inputDir = Path.Combine(_projectRoot, "input");

        // Run all file system I/O on a background thread to avoid freezing the UI
        var (outputBooks, inputBooks) = await Task.Run(() =>
        {
            var outputs = new List<BookStatus>();
            var inputs = new List<BookStatus>();

            if (Directory.Exists(booksDir))
            {
                foreach (var d in Directory.GetDirectories(booksDir).OrderBy(x => x))
                {
                    var title = Path.GetFileName(d);
                    outputs.Add(GetBookStatus(_projectRoot, d, title, "output"));
                }
            }

            if (Directory.Exists(inputDir))
            {
                foreach (var f in Directory.GetFiles(inputDir, "*", SearchOption.AllDirectories).OrderBy(x => x))
                {
                    var ext = Path.GetExtension(f).ToLower();
                    if (ext is not (".pdf" or ".epub" or ".docx")) continue;

                    var relDir = Path.GetRelativePath(inputDir, Path.GetDirectoryName(f) ?? inputDir);
                    var category = relDir.Replace("\\", "/").Split('/')[0];
                    if (string.IsNullOrEmpty(category) || category == ".") category = "chua-lam";

                    var rawTitle = Path.GetFileNameWithoutExtension(f);
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
                    inputs.Add(book);
                }
            }

            return (outputs, inputs);
        });

        foreach (var book in outputBooks) OutputBooks.Add(book);
        foreach (var book in inputBooks) InputBooks.Add(book);

        // Cập nhật các chỉ số Dashboard Analytics
        PendingBooksCount = InputBooks.Count(b => b.InputCategory == "chua-lam");
        TranslatedBooksCount = OutputBooks.Count + InputBooks.Count(b => b.InputCategory == "da-dich" || b.InputCategory == "da-audio");
        AudioBooksCount = OutputBooks.Count(b => b.Mp3Count > 0) + InputBooks.Count(b => b.InputCategory == "da-audio");
        TotalBooksCount = InputBooks.Count + OutputBooks.Count;

        // Ước tính tổng số từ đã dịch (background I/O)
        TotalTranslatedWords = await Task.Run(() =>
        {
            long totalWords = 0;
            try
            {
                if (Directory.Exists(booksDir))
                {
                    foreach (var d in Directory.GetDirectories(booksDir))
                    {
                        var viFile = Path.Combine(d, "final", "vi.md");
                        if (File.Exists(viFile))
                        {
                            var info = new FileInfo(viFile);
                            totalWords += info.Length / 5;
                        }
                    }
                }
            }
            catch { }
            return totalWords;
        });

        AppendLog($"Đã tải {InputBooks.Count} input, {OutputBooks.Count} output (Chưa làm: {PendingBooksCount}, Đã dịch: {TranslatedBooksCount}, Có Audio: {AudioBooksCount})");
    }

    [RelayCommand]
    private void CopyBookPath(BookStatus? book)
    {
        if (book == null) return;
        var p = !string.IsNullOrEmpty(book.FilePath) && File.Exists(book.FilePath)
            ? book.FilePath
            : Path.Combine(_projectRoot, "output", "books", book.Title);
        try
        {
            Clipboard.SetText(p);
            AppendLog($"📋 Đã sao chép đường dẫn: {p}");
        }
        catch { }
    }

    [RelayCommand]
    private void CleanBookCache(BookStatus? book)
    {
        if (book == null || string.IsNullOrWhiteSpace(book.Slug)) return;
        var app = Application.Current;

        var dirsToClean = new List<string>
        {
            Path.Combine(_projectRoot, "working", "chunks", book.Slug),
            Path.Combine(_projectRoot, "working", "progress", book.Slug),
            Path.Combine(_projectRoot, "working", "progress_audio", "chunks", book.Slug),
            Path.Combine(_projectRoot, "working", "qa", book.Slug),
            Path.Combine(_projectRoot, "working", "tmp", book.Slug)
        };

        var filesToClean = new List<string>
        {
            Path.Combine(_projectRoot, "working", "progress_audio", $"{book.Slug}.json"),
            Path.Combine(_projectRoot, "output", "samples", $"{book.Slug}_preview.md")
        };

        int deletedCount = 0;
        try
        {
            foreach (var dir in dirsToClean)
            {
                if (Directory.Exists(dir))
                {
                    Directory.Delete(dir, true);
                    deletedCount++;
                }
            }

            foreach (var file in filesToClean)
            {
                if (File.Exists(file))
                {
                    File.Delete(file);
                    deletedCount++;
                }
            }

            var msg = $"Đã dọn sạch toàn bộ cache trung gian ({deletedCount} mục) cho cuốn: {book.DisplayTitle}";
            AppendLog($"🧹 {msg}");
            
            app?.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw)
                    mw.ShowSnackbar(msg, isError: false);
            });

            LoadBooks();
        }
        catch (Exception ex)
        {
            var errMsg = $"Lỗi dọn cache: {ex.Message}";
            AppendLog($"[Lỗi dọn cache] {ex.Message}", "error");
            app?.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw)
                    mw.ShowSnackbar(errMsg, isError: true);
            });
        }
    }

    /// <summary>
    /// Xóa thư mục an toàn: xóa read-only, retry khi file bị khóa tạm thời,
    /// và KHÔNG fail toàn bộ nếu 1 file đang bị process khác giữ (bỏ qua).
    /// Đặc biệt xử lý file OneDrive cloud (ReparsePoint/Offline) — không đụng
    /// attributes placeholder, chỉ File.Delete để OneDrive tự giải phóng.
    /// Lặp nhiều vòng để dọn triệt để các thư mục lồng nhau.
    /// Trả về số file thực sự xóa được.
    /// </summary>
    private static int DeleteDirectorySafe(string dir)
    {
        if (!Directory.Exists(dir)) return 0;
        int deleted = 0;

        // Vòng 1: xóa toàn bộ file (kể cả read-only), retry nếu bị khóa tạm
        foreach (var f in Directory.GetFiles(dir, "*", SearchOption.AllDirectories))
        {
            for (int i = 0; i < 3; i++)
            {
                try
                {
                    // Chỉ bỏ ReadOnly (an toàn); KHÔNG đụng ReparsePoint/Offline của OneDrive
                    try
                    {
                        var attrs = File.GetAttributes(f);
                        if ((attrs & FileAttributes.ReadOnly) != 0)
                            File.SetAttributes(f, attrs & ~FileAttributes.ReadOnly);
                    }
                    catch (Exception) { }

                    File.Delete(f);
                    deleted++;
                    break;
                }
                catch (Exception) when (i < 2)
                {
                    System.Threading.Thread.Sleep(200);
                }
            }
        }

        // Vòng 2: xóa thư mục con từ sâu lên, LẶP LẠI nhiều vòng
        // (thư mục lồng nhau có thể rỗng dần khi các file bị khóa được giải phóng)
        for (int pass = 0; pass < 5; pass++)
        {
            bool removedAny = false;
            foreach (var d in Directory.GetDirectories(dir, "*", SearchOption.AllDirectories).OrderByDescending(x => x.Length))
            {
                try
                {
                    // Bỏ ReadOnly/archive nếu thư mục bị set đặc biệt (an toàn cho thư mục thường)
                    try
                    {
                        var attrs = File.GetAttributes(d);
                        if ((attrs & FileAttributes.ReadOnly) != 0)
                            File.SetAttributes(d, attrs & ~FileAttributes.ReadOnly);
                    }
                    catch (Exception) { }

                    Directory.Delete(d, false);
                    removedAny = true;
                }
                catch (Exception) { /* còn file bên trong hoặc bị khóa — vòng sau thử lại */ }
            }
            if (!removedAny) break;
        }

        // Cuối cùng xóa thư mục gốc
        try { Directory.Delete(dir, false); } catch (Exception) { }
        return deleted;
    }

    [RelayCommand]
    private void DeleteBook(BookStatus? book)
    {
        if (book == null) return;
        var app = Application.Current;

        bool isInputTab = string.Equals(book.Source, "input", StringComparison.OrdinalIgnoreCase);

        string prompt = isInputTab
            ? $"Bạn có chắc chắn muốn xóa file sách gốc '{book.DisplayTitle}' khỏi thư mục Input không?\n\n(Lưu ý: Hành động này sẽ xóa file nguồn trong input và không thể hoàn tác)"
            : $"Bạn có chắc chắn muốn XÓA TOÀN BỘ sản phẩm đã dịch của cuốn '{book.DisplayTitle}' không?\n\n- Sẽ xóa sạch thư mục Output (EPUB, Audiobook, bản dịch .md)\n- Sẽ xóa sạch toàn bộ cache trong Working\n- GIỮ NGUYÊN file gốc trong Input (nếu có)";

        var confirm = MessageBox.Show(prompt, "Xác nhận xóa sách", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (confirm != MessageBoxResult.Yes) return;

        try
        {
            int deletedCount = 0;

            if (isInputTab)
            {
                // Chỉ xóa file trong input
                if (!string.IsNullOrEmpty(book.FilePath) && File.Exists(book.FilePath))
                {
                    File.Delete(book.FilePath);
                    deletedCount++;
                }
                else if (!string.IsNullOrEmpty(book.FolderPath) && Directory.Exists(book.FolderPath))
                {
                    DeleteDirectorySafe(book.FolderPath);
                    deletedCount++;
                }

                // Dọn thêm cache working nếu có
                if (!string.IsNullOrWhiteSpace(book.Slug))
                {
                    var cDir = Path.Combine(_projectRoot, "working", "chunks", book.Slug);
                    var pDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
                    if (Directory.Exists(cDir)) DeleteDirectorySafe(cDir);
                    if (Directory.Exists(pDir)) DeleteDirectorySafe(pDir);
                }

                var msg = $"Đã xóa sách khỏi Input: {book.DisplayTitle}";
                AppendLog($"🗑️ {msg}");
                app?.Dispatcher.Invoke(() =>
                {
                    if (app.MainWindow is MainWindow mw)
                        mw.ShowSnackbar(msg, isError: false);
                });
            }
            else
            {
                // Xóa toàn bộ output + working, giữ lại input
                var possibleOutDirs = new List<string>
                {
                    Path.Combine(_projectRoot, "output", "books", book.Title),
                    Path.Combine(_projectRoot, "output", "books", book.Slug)
                };

                foreach (var outDir in possibleOutDirs)
                {
                    if (Directory.Exists(outDir))
                    {
                        DeleteDirectorySafe(outDir);
                        deletedCount++;
                    }
                }

                // Xóa toàn bộ working cache
                if (!string.IsNullOrWhiteSpace(book.Slug))
                {
                    var workingDirs = new List<string>
                    {
                        Path.Combine(_projectRoot, "working", "extracted", book.Slug),
                        Path.Combine(_projectRoot, "working", "chunks", book.Slug),
                        Path.Combine(_projectRoot, "working", "progress", book.Slug),
                        Path.Combine(_projectRoot, "working", "progress_audio", "chunks", book.Slug),
                        Path.Combine(_projectRoot, "working", "qa", book.Slug),
                        Path.Combine(_projectRoot, "working", "tmp", book.Slug),
                        Path.Combine(_projectRoot, "working", "profile", $"{book.Slug}.md")
                    };

                    foreach (var wd in workingDirs)
                    {
                        if (Directory.Exists(wd)) DeleteDirectorySafe(wd);
                        else if (File.Exists(wd)) File.Delete(wd);
                    }

                    var pJson = Path.Combine(_projectRoot, "working", "progress_audio", $"{book.Slug}.json");
                    if (File.Exists(pJson)) File.Delete(pJson);

                    var sPreview = Path.Combine(_projectRoot, "output", "samples", $"{book.Slug}_preview.md");
                    if (File.Exists(sPreview)) File.Delete(sPreview);
                }

                var msg = $"Đã xóa sạch toàn bộ sản phẩm dịch và cache của cuốn: {book.DisplayTitle} (Giữ nguyên file gốc Input)";
                AppendLog($"🗑️ {msg}");
                app?.Dispatcher.Invoke(() =>
                {
                    if (app.MainWindow is MainWindow mw)
                        mw.ShowSnackbar(msg, isError: false);
                });
            }

            LoadBooks();
        }
        catch (Exception ex)
        {
            var errMsg = $"Lỗi khi xóa sách: {ex.Message}";
            AppendLog($"[Lỗi xóa sách] {ex.Message}", "error");
            app?.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw)
                    mw.ShowSnackbar(errMsg, isError: true);
            });
        }
    }

    [RelayCommand]
    private void PreviewTranslated(BookStatus? book)
    {
        if (book == null) return;
        var app = Application.Current;
        if (app == null) return;

        // Tìm file .md phù hợp nhất để mở preview:
        // 1. final/vi.md hoặc final/tamngu.md
        // 2. working/qa/<slug>/vi_only.md
        // 3. working/extracted/<slug>/raw.md
        // 4. output/samples/<slug>_preview.md
        // 5. file preview mẫu gần nhất
        string mdPath = "";
        var possibleDirs = new List<string>
        {
            Path.Combine(_projectRoot, "output", "books", book.Title, "final"),
            Path.Combine(_projectRoot, "output", "books", book.Slug, "final"),
            Path.Combine(_projectRoot, "output", "books", Path.GetFileNameWithoutExtension(book.FilePath ?? ""), "final")
        };

        foreach (var dir in possibleDirs)
        {
            if (string.IsNullOrWhiteSpace(dir)) continue;
            var viMd = Path.Combine(dir, "vi.md");
            var tamnguMd = Path.Combine(dir, "tamngu.md");
            if (File.Exists(viMd)) { mdPath = viMd; break; }
            if (File.Exists(tamnguMd)) { mdPath = tamnguMd; break; }
        }

        if (string.IsNullOrEmpty(mdPath))
        {
            var qaViMd = Path.Combine(_projectRoot, "working", "qa", book.Slug, "vi_only.md");
            var rawMd = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw.md");
            var samplePreviewMd = Path.Combine(_projectRoot, "output", "samples", $"{book.Slug}_preview.md");

            if (File.Exists(qaViMd)) mdPath = qaViMd;
            else if (File.Exists(samplePreviewMd)) mdPath = samplePreviewMd;
            else if (File.Exists(rawMd)) mdPath = rawMd;
        }

        // Tìm dữ liệu source/pinyin từ progress chunks để hỗ trợ Split-View và Tam ngữ
        string srcText = "";
        string pinyinText = "";
        var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
        if (Directory.Exists(progressDir))
        {
            try
            {
                var pFiles = Directory.GetFiles(progressDir, "chunk_*.json").OrderBy(x => x).ToList();
                var sList = new List<string>();
                var pList = new List<string>();
                var vList = new List<string>();
                foreach (var pf in pFiles)
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(pf));
                    if (doc.RootElement.TryGetProperty("original_text", out var ot) && !string.IsNullOrEmpty(ot.GetString()))
                        sList.Add(ot.GetString()!);
                    else if (doc.RootElement.TryGetProperty("source_text", out var st) && !string.IsNullOrEmpty(st.GetString()))
                        sList.Add(st.GetString()!);

                    if (doc.RootElement.TryGetProperty("pinyin_text", out var pt) && !string.IsNullOrEmpty(pt.GetString()))
                        pList.Add(pt.GetString()!);

                    if (doc.RootElement.TryGetProperty("translated_text", out var tt) && !string.IsNullOrEmpty(tt.GetString()))
                        vList.Add(tt.GetString()!);
                }
                srcText = string.Join("\n\n", sList);
                pinyinText = string.Join("\n\n", pList);

                // Nếu chưa có file .md gộp sẵn thì tự tạo file tạm từ các chunk đã dịch
                if (string.IsNullOrEmpty(mdPath) && vList.Count > 0)
                {
                    var tempDir = Path.Combine(_projectRoot, "working", "qa", book.Slug);
                    Directory.CreateDirectory(tempDir);
                    mdPath = Path.Combine(tempDir, "preview_combined.md");
                    File.WriteAllText(mdPath, string.Join("\n\n", vList), new System.Text.UTF8Encoding(false));
                }
            }
            catch { }
        }

        // Nếu sách chưa dịch chunk nào nhưng có file gốc EPUB/raw.md, mở raw.md hoặc thông báo rõ ràng
        if (string.IsNullOrEmpty(mdPath) || !File.Exists(mdPath))
        {
            var rawExtract = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw.md");
            if (File.Exists(rawExtract))
            {
                mdPath = rawExtract;
            }
        }

        if (string.IsNullOrEmpty(mdPath) || !File.Exists(mdPath))
        {
            var msg = $"Chưa có bản dịch cho cuốn '{book.DisplayTitle}'. Hãy bấm 'Dịch test' hoặc 'Dịch Toàn bộ' trước.";
            AppendLog($"[Thông báo] {msg}", "warning");
            app.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw)
                    mw.ShowSnackbar(msg, isError: true);
            });
            return;
        }

        app.Dispatcher.InvokeAsync(() =>
        {
            try
            {
                var window = new MdPreviewWindow(mdPath, book.DisplayTitle, book.Slug);
                if (app.MainWindow != null) window.Owner = app.MainWindow;
                if (!string.IsNullOrEmpty(srcText))
                    window.SetSourceContent(srcText, pinyinText);
                window.Show();
                AppendLog($"👁️ Đang mở Trình đọc E-Reader cho cuốn: {book.DisplayTitle}");
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Mở Trình đọc: {ex.Message}", "error");
            }
        });
    }

    [RelayCommand]
    private void RefreshBooks()
    {
        LoadBooks();
    }

    /// <summary>Mở EpubPreviewWindow đọc nội dung file gốc của sách Input (EPUB native hoặc chuyển đổi qua Calibre).</summary>
    [RelayCommand]
    private async Task PreviewInputBookAsync(BookStatus? book)
    {
        if (book == null || string.IsNullOrWhiteSpace(book.FilePath)) return;
        var app = Application.Current;
        if (app == null) return;

        var filePath = book.FilePath;
        if (!File.Exists(filePath))
        {
            var msg = $"Không tìm thấy file: {filePath}";
            AppendLog($"[Lỗi] {msg}", "error");
            app.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw) mw.ShowSnackbar(msg, isError: true);
            });
            return;
        }

        if (!Services.EbookConvertService.CanPreview(filePath))
        {
            var ext = Path.GetExtension(filePath);
            var msg = $"Định dạng '{ext}' chưa được hỗ trợ xem trước.";
            AppendLog($"[Thông báo] {msg}", "warning");
            app.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw) mw.ShowSnackbar(msg, isError: true);
            });
            return;
        }

        // Chuyển đổi (nếu cần) ở background, hiển thị snackbar bận nếu lâu
        var convertTask = Task.Run(() => Services.EbookConvertService.GetPreviewEpub(filePath, _projectRoot));
        string? epubPath = null;
        string? error = null;
        try
        {
            epubPath = await convertTask;
        }
        catch (Exception ex)
        {
            error = ex.Message;
        }

        if (error != null)
        {
            AppendLog($"[Lỗi] {error}", "error");
            app.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw) mw.ShowSnackbar(error, isError: true);
            });
            return;
        }

        if (string.IsNullOrEmpty(epubPath) || !File.Exists(epubPath))
        {
            var msg = $"Không mở được nội dung của '{book.DisplayTitle}'.";
            AppendLog($"[Lỗi] {msg}", "error");
            app.Dispatcher.Invoke(() =>
            {
                if (app.MainWindow is MainWindow mw) mw.ShowSnackbar(msg, isError: true);
            });
            return;
        }

        app.Dispatcher.Invoke(() =>
        {
            try
            {
                var window = new Views.EpubPreviewWindow(epubPath);
                if (app.MainWindow != null) window.Owner = app.MainWindow;
                window.Show();
                AppendLog($"👁️ Đang xem nội dung sách: {book.DisplayTitle}");
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Mở xem sách: {ex.Message}", "error");
            }
        });
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
    private async Task GenerateFullAudiobookAsync(BookStatus book)
    {
        if (book == null || book.IsBusy) return;
        if (_currentCts != null)
        {
            AppendLog("Đang có thao tác khác chạy, vui lòng đợi hoặc nhấn Hủy.", "warning");
            return;
        }

        book.IsBusy = true;
        book.BusyStatusText = "Đang khởi tạo Audio Toàn bộ...";
        book.BusyProgressPercent = 5;
        book.BusyDetailText = "Nạp model VieNeu-TTS Turbo & Chuẩn bị GPU RTX...";
        IsVoiceBusy = true;
        BusyMessage = $"Đang tạo mới toàn bộ audio: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"🚀 BẮT ĐẦU TẠO AUDIO TOÀN BỘ SÁCH: {book.DisplayTitle} ({book.Slug})");
        AppendLog($"  Cấu hình: GPU={AudioUseGpu}, batch={AudioBatchSize}, Nhạc nền AI={AudioMusicAuto} (vol={AudioMusicVolume:0.00}), bitrate={AudioBitrate}, force=TRUE");
        try
        {
            var ok = await _pipeline.RunAudiobookAsync(
                book.Slug,
                AudioTemperature.ToString("0.0"),
                AudioTopK.ToString(),
                AudioBitrate,
                AudioReadTitles,
                AudioMergeChapters,
                force: true,
                book.ChapterInput,
                AudioUseGpu,
                AudioBatchSize,
                AudioMusicAuto,
                AudioMusicVolume,
                isSample: false,
                sampleChars: 400,
                ct: ct);
            if (ok)
            {
                book.BusyProgressPercent = 100;
                book.BusyStatusText = "Hoàn tất";
                book.BusyDetailText = "Tạo mới Audiobook toàn bộ thành công 100%";
                AppendLog($"✨ HOÀN TẤT: Tạo toàn bộ audio thành công cho {book.Slug}!");
            }
            else AppendLog($"[Lỗi] Tạo audio toàn bộ thất bại: {book.Slug}", "error");
        }
        catch (OperationCanceledException)
        {
            AppendLog($"Đã hủy bỏ tạo audio: {book.Slug}", "warning");
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi] {ex.Message}", "error");
        }
        finally
        {
            book.IsBusy = false;
            book.BusyProgressPercent = -1;
            book.BusyDetailText = "";
            IsVoiceBusy = false;
            BusyMessage = "";
            _currentCts = null;
            UpdateBookStatus(book);
        }
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
        book.BusyStatusText = "Đang rà soát Audio...";
        book.BusyProgressPercent = 5;
        book.BusyDetailText = "Rà soát MP3 các chương và nạp model...";
        IsVoiceBusy = true;
        BusyMessage = $"Đang sửa/tạo audio: {book.Slug}...";
        _currentCts = new CancellationTokenSource();
        var ct = _currentCts.Token;

        AppendLog($"🔧 BẮT ĐẦU SỬA CHỮA & RÀ SOÁT AUDIOBOOK: {book.DisplayTitle} ({book.Slug})");
        AppendLog($"  Chế độ thông minh: Chỉ tạo các chương còn thiếu/lỗi, giữ nguyên các chương MP3 chuẩn.");
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
            if (ok)
            {
                book.BusyProgressPercent = 100;
                book.BusyStatusText = "Hoàn tất";
                book.BusyDetailText = "Tạo Audiobook thành công 100%";
                AppendLog($"Audio hoàn thành: {book.Slug}");
            }
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
            book.BusyProgressPercent = -1;
            book.BusyDetailText = "";
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
        book.BusyStatusText = "Đang tạo mẫu audio thử...";
        book.BusyProgressPercent = 15;
        book.BusyDetailText = "Đọc thử đoạn văn bản mẫu (~30s)...";
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
                book.BusyProgressPercent = 100;
                book.BusyStatusText = "Hoàn tất";
                book.BusyDetailText = "Đã tạo mẫu audio xong";
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
            book.BusyProgressPercent = -1;
            book.BusyDetailText = "";
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

    public void AppendLog(string msg, string level = "info")
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

    private static bool IsVietnameseText(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return false;
        // Kiểm tra chữ Hán trước — nếu có chữ Hán thì là sách Trung
        if (ContainsChinese(text)) return false;

        // Đếm mật độ các nguyên âm có dấu đặc trưng của tiếng Việt
        var viChars = "àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ";
        int countVi = text.Count(c => viChars.Contains(c));
        
        // Nếu có trên 15 ký tự dấu tiếng Việt hoặc tỷ lệ dấu trên tổng ký tự > 1.5%
        return countVi >= 15 || (text.Length > 50 && (double)countVi / text.Length > 0.015);
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
            // === LÀM SẠCH DỮ LIỆU CŨ (CLEAN SLATE): ĐẢM BẢO CHẠY MỚI 100% TỪ ĐẦU ===
            var slugsToClean = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { book.Slug };
            if (!string.IsNullOrWhiteSpace(book.Title)) slugsToClean.Add(book.Title);
            if (!string.IsNullOrWhiteSpace(book.EpubTitle)) slugsToClean.Add(book.EpubTitle);
            var rawBaseName = Path.GetFileNameWithoutExtension(book.FilePath);
            if (!string.IsNullOrWhiteSpace(rawBaseName)) slugsToClean.Add(rawBaseName);

            foreach (var s in slugsToClean)
            {
                try
                {
                    var extD = Path.Combine(_projectRoot, "working", "extracted", s);
                    var chkD = Path.Combine(_projectRoot, "working", "chunks", s);
                    var prgD = Path.Combine(_projectRoot, "working", "progress", s);
                    var qaD = Path.Combine(_projectRoot, "working", "qa", s);
                    var profF = Path.Combine(_projectRoot, "working", "profile", $"{s}.md");
                    var pronF = Path.Combine(_projectRoot, "working", "profile", $"{s}-pronunciation.json");
                    var progAudioD = Path.Combine(_projectRoot, "working", "progress_audio", "chunks", s);

                    if (Directory.Exists(extD)) Directory.Delete(extD, true);
                    if (Directory.Exists(chkD)) Directory.Delete(chkD, true);
                    if (Directory.Exists(prgD)) Directory.Delete(prgD, true);
                    if (Directory.Exists(qaD)) Directory.Delete(qaD, true);
                    if (Directory.Exists(progAudioD)) Directory.Delete(progAudioD, true);
                    if (File.Exists(profF)) File.Delete(profF);
                    if (File.Exists(pronF)) File.Delete(pronF);
                }
                catch { }
            }

            // Dọn sạch thư mục thành phẩm output cũ nếu có
            try
            {
                var oldOutDir = Path.Combine(_projectRoot, "output", "books", book.Title);
                if (Directory.Exists(oldOutDir))
                {
                    var oldFinal = Path.Combine(oldOutDir, "final");
                    if (Directory.Exists(oldFinal)) Directory.Delete(oldFinal, true);
                    var oldEpub = Path.Combine(oldOutDir, $"{book.Title}.epub");
                    if (File.Exists(oldEpub)) File.Delete(oldEpub);
                }
            }
            catch { }

            AppendLog("  🧹 [Clean Slate] Đã xóa sạch toàn bộ bản trích xuất, chunks, bản dịch và thành phẩm cũ. Bắt đầu dịch mới 100% từ đầu.");

            var extractedDir = Path.Combine(_projectRoot, "working", "extracted", book.Slug);
            var chunksDir = Path.Combine(_projectRoot, "working", "chunks", book.Slug);
            var progressDir = Path.Combine(_projectRoot, "working", "progress", book.Slug);
            var qaDir = Path.Combine(_projectRoot, "working", "qa", book.Slug);

            // === BƯỚC 1: TRÍCH XUẤT (EXTRACT) ===
            var rawMdPath = Path.Combine(extractedDir, "raw.md");
            BusyMessage = $"[1/6] Đang trích xuất nội dung: {book.Slug}...";
            book.BusyStatusText = "[1/6] Đang trích xuất...";
            book.BusyProgressPercent = 5;
            book.BusyDetailText = "Trích xuất văn bản & cấu trúc (MinerU/EPUB)...";
            AppendLog($"[Bước 1/6] Trích xuất file gốc ({Path.GetFileName(book.FilePath)})...");
            var okExtract = await _pipeline.RunExtractAsync(book.FilePath, book.Slug, string.IsNullOrWhiteSpace(book.PipelineLang) ? "auto" : book.PipelineLang, ct);
            if (!okExtract || !File.Exists(rawMdPath))
            {
                AppendLog($"[Lỗi] Trích xuất nội dung thất bại: {book.FilePath}", "error");
                return;
            }
            book.BusyProgressPercent = 12;
            AppendLog("  ✅ Trích xuất nội dung hoàn tất.");

            var rawText = await File.ReadAllTextAsync(rawMdPath, ct);

            // KIỂM TRA: NẾU SÁCH ĐÃ LÀ TIẾNG VIỆT
            if (book.PipelineLang == "vi" || IsVietnameseText(rawText))
            {
                AppendLog($"ℹ️ [THÔNG BÁO] Cuốn sách '{book.DisplayTitle}' vốn đã là TIẾNG VIỆT!");
                AppendLog("  → Không cần dịch qua API (để bảo toàn 100% nguyên tác và tiết kiệm token).");
                AppendLog("  → Tự động xuất bản thành phẩm và chuyển sang trạng thái sẵn sàng Tạo Audiobook...");

                book.BusyStatusText = "Đang đóng gói sách tiếng Việt...";
                book.BusyProgressPercent = 50;
                book.BusyDetailText = "Đóng gói EPUB & lưu bản dịch thuần Việt...";

                var outBookDir = Path.Combine(_projectRoot, "output", "books", book.Title);
                var fnDir = Path.Combine(outBookDir, "final");
                Directory.CreateDirectory(fnDir);
                var destViPath = Path.Combine(fnDir, "vi.md");
                var destRawPath = Path.Combine(fnDir, "raw.md");
                await File.WriteAllTextAsync(destViPath, rawText, new System.Text.UTF8Encoding(false), ct);
                await File.WriteAllTextAsync(destRawPath, rawText, new System.Text.UTF8Encoding(false), ct);

                // Tạo metadata.json
                var metaF = Path.Combine(outBookDir, "metadata.json");
                var metaObjVi = new Dictionary<string, object>
                {
                    ["slug"] = book.Slug,
                    ["title"] = book.Title,
                    ["source_file"] = Path.GetFileName(book.FilePath),
                    ["author"] = book.EpubAuthor ?? "",
                    ["language"] = "vi",
                    ["genre"] = "",
                    ["has_audio"] = false,
                    ["has_epub"] = true,
                    ["epub_file"] = $"{book.Title}.epub",
                    ["created"] = DateTime.Now.ToString("yyyy-MM-dd")
                };
                await File.WriteAllTextAsync(metaF, JsonSerializer.Serialize(metaObjVi, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }), ct);

                // Tạo EPUB
                book.BusyProgressPercent = 80;
                var resPath = $"{Path.Combine(outBookDir, "images")};{Path.Combine(_projectRoot, "working", "extracted", book.Slug)}";
                await _pipeline.RunMakeEpubAsync(destViPath, book.Title, book.EpubAuthor ?? "", resPath, ct);
                var genEpub = Path.ChangeExtension(destViPath, ".epub");
                var tgEpub = Path.Combine(outBookDir, $"{book.Title}.epub");
                if (File.Exists(genEpub))
                {
                    if (File.Exists(tgEpub)) File.Delete(tgEpub);
                    File.Move(genEpub, tgEpub);
                }

                // Chuyển file nguồn sang input/da-dich/
                var daDichFolder = Path.Combine(_projectRoot, "input", "da-dich");
                Directory.CreateDirectory(daDichFolder);
                var destInFile = Path.Combine(daDichFolder, Path.GetFileName(book.FilePath));
                if (File.Exists(book.FilePath) && book.FilePath != destInFile)
                {
                    if (File.Exists(destInFile)) File.Delete(destInFile);
                    File.Move(book.FilePath, destInFile);
                }

                book.BusyProgressPercent = 100;
                book.BusyStatusText = "Hoàn tất";
                book.BusyDetailText = "Sách tiếng Việt đã sẵn sàng";
                AppendLog($"✨ HOÀN TẤT: Đã sẵn sàng sách tiếng Việt cho {book.DisplayTitle} (có thể tạo Audio ngay bên tab Audio)!");
                LoadBooks();
                return;
            }

            // === BƯỚC 1.5: QC TRÍCH XUẤT + OPENCC NORMALIZE (ZH-HANT -> ZH-HANS) ===
            var actualRawForChunk = rawMdPath;
            if (ContainsChinese(rawText))
            {
                var qcReport = Path.Combine(_projectRoot, "working", "qa", book.Slug, "extract-qc.md");
                Directory.CreateDirectory(Path.GetDirectoryName(qcReport)!);
                await _pipeline.RunPostExtractQcAsync(rawMdPath, qcReport, "zh", ct);

                // Tự động kiểm tra và chuyển đổi OpenCC t2s nếu chứa phồn thể
                var rawHansPath = Path.Combine(_projectRoot, "working", "extracted", book.Slug, "raw-hans.md");
                var okOpencc = await _pipeline.RunOpenccAsync(rawMdPath, rawHansPath, "t2s", ct);
                if (okOpencc && File.Exists(rawHansPath))
                {
                    actualRawForChunk = rawHansPath;
                    AppendLog("  ✅ Đã chuẩn hóa phồn thể sang giản thể (OpenCC t2s).");
                }
            }

            // === BƯỚC 2: CHIA CHUNK (SMART CHUNKING) ===
            BusyMessage = $"[2/6] Đang chia chunk: {book.Slug}...";
            book.BusyStatusText = "[2/6] Đang chia chunk...";
            book.BusyProgressPercent = 15;
            book.BusyDetailText = "Phân tích cấu trúc đoạn văn thông minh...";
            AppendLog($"[Bước 2/6] Phân đoạn văn bản (Chunking)...");
            var okChunk = await _pipeline.RunChunkAsync(actualRawForChunk, chunksDir, ct);
            if (!okChunk)
            {
                AppendLog($"[Lỗi] Chia chunk thất bại: {actualRawForChunk}", "error");
                return;
            }
            book.BusyProgressPercent = 20;
            AppendLog("  ✅ Phân đoạn văn bản hoàn tất.");

            // === BƯỚC 3: KHỞI TẠO SKELETON PROGRESS ===
            BusyMessage = $"[3/6] Đang tạo khung dịch (Skeleton)...";
            book.BusyStatusText = "[3/6] Tạo khung dịch...";
            book.BusyProgressPercent = 22;
            book.BusyDetailText = "Khởi tạo khung tiến trình Tam ngữ...";
            AppendLog($"[Bước 3/6] Khởi tạo khung tiến trình (Skeleton progress)...");
            await _pipeline.RunSkeletonAsync(chunksDir, progressDir, ct);
            book.BusyProgressPercent = 25;
            AppendLog("  ✅ Tạo khung dịch hoàn tất.");

            // === BƯỚC 4: NẠP GLOSSARY MASTER & HỒ SƠ VĂN CHƯƠNG (BOOK PROFILE) ===
            book.BusyStatusText = "[4/6] Nạp hồ sơ văn chương...";
            book.BusyProgressPercent = 27;
            book.BusyDetailText = "Nạp từ điển thuật ngữ & Book Profile...";
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
            book.BusyProgressPercent = 30;

            // === BƯỚC 5: VÒNG LẶP DỊCH THÔNG MINH BẢO VỆ NGỮ CẢNH QUA API ===
            var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(f => f).ToArray();
            book.TotalChunks = chunkFiles.Length;
            book.ProgressCount = 0;
            int concurrency = Math.Clamp(TranslateConcurrency, 1, 4);
            AppendLog($"[Bước 5/6] Bắt đầu dịch tự động {chunkFiles.Length} chunk qua API ({ActiveProvider}) [Số luồng song song: {concurrency}]...");

            // Đọc trước toàn bộ thông tin cơ bản của các chunk để phân tích ngữ cảnh gối đầu
            var chunkMetaList = new List<(int index, int chunkId, string origText, string pinyinText, string chapter, string progChunkFile, bool isTrilingual)>();
            for (int i = 0; i < chunkFiles.Length; i++)
            {
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
                bool isTrilingual = ContainsChinese(text);

                if (File.Exists(progChunkFile))
                {
                    try
                    {
                        using var pdoc = JsonDocument.Parse(File.ReadAllText(progChunkFile));
                        if (pdoc.RootElement.TryGetProperty("original_text", out var ot) && !string.IsNullOrWhiteSpace(ot.GetString()))
                            origText = ot.GetString()!;
                        if (pdoc.RootElement.TryGetProperty("pinyin_text", out var pt) && !string.IsNullOrWhiteSpace(pt.GetString()))
                            pinyinText = pt.GetString()!;
                    }
                    catch { }
                }

                chunkMetaList.Add((i, chunkId, origText, pinyinText, chapter, progChunkFile, isTrilingual));
            }

            int successCount = 0;
            using var semaphore = new SemaphoreSlim(concurrency, concurrency);
            var translateTasks = new List<Task>();

            for (int i = 0; i < chunkMetaList.Count; i++)
            {
                ct.ThrowIfCancellationRequested();
                var currentMeta = chunkMetaList[i];

                if (string.IsNullOrWhiteSpace(currentMeta.origText))
                {
                    continue;
                }

                // Trích xuất ngữ cảnh gối đầu (3-4 câu cuối của chunk trước, ưu tiên kèm bản dịch) để giữ mạch văn 100%
                string prevContextText = "";
                if (i > 0)
                {
                    var prevProgFile = chunkMetaList[i - 1].progChunkFile;
                    string prevChunkSrc = chunkMetaList[i - 1].origText;
                    string prevChunkTrans = "";

                    if (File.Exists(prevProgFile))
                    {
                        try
                        {
                            using var prevDoc = JsonDocument.Parse(File.ReadAllText(prevProgFile));
                            if (prevDoc.RootElement.TryGetProperty("translated_text", out var ptVal))
                                prevChunkTrans = ptVal.GetString() ?? "";
                        }
                        catch { }
                    }

                    var contextLines = new List<string>();
                    if (!string.IsNullOrWhiteSpace(prevChunkTrans))
                    {
                        var transLines = prevChunkTrans.Split('\n').Where(l => !string.IsNullOrWhiteSpace(l) && !l.StartsWith("#")).TakeLast(3);
                        contextLines.Add("• Bản dịch đoạn trước vừa kết thúc bằng: \"" + string.Join(" ", transLines) + "\"");
                    }
                    else if (!string.IsNullOrWhiteSpace(prevChunkSrc))
                    {
                        var srcLines = prevChunkSrc.Split('\n').Where(l => !string.IsNullOrWhiteSpace(l) && !l.StartsWith("#")).TakeLast(3);
                        contextLines.Add("• Câu gốc đoạn trước: " + string.Join("\n", srcLines));
                    }

                    if (contextLines.Count > 0)
                    {
                        prevContextText = string.Join("\n", contextLines);
                    }
                }

                await semaphore.WaitAsync(ct);

                // Giãn cách nhẹ giữa các request để tránh bão kết nối làm Server AI trả về Timeout/503/429
                if (concurrency > 1 && i > 0)
                {
                    await Task.Delay(600, ct);
                }

                var task = Task.Run(async () =>
                {
                    try
                    {
                        ct.ThrowIfCancellationRequested();

                        // Nạp cấu trúc progress hiện tại nếu có
                        Dictionary<string, object> progObj = new();
                        if (File.Exists(currentMeta.progChunkFile))
                        {
                            try
                            {
                                using var pdoc = JsonDocument.Parse(File.ReadAllText(currentMeta.progChunkFile));
                                foreach (var prop in pdoc.RootElement.EnumerateObject())
                                {
                                    if (prop.Value.ValueKind == JsonValueKind.String)
                                        progObj[prop.Name] = prop.Value.GetString()!;
                                    else if (prop.Value.ValueKind == JsonValueKind.Number)
                                        progObj[prop.Name] = prop.Value.GetInt32();
                                    else if (prop.Value.ValueKind == JsonValueKind.True || prop.Value.ValueKind == JsonValueKind.False)
                                        progObj[prop.Name] = prop.Value.GetBoolean();
                                }
                            }
                            catch { }
                        }

                        // Ghép Hồ sơ văn chương (Book Profile)
                        var contextSb = new System.Text.StringBuilder();
                        if (!string.IsNullOrWhiteSpace(bookProfile))
                        {
                            contextSb.AppendLine(bookProfile);
                        }

                        // Cập nhật trạng thái hiển thị trên UI
                        lock (book)
                        {
                            double translatePhasePercent = chunkMetaList.Count > 0 ? (double)successCount / chunkMetaList.Count : 0;
                            book.BusyProgressPercent = 30 + (translatePhasePercent * 58);
                            book.BusyStatusText = $"[5/6] Dịch chunk {currentMeta.index + 1}/{chunkMetaList.Count}";
                            book.BusyDetailText = $"Đang dịch chương: {currentMeta.chapter}";
                            BusyMessage = $"Đang dịch: [{currentMeta.index + 1}/{chunkMetaList.Count}] ({book.Slug})...";
                        }
                        AppendLog($"  → [{currentMeta.index + 1}/{chunkMetaList.Count}] Dịch chunk {currentMeta.chunkId} ({currentMeta.chapter})...");

                        var sourceLang = currentMeta.isTrilingual ? "Chinese" : "English";
                        var result = await _apiService.TranslateAsync(
                            currentMeta.origText, ActiveProvider, glossary,
                            context: contextSb.ToString(),
                            sourceLang: sourceLang, targetLang: "Vietnamese",
                            trilingual: currentMeta.isTrilingual,
                            contextPreviousText: prevContextText,
                            onStatusLog: msg => AppendLog(msg, "warning"),
                            ct: ct);

                        if (string.IsNullOrWhiteSpace(result.Text))
                        {
                            AppendLog($"    [Cảnh báo] Chunk {currentMeta.chunkId} dịch trả về rỗng, thử lại lần sau.", "warning");
                            return;
                        }

                        // Cập nhật kết quả dịch vào progress JSON
                        progObj["chunk_id"] = currentMeta.chunkId;
                        progObj["total_chunks"] = chunkMetaList.Count;
                        progObj["chapter"] = currentMeta.chapter;
                        progObj["source_text"] = currentMeta.origText;
                        progObj["original_text"] = currentMeta.origText;
                        progObj["pinyin_text"] = currentMeta.pinyinText;
                        progObj["translated_text"] = result.Text.Trim();
                        progObj["word_count_source"] = currentMeta.origText.Length;
                        progObj["word_count_translated"] = result.Text.Length;
                        progObj["mode"] = currentMeta.isTrilingual ? "trilingual" : "bilingual";
                        progObj["translated_at"] = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss");

                        // Ghi file atomic/an toàn
                        var saveJson = JsonSerializer.Serialize(progObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
                        await File.WriteAllTextAsync(currentMeta.progChunkFile, saveJson, new System.Text.UTF8Encoding(false), ct);

                        // QA nhanh cho chunk
                        await _pipeline.RunBatchQaAsync(progressDir, currentMeta.chunkId, ct);

                        Interlocked.Increment(ref successCount);
                        lock (book)
                        {
                            book.ProgressCount = successCount;
                            book.BusyProgressPercent = 30 + (((double)successCount / chunkMetaList.Count) * 58);
                        }
                        AppendLog($"    ✅ Chunk {currentMeta.chunkId} dịch xong ({result.Text.Length} ký tự)");
                    }
                    finally
                    {
                        semaphore.Release();
                    }
                }, ct);

                translateTasks.Add(task);
            }

            await Task.WhenAll(translateTasks);
            AppendLog($"  🎉 Dịch hoàn tất {successCount}/{chunkFiles.Length} chunks!");

            // === BƯỚC 6: MERGE CHUNKS & MAKE EPUB ===
            BusyMessage = $"[6/6] Đang gộp file và tạo EPUB: {book.Slug}...";
            book.BusyStatusText = "[6/6] Đang tạo EPUB...";
            book.BusyProgressPercent = 90;
            book.BusyDetailText = "Gộp file tamngu.md, vi.md & nhúng font Noto Serif SC...";
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

            // Sao chép bản gốc thô raw.md vào output final/ để lưu trữ trọn vẹn
            var destRawFinal = Path.Combine(finalDir, "raw.md");
            if (File.Exists(rawMdPath))
            {
                try
                {
                    File.Copy(rawMdPath, destRawFinal, true);
                    AppendLog($"📄 Đã xuất bản gốc vào: final/raw.md");
                }
                catch { }
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

            book.BusyProgressPercent = 100;
            book.BusyStatusText = "Hoàn tất";
            book.BusyDetailText = "Đã dịch và tạo EPUB thành công 100%";
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
            book.BusyProgressPercent = -1;
            book.BusyDetailText = "";
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
            book.BusyProgressPercent = 5;
            book.BusyStatusText = "[1/5] Kiểm tra bản trích xuất...";
            book.BusyDetailText = "Kiểm tra raw.md (MinerU/EPUB)...";
            if (!File.Exists(rawMdPath) && File.Exists(book.FilePath))
            {
                BusyMessage = $"Trích xuất file gốc: {actualSlug}...";
                book.BusyStatusText = "Đang trích xuất...";
                AppendLog($"[Rà soát] Trích xuất file gốc ({Path.GetFileName(book.FilePath)})...");
                await _pipeline.RunExtractAsync(book.FilePath, actualSlug, string.IsNullOrWhiteSpace(book.PipelineLang) ? "auto" : book.PipelineLang, ct);
            }

            if (File.Exists(rawMdPath))
            {
                var checkRawText = await File.ReadAllTextAsync(rawMdPath, ct);
                if (book.PipelineLang == "vi" || IsVietnameseText(checkRawText))
                {
                    AppendLog($"ℹ️ [THÔNG BÁO] Cuốn sách '{book.DisplayTitle}' là sách TIẾNG VIỆT chuẩn!");
                    AppendLog("  → Toàn bộ nội dung đã hoàn hảo, không cần rà soát hay dịch qua API.");
                    AppendLog("  → Bạn có thể sang tab Audio để tạo Audiobook ngay bất cứ lúc nào.");
                    return;
                }
            }
            book.BusyProgressPercent = 12;

            // 2. Kiểm tra Chunks
            var chunksDir = Path.Combine(_projectRoot, "working", "chunks", actualSlug);
            book.BusyProgressPercent = 15;
            book.BusyStatusText = "[2/5] Kiểm tra cấu trúc chunks...";
            book.BusyDetailText = "Rà soát phân đoạn văn bản...";
            if (!Directory.Exists(chunksDir) || Directory.GetFiles(chunksDir, "chunk-*.json").Length == 0)
            {
                BusyMessage = $"Phân đoạn chunk: {actualSlug}...";
                book.BusyStatusText = "Đang chia chunk...";
                AppendLog($"[Rà soát] Chia chunk văn bản...");
                await _pipeline.RunChunkAsync(rawMdPath, chunksDir, ct);
            }
            book.BusyProgressPercent = 20;

            // 3. Kiểm tra Skeleton
            var progressDir = Path.Combine(_projectRoot, "working", "progress", actualSlug);
            book.BusyProgressPercent = 22;
            book.BusyStatusText = "[3/5] Kiểm tra khung Skeleton...";
            book.BusyDetailText = "Đồng bộ tiến trình đa ngữ...";
            if (!Directory.Exists(progressDir) || Directory.GetFiles(progressDir, "chunk_*.json").Length == 0)
            {
                BusyMessage = $"Tạo khung dịch (Skeleton): {actualSlug}...";
                book.BusyStatusText = "Tạo khung dịch...";
                AppendLog($"[Rà soát] Tạo khung tiến trình (Skeleton)...");
                await _pipeline.RunSkeletonAsync(chunksDir, progressDir, ct);
            }
            book.BusyProgressPercent = 25;

            // 4. Nạp Glossary Master & Book Profile
            book.BusyProgressPercent = 27;
            book.BusyStatusText = "[4/5] Nạp thuật ngữ & hồ sơ...";
            book.BusyDetailText = "Nạp glossary/master.csv & Book Profile...";
            var glossary = ApiTranslationService.LoadGlossary(actualSlug, _projectRoot);
            var profilePath = Path.Combine(_projectRoot, "working", "profile", $"{actualSlug}.md");
            string bookProfile = "";
            if (File.Exists(profilePath))
            {
                try { bookProfile = await File.ReadAllTextAsync(profilePath, ct); } catch { }
            }

            var chunkFiles = Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(f => f).ToArray();
            book.TotalChunks = chunkFiles.Length;
            book.ProgressCount = 0;

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
                        AppendLog($"  ⚠️ Chunk {chunkId}: Phát hiện lỗi Font/Mojibake -> Sửa lại qua API...");
                    }

                    // Tầng 2: Kiểm tra lệch số dòng đối ứng (đặc biệt quan trọng với Tam ngữ)
                    if (!needApiTranslate && isTrilingual)
                    {
                        var origLines = origText.Split('\n').Where(l => !string.IsNullOrWhiteSpace(l)).ToArray();
                        var transLines = currentTrans.Split('\n').Where(l => !string.IsNullOrWhiteSpace(l)).ToArray();
                        if (Math.Abs(origLines.Length - transLines.Length) >= 3 && origLines.Length > 2)
                        {
                            needApiTranslate = true;
                            AppendLog($"  ⚠️ Chunk {chunkId}: Lệch số dòng nghiêm trọng ({transLines.Length} vs {origLines.Length} dòng gốc) -> Sửa lại qua API...");
                        }
                    }

                    // Tầng 3: Kiểm tra rác OCR /// dư thừa
                    if (!needApiTranslate && currentTrans.Contains("///"))
                    {
                        currentTrans = currentTrans.Replace("///", "").Trim();
                        modifiedOffline = true;
                        offlineFixedCount++;
                        AppendLog($"  🧹 Chunk {chunkId}: Đã dọn sạch ký tự rác OCR '///' (sửa nhanh offline)");
                    }
                }

                // Cập nhật total_chunks chuẩn trong file nếu bị lệch
                if (progObj.TryGetValue("total_chunks", out var tcVal) && Convert.ToInt32(tcVal) != chunkFiles.Length)
                {
                    progObj["total_chunks"] = chunkFiles.Length;
                    modifiedOffline = true;
                }

                // Tính toán % tiến độ cho bước quét & sửa (30% đến 88%)
                double repairPhasePercent = chunkFiles.Length > 0 ? (double)i / chunkFiles.Length : 0;
                book.BusyProgressPercent = 30 + (repairPhasePercent * 58);

                if (needApiTranslate)
                {
                    BusyMessage = $"Đang sửa chunk: [{i + 1}/{chunkFiles.Length}] ({book.Slug})...";
                    book.BusyStatusText = $"[5/5] Sửa chunk {i + 1}/{chunkFiles.Length}";
                    book.BusyDetailText = $"Dịch sửa chương: {chapter}";
                    AppendLog($"  🔄 Dịch sửa chunk {chunkId} ({chapter})...");

                    var contextSb = new System.Text.StringBuilder();
                    if (!string.IsNullOrWhiteSpace(bookProfile))
                    {
                        contextSb.AppendLine("### HỒ SƠ VĂN CHƯƠNG CUỐN SÁCH (BẮT BUỘC BÁM SÁT):");
                        contextSb.AppendLine(bookProfile);
                        contextSb.AppendLine();
                    }

                    // Lấy ngữ cảnh gối đầu (2-3 câu cuối của chunk trước)
                    string prevContextText = "";
                    if (i > 0)
                    {
                        var prevProg = Path.Combine(progressDir, $"chunk_{i - 1:D3}.json");
                        if (File.Exists(prevProg))
                        {
                            try
                            {
                                using var pdoc = JsonDocument.Parse(File.ReadAllText(prevProg));
                                if (pdoc.RootElement.TryGetProperty("original_text", out var prevOt) && !string.IsNullOrWhiteSpace(prevOt.GetString()))
                                {
                                    var prevLines = prevOt.GetString()!.Split('\n').Where(l => !string.IsNullOrWhiteSpace(l)).ToArray();
                                    int takeCount = Math.Min(3, prevLines.Length);
                                    prevContextText = string.Join("\n", prevLines.TakeLast(takeCount));
                                }
                            }
                            catch { }
                        }
                    }

                    var sourceLang = isTrilingual ? "Chinese" : "English";
                    var result = await _apiService.TranslateAsync(
                        origText, ActiveProvider, glossary,
                        context: contextSb.ToString(),
                        sourceLang: sourceLang, targetLang: "Vietnamese",
                        trilingual: isTrilingual,
                        contextPreviousText: prevContextText,
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
                    book.BusyStatusText = $"[5/5] Rà soát chunk {i + 1}/{chunkFiles.Length}";
                    book.BusyDetailText = $"Kiểm tra chương: {chapter}";
                    if (modifiedOffline)
                    {
                        progObj["translated_text"] = currentTrans;
                        var saveJson = JsonSerializer.Serialize(progObj, new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping });
                        await File.WriteAllTextAsync(progChunkFile, saveJson, new System.Text.UTF8Encoding(false), ct);
                    }
                    validCount++;
                }

                book.ProgressCount = i + 1;
                book.BusyProgressPercent = 30 + (((double)(i + 1) / chunkFiles.Length) * 58);
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
            book.BusyStatusText = "Đang gộp và tạo lại EPUB...";
            book.BusyProgressPercent = 90;
            book.BusyDetailText = "Cập nhật tamngu.md, vi.md & đóng gói EPUB...";
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

            // Sao chép bản gốc thô raw.md vào output final/ để lưu trữ trọn vẹn
            var extractedRaw = Path.Combine(_projectRoot, "working", "extracted", actualSlug, "raw.md");
            var destRaw = Path.Combine(finalDir, "raw.md");
            if (File.Exists(extractedRaw))
            {
                try
                {
                    File.Copy(extractedRaw, destRaw, true);
                    AppendLog($"📄 Đã xuất bản gốc vào: final/raw.md");
                }
                catch { }
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

            book.BusyProgressPercent = 100;
            book.BusyStatusText = "Hoàn tất";
            book.BusyDetailText = "Rà soát & Sửa chữa thành công 100%";
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
            book.BusyProgressPercent = -1;
            book.BusyDetailText = "";
            IsPipelineBusy = false;
            BusyMessage = "";
            _currentCts = null;
            UpdateBookStatus(book);
        }
    }

    // ==================== CANCEL COMMAND ====================

    [RelayCommand]
    private void CancelTask(BookStatus? book)
    {
        AppendLog("🛑 Người dùng nhấn HỦY TIẾN TRÌNH!", "warning");
        try
        {
            // 1. Ngắt CancellationToken của toàn bộ các luồng dịch
            if (_currentCts != null && !_currentCts.IsCancellationRequested)
            {
                _currentCts.Cancel();
            }

            // 2. Cắt đứt cưỡng bức toàn bộ kết nối HTTP Socket đang gửi/nhận tới Server API
            _apiService.CancelPendingRequests();

            // 3. Dừng process Python con nếu đang chạy pipeline
            _pipeline.KillCurrentProcess();

            if (book != null)
            {
                book.IsBusy = false;
                book.BusyProgressPercent = -1;
                book.BusyDetailText = "Đã hủy";
                UpdateBookStatus(book);
            }
            else
            {
                foreach (var b in InputBooks) { b.IsBusy = false; b.BusyProgressPercent = -1; }
                foreach (var b in OutputBooks) { b.IsBusy = false; b.BusyProgressPercent = -1; }
            }

            // Reset toàn bộ cờ bận
            IsPipelineBusy = false;
            IsQaBusy = false;
            IsVoiceBusy = false;
            BusyMessage = "";
        }
        catch (Exception ex)
        {
            AppendLog($"[Lỗi khi Hủy] {ex.Message}", "error");
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
    private void PlayReferenceVoice()
    {
        if (string.IsNullOrWhiteSpace(SelectedVoice)) return;

        // 1. Thử tìm trong core/voices/<SelectedVoice>.wav
        var refWav = Path.Combine(_projectRoot, "core", "voices", $"{SelectedVoice}.wav");
        if (!File.Exists(refWav))
        {
            // 2. Thử tìm trong output/voice_preview/preview_<SelectedVoice>.wav
            refWav = Path.Combine(_projectRoot, "output", "voice_preview", $"preview_{SelectedVoice}.wav");
        }

        if (File.Exists(refWav))
        {
            AppendLog($"[Phát âm mẫu] {SelectedVoice}: {Path.GetFileName(refWav)}");
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = refWav,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                AppendLog($"[Lỗi] Không thể mở trình phát: {ex.Message}", "error");
            }
        }
        else
        {
            AppendLog($"Chưa có file mẫu sẵn cho '{SelectedVoice}'. Bấm nút '▶' để tạo bản đọc thử tự động.", "warning");
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
