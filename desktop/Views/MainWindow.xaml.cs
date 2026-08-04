using System.Windows;
using System.Windows.Input;

namespace TranslateBook.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
            ToggleMaximize();
        else
            DragMove();
    }

    private void Minimize_Click(object sender, RoutedEventArgs e) =>
        WindowState = WindowState.Minimized;

    private void Maximize_Click(object sender, RoutedEventArgs e) =>
        ToggleMaximize();

    private void Close_Click(object sender, RoutedEventArgs e) =>
        Close();

    private void ToggleMaximize() =>
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal
            : WindowState.Maximized;

    private void Nav_Checked(object sender, RoutedEventArgs e)
    {
        if (BooksPage == null || AudioPage == null || ApiPage == null) return;

        BooksPage.Visibility = Visibility.Collapsed;
        AudioPage.Visibility = Visibility.Collapsed;
        ApiPage.Visibility = Visibility.Collapsed;

        if (NavBooks.IsChecked == true) BooksPage.Visibility = Visibility.Visible;
        else if (NavAudio.IsChecked == true) AudioPage.Visibility = Visibility.Visible;
        else if (NavApi.IsChecked == true) ApiPage.Visibility = Visibility.Visible;
    }

    private void TestApi_Click(object sender, RoutedEventArgs e)
    {
        var provider = (ProviderCombo.SelectedItem as System.Windows.Controls.ComboBoxItem)
            ?.Content?.ToString() ?? "deepseek";
        ApiStatus.Text = "Dang test...";
        ApiStatus.Foreground = System.Windows.Media.Brushes.Yellow;

        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var (ok, msg) = await service.TestConnectionAsync(provider);
            Dispatcher.Invoke(() =>
            {
                ApiStatus.Text = ok ? $"OK: {msg}" : $"Loi: {msg}";
                ApiStatus.Foreground = ok
                    ? System.Windows.Media.Brushes.LightGreen
                    : System.Windows.Media.Brushes.LightCoral;
            });
        });
    }
}
