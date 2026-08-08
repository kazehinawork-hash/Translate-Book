using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;

namespace TranslateBook.Views;

    public partial class MainWindow : FluentWindow
    {
        private readonly Wpf.Ui.SnackbarService _snackbarService = new();
        private readonly List<ViewModels.MainViewModel.LogEntry> _logHistory = new();

        public MainWindow()
        {
            InitializeComponent();
            SystemThemeWatcher.Watch(this, WindowBackdropType.Mica, true);
            _snackbarService.SetSnackbarPresenter(SnackbarPresenter);
            Loaded += MainWindow_Loaded;
            Closing += MainWindow_Closing;
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
            }
        }

        private void OnLogEntryAdded(ViewModels.MainViewModel.LogEntry entry)
        {
            _logHistory.Add(entry);
            if (_logHistory.Count > 2000)
                _logHistory.RemoveAt(0);
            if (FilterApplies(entry.Text))
                AppendLogEntry(entry);
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
            var brush = entry.Level switch
            {
                "error" => (Brush)new SolidColorBrush(Color.FromRgb(0xff, 0x6b, 0x6b)),
                "warning" => (Brush)new SolidColorBrush(Color.FromRgb(0xff, 0xc9, 0x4d)),
                _ => (Brush)new SolidColorBrush(Color.FromRgb(0xb0, 0xb0, 0xb0))
            };
            var para = new Paragraph(new Run(entry.Text + "\n")) { Foreground = brush };
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

    private void LogTextBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (sender is System.Windows.Controls.RichTextBox tb)
            tb.ScrollToEnd();
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
        // Re-render from history so only matching lines are shown (colored).
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
}