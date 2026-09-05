using System.Globalization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace TranslateBook.Models;

public partial class BookStatus : ObservableObject
{
    [ObservableProperty] private string _slug = "";
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(StatusText))]
    [NotifyPropertyChangedFor(nameof(DisplayTitle))]
    private string _source = ""; // "input" or "output"

    /// <summary>Tên hiển thị (tên sách gốc / tên thư mục output). Rỗng → dùng Slug.</summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(DisplayTitle))]
    [NotifyPropertyChangedFor(nameof(Initial))]
    private string _title = "";
    
    [ObservableProperty] private string _filePath = "";
    [ObservableProperty] private string _folderPath = "";
    [ObservableProperty] private string _inputCategory = ""; // "chua-lam", "da-dich", "da-audio", "root"
    
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    [NotifyPropertyChangedFor(nameof(ProgressPercent))]
    private bool _hasViMd;
    
    [ObservableProperty] private bool _hasEpub;
    [ObservableProperty] private int _mp3Count;
    [ObservableProperty] private int _totalChapters;
    
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(ProgressPercent))]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    private int _progressCount;
    
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(ProgressPercent))]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    private int _totalChunks;
    
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(AudioProgressPercent))]
    private int _audioDone;
    
    [ObservableProperty] 
    [NotifyPropertyChangedFor(nameof(AudioProgressPercent))]
    private int _audioTotal;
    
    [ObservableProperty] private string _chapterInput = "";

    /// <summary>Absolute path to a cover image if one exists, else empty.</summary>
    [ObservableProperty] private string _coverPath = "";

    // === Per-book pipeline config (chỉnh ngay trong card Input) ===

    /// <summary>Ngôn ngữ gốc của sách (auto/zh/zh-Hans/zh-Hant/en/vi). Mặc định "auto" — script tự nhận diện.</summary>
    [ObservableProperty] private string _pipelineLang = "auto";

    /// <summary>Tác giả cho EPUB metadata.</summary>
    [ObservableProperty] private string _epubAuthor = "";

    /// <summary>Tiêu đề EPUB (mặc định = tên file).</summary>
    [ObservableProperty] private string _epubTitle = "";

    /// <summary>Danh sách chương trích xuất được để dịch thử theo từng cuốn sách.</summary>
    [ObservableProperty] private System.Collections.ObjectModel.ObservableCollection<string> _availableChapters = new();

    /// <summary>Chương được chọn để dịch thử riêng cho cuốn sách này.</summary>
    [ObservableProperty] private string _selectedSampleChapter = "";

    /// <summary>Danh sách ngôn ngữ cho ComboBox trong card.</summary>
    public IReadOnlyList<string> LangOptions { get; } = new[]
    {
        "auto", "zh", "zh-Hans", "zh-Hant", "en", "vi"
    };

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    private bool _isBusy;

    /// <summary>Raised whenever any book's IsBusy changes, so global busy UI can react.</summary>
    public static event Action? AnyBusyChanged;

    partial void OnIsBusyChanged(bool value) => AnyBusyChanged?.Invoke();

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(StatusText))]
    private string _busyStatusText = "";

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ProgressPercent))]
    [NotifyPropertyChangedFor(nameof(AudioProgressPercent))]
    private double _busyProgressPercent = -1;

    [ObservableProperty]
    private string _busyDetailText = "";

    public double ProgressPercent =>
        IsBusy && BusyProgressPercent >= 0
            ? Math.Clamp(BusyProgressPercent, 0, 100)
            : HasViMd ? 100 : (TotalChunks > 0 ? (double)ProgressCount / TotalChunks * 100 : 0);

    public double AudioProgressPercent =>
        IsBusy && BusyProgressPercent >= 0
            ? Math.Clamp(BusyProgressPercent, 0, 100)
            : (AudioTotal > 0 ? (double)AudioDone / AudioTotal * 100 : (Mp3Count > 0 && TotalChapters > 0 ? (double)Mp3Count / TotalChapters * 100 : 0));

    public string StatusText
    {
        get
        {
            if (IsBusy)
            {
                if (!string.IsNullOrWhiteSpace(BusyStatusText))
                    return BusyStatusText;
                if (TotalChunks > 0)
                    return $"Đang xử lý ({ProgressCount}/{TotalChunks})";
                return "Đang xử lý...";
            }

            return Source == "input"
                ? "Chưa dịch"
                : HasViMd ? "Hoàn thành"
                : ProgressCount > 0 ? $"Đã dịch {ProgressCount}/{TotalChunks}"
                : "Chưa bắt đầu";
        }
    }

    /// <summary>Định dạng file (.epub, .pdf, .docx, .txt...)</summary>
    public string FileExtension
    {
        get
        {
            if (!string.IsNullOrEmpty(FilePath))
                return System.IO.Path.GetExtension(FilePath).TrimStart('.').ToUpperInvariant();
            if (!string.IsNullOrEmpty(Title) && Title.Contains('.'))
                return System.IO.Path.GetExtension(Title).TrimStart('.').ToUpperInvariant();
            return "EPUB";
        }
    }

    /// <summary>First letter of the title — used as the card avatar.</summary>
    public string Initial => string.IsNullOrEmpty(Title)
        ? (string.IsNullOrEmpty(Slug) ? "?" : Slug[..1].ToUpperInvariant())
        : Title[..1].ToUpperInvariant();

    public string DisplayTitle => !string.IsNullOrEmpty(Title)
        ? Title
        : new CultureInfo("vi-VN").TextInfo.ToTitleCase(Slug.Replace("-", " ").ToLower());
}
