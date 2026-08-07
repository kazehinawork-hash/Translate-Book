using System;
using System.Windows;
using System.Windows.Controls;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;

namespace TranslateBook.Views;

    public partial class MainWindow : FluentWindow
    {
        private readonly Wpf.Ui.SnackbarService _snackbarService = new();

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
        }

        private void MainWindow_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
        {
            // Kill any running Python processes when closing
            if (DataContext is ViewModels.MainViewModel vm)
            {
                vm.KillCurrentProcess();
            }
        }

    private void LogTextBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (sender is System.Windows.Controls.TextBox tb)
            tb.ScrollToEnd();
    }

    private void ClearLogButton_Click(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
            vm.LogText = "";
    }

    private void CopyLogButton_Click(object sender, RoutedEventArgs e)
    {
        if (LogBox != null && !string.IsNullOrEmpty(LogBox.Text))
            System.Windows.Clipboard.SetText(LogBox.Text);
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