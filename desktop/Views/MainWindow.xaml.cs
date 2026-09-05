using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;

namespace TranslateBook.Views
{

    public partial class MainWindow : FluentWindow
    {
        private readonly Wpf.Ui.SnackbarService _snackbarService = new();
        private readonly List<ViewModels.MainViewModel.LogEntry> _logHistory = new();

        // Cached brushes for log entry colors (avoids allocating a new SolidColorBrush per line)
        private static readonly SolidColorBrush BrushTimestamp = new(Color.FromRgb(0x75, 0x85, 0x95));
        private static readonly SolidColorBrush BrushError = new(Color.FromRgb(0xff, 0x52, 0x52));
        private static readonly SolidColorBrush BrushWarning = new(Color.FromRgb(0xff, 0xb7, 0x4d));
        private static readonly SolidColorBrush BrushSuccess = new(Color.FromRgb(0x69, 0xf0, 0xae));
        private static readonly SolidColorBrush BrushInfo = new(Color.FromRgb(0x40, 0xc4, 0xff));
        private static readonly SolidColorBrush BrushMusic = new(Color.FromRgb(0xe0, 0x82, 0xff));
        private static readonly SolidColorBrush BrushDefault = new(Color.FromRgb(0xd0, 0xd8, 0xe0));

        // Debounce timer for log filter: waits 200ms after last keystroke before re-rendering
        private DispatcherTimer? _logFilterDebounce;

        public MainWindow()
        {
            InitializeComponent();
            try
            {
                var iconUri = new Uri("pack://application:,,,/app_icon.png", UriKind.RelativeOrAbsolute);
                Icon = new System.Windows.Media.Imaging.BitmapImage(iconUri);
            }
            catch { }
            SystemThemeWatcher.Watch(this, WindowBackdropType.Acrylic, true);
            _snackbarService.SetSnackbarPresenter(SnackbarPresenter);
            PreviewKeyDown += MainWindow_PreviewKeyDown;
            Loaded += MainWindow_Loaded;
            Closing += MainWindow_Closing;
        }

        private void MainWindow_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            // Ctrl+F: focus ô GlobalSearchBox trên TitleBar và chọn toàn bộ text
            if (e.Key == System.Windows.Input.Key.F
                && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
            {
                e.Handled = true;
                NavigateToBooks();
                GlobalSearchBox?.Focus();
                GlobalSearchBox?.SelectAll();
            }
        }

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (NavView.SelectedItem is NavigationViewItem item && item.TargetPageType != null)
                NavView.Navigate(item.TargetPageType);
            else
                NavView.Navigate(typeof(BooksPage));

            if (DataContext is ViewModels.MainViewModel vm)
            {
                vm.LogEntryAdded += OnLogEntryAdded;
                vm.LogCleared += OnLogCleared;
                ReplayLogHistory(vm.LogText);
            }
        }

        /// <summary>Renders log lines that were written before the window subscribed.</summary>
        private void ReplayLogHistory(string logText)
        {
            if (string.IsNullOrEmpty(logText) || LogBox == null) return;
            foreach (var line in logText.Split('\n'))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var level = line.Contains("[ERR]") ? "error"
                    : line.Contains("[WARN]") ? "warning" : "info";
                var entry = new ViewModels.MainViewModel.LogEntry(line.TrimEnd('\r'), level);
                _logHistory.Add(entry);
                if (_logHistory.Count > 2000)
                    _logHistory.RemoveAt(0);
                if (FilterApplies(entry.Text))
                    AppendLogEntry(entry);
            }
            LogBox.ScrollToEnd();
        }

        private void OnLogEntryAdded(ViewModels.MainViewModel.LogEntry entry)
        {
            Dispatcher.Invoke(() =>
            {
                _logHistory.Add(entry);
                if (_logHistory.Count > 2000)
                    _logHistory.RemoveAt(0);

                if (DataContext is ViewModels.MainViewModel vm && !vm.LogExpanded && (entry.Level == "error" || entry.Text.Contains("Bắt đầu") || entry.Text.Contains("Đang tạo")))
                {
                    vm.LogExpanded = true;
                }

                if (FilterApplies(entry.Text))
                    AppendLogEntry(entry);
            });
        }

        private void OnLogCleared()
        {
            _logHistory.Clear();
            LogBox?.Document.Blocks.Clear();
        }

        private bool FilterApplies(string line)
        {
            if (DataContext is not ViewModels.MainViewModel vm) return true;
            var filter = vm.LogFilter?.Trim() ?? "";
            return string.IsNullOrEmpty(filter) ||
                   line.Contains(filter, StringComparison.OrdinalIgnoreCase);
        }

        private void AppendLogEntry(ViewModels.MainViewModel.LogEntry entry)
        {
            if (LogBox == null) return;

            var timeStr = DateTime.Now.ToString("HH:mm:ss");
            var para = new Paragraph { Margin = new Thickness(0, 1, 0, 1), LineHeight = 16 };

            // Timestamp in subtle muted color (reuses cached brush)
            var timeRun = new Run($"[{timeStr}] ") { Foreground = BrushTimestamp, FontWeight = FontWeights.Normal };
            para.Inlines.Add(timeRun);

            // Message with cached brushes per severity/content (no allocation per line)
            Brush textBrush;
            FontWeight weight = FontWeights.Normal;

            if (entry.Level == "error" || entry.Text.Contains("[Lỗi]") || entry.Text.Contains("Failed") || entry.Text.Contains("❌"))
            {
                textBrush = BrushError;
                weight = FontWeights.SemiBold;
            }
            else if (entry.Level == "warning" || entry.Text.Contains("[Cảnh báo]") || entry.Text.Contains("⚠️"))
            {
                textBrush = BrushWarning;
            }
            else if (entry.Text.Contains("Hoàn thành") || entry.Text.Contains("hoàn tất") || entry.Text.Contains("✅") || entry.Text.Contains("OK"))
            {
                textBrush = BrushSuccess;
                weight = FontWeights.SemiBold;
            }
            else if (entry.Text.Contains("Bắt đầu") || entry.Text.Contains("Đang tạo") || entry.Text.Contains("Chapter") || entry.Text.Contains("Chương") || entry.Text.Contains("RTF"))
            {
                textBrush = BrushInfo;
            }
            else if (entry.Text.Contains("🎵") || entry.Text.Contains("Nhạc nền") || entry.Text.Contains("giọng"))
            {
                textBrush = BrushMusic;
            }
            else
            {
                textBrush = BrushDefault;
            }

            var textRun = new Run(entry.Text) { Foreground = textBrush, FontWeight = weight };
            para.Inlines.Add(textRun);

            // Giữ tối đa 800 blocks trên màn hình UI để render siêu mượt
            if (LogBox.Document.Blocks.Count > 800)
            {
                LogBox.Document.Blocks.Remove(LogBox.Document.Blocks.FirstBlock);
            }

            LogBox.Document.Blocks.Add(para);
            LogBox.ScrollToEnd();
        }

        private void MainWindow_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
        {
            // Kill any running Python processes when closing
            if (DataContext is ViewModels.MainViewModel vm)
            {
                vm.LogEntryAdded -= OnLogEntryAdded;
                vm.LogCleared -= OnLogCleared;
                vm.KillCurrentProcess();
            }
        }

    private void ClearLogButton_Click(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
            vm.ClearLog();
    }

    private void CopyLogButton_Click(object sender, RoutedEventArgs e)
    {
        if (LogBox != null)
        {
            var text = new TextRange(LogBox.Document.ContentStart, LogBox.Document.ContentEnd).Text;
            if (!string.IsNullOrEmpty(text))
                System.Windows.Clipboard.SetText(text.TrimEnd('\r', '\n'));
        }
    }

    private void LogFilterBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (LogBox == null || DataContext is not ViewModels.MainViewModel vm) return;

        // Debounce: restart timer on each keystroke, only re-render after 200ms of inactivity.
        // This prevents lag when typing quickly in the filter box with a large log history.
        if (_logFilterDebounce == null)
        {
            _logFilterDebounce = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
            _logFilterDebounce.Tick += (s, args) =>
            {
                _logFilterDebounce.Stop();
                RebuildLogFromHistory();
            };
        }

        _logFilterDebounce.Stop();
        _logFilterDebounce.Start();
    }

    /// <summary>Re-renders the LogBox from _logHistory, applying the current filter.</summary>
    private void RebuildLogFromHistory()
    {
        if (LogBox == null || DataContext is not ViewModels.MainViewModel vm) return;
        LogBox.Document.Blocks.Clear();
        foreach (var entry in _logHistory)
        {
            if (FilterApplies(entry.Text))
                AppendLogEntry(entry);
        }
        LogBox.ScrollToEnd();
    }

    public void NavigateToBooks()
    {
        NavView.Navigate(typeof(BooksPage));
    }

    /// <summary>Enter in the titlebar search jumps to the books list and applies the query.</summary>
    private void GlobalSearch_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key != System.Windows.Input.Key.Enter) return;
        e.Handled = true;
        NavigateToBooks();
    }

    public void ShowSnackbar(string message, bool isError = false)
    {
        _snackbarService.Show(
            isError ? "Lỗi" : "Thành công",
            message,
            isError ? ControlAppearance.Danger : ControlAppearance.Success,
            isError
                ? new SymbolIcon { Symbol = SymbolRegular.ErrorCircle24 }
                : new SymbolIcon { Symbol = SymbolRegular.Checkmark24 },
            TimeSpan.FromSeconds(3));
    }

    private void Window_DragEnter(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            if (DragDropOverlay != null) DragDropOverlay.Visibility = Visibility.Visible;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
    }

    private void Window_DragLeave(object sender, DragEventArgs e)
    {
        if (DragDropOverlay != null) DragDropOverlay.Visibility = Visibility.Collapsed;
    }

    private void Window_Drop(object sender, DragEventArgs e)
    {
        if (DragDropOverlay != null) DragDropOverlay.Visibility = Visibility.Collapsed;

        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            var files = (string[]?)e.Data.GetData(DataFormats.FileDrop);
            if (files == null || files.Length == 0) return;

            var projectRoot = Services.ProjectHelper.FindProjectRoot();
            if (string.IsNullOrEmpty(projectRoot)) return;

            var chuaLamDir = System.IO.Path.Combine(projectRoot, "input", "chua-lam");
            System.IO.Directory.CreateDirectory(chuaLamDir);

            int copied = 0;
            foreach (var f in files)
            {
                var ext = System.IO.Path.GetExtension(f).ToLowerInvariant();
                if (ext is ".pdf" or ".epub" or ".docx" or ".txt")
                {
                    var dest = System.IO.Path.Combine(chuaLamDir, System.IO.Path.GetFileName(f));
                    try
                    {
                        System.IO.File.Copy(f, dest, overwrite: true);
                        copied++;
                    }
                    catch { }
                }
            }

            if (copied > 0)
            {
                NavigateToBooks();
                if (DataContext is ViewModels.MainViewModel vm)
                {
                    vm.LoadBooks();
                    vm.AppendLog($"📥 Đã thêm {copied} file sách mới vào input/chua-lam/ thành công!");
                }
                ShowSnackbar($"Đã thêm {copied} sách mới vào danh sách!");
            }
            else
            {
                ShowSnackbar("Vui lòng thả file sách định dạng .epub, .pdf hoặc .docx", true);
            }
        }
    }

    private void ApiStatusCard_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
            NavView.Navigate(typeof(ApiPage));
        }
    }
}