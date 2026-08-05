using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Threading.Tasks;
using System.Windows.Data;
using System.ComponentModel;
using System;
using TranslateBook.Models;

namespace TranslateBook.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        this.SourceInitialized += MainWindow_SourceInitialized;
    }

    private void MainWindow_SourceInitialized(object? sender, EventArgs e)
    {
        Services.AcrylicWindowHelper.EnableAcrylic(this);
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

        UIElement? targetPage = null;

        if (NavBooks.IsChecked == true) targetPage = BooksPage;
        else if (NavAudio.IsChecked == true) targetPage = AudioPage;
        else if (NavApi.IsChecked == true) targetPage = ApiPage;

        if (targetPage != null)
        {
            targetPage.Visibility = Visibility.Visible;
            targetPage.Opacity = 0;
            var anim = new DoubleAnimation(0, 1, TimeSpan.FromSeconds(0.25));
            targetPage.BeginAnimation(UIElement.OpacityProperty, anim);
        }
    }

    private void SearchBox_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
    {
        var searchText = SearchBox.Text.Trim().ToLower();

        if (InputItemsControl != null && InputItemsControl.ItemsSource != null)
        {
            ICollectionView inputView = CollectionViewSource.GetDefaultView(InputItemsControl.ItemsSource);
            if (inputView != null)
            {
                inputView.Filter = item =>
                {
                    if (string.IsNullOrEmpty(searchText)) return true;
                    if (item is BookStatus bs && !string.IsNullOrEmpty(bs.Slug))
                        return bs.Slug.ToLower().Contains(searchText);
                    return false;
                };
            }
        }

        if (OutputItemsControl != null && OutputItemsControl.ItemsSource != null)
        {
            ICollectionView outputView = CollectionViewSource.GetDefaultView(OutputItemsControl.ItemsSource);
            if (outputView != null)
            {
                outputView.Filter = item =>
                {
                    if (string.IsNullOrEmpty(searchText)) return true;
                    if (item is BookStatus bs && !string.IsNullOrEmpty(bs.Slug))
                        return bs.Slug.ToLower().Contains(searchText);
                    return false;
                };
            }
        }
    }

    private void ApiKeyBox_PasswordChanged(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.ApiKeyInput = ApiKeyBox.Password;
        }
    }

    private void LogTextBox_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
    {
        if (sender is System.Windows.Controls.TextBox textBox)
        {
            textBox.ScrollToEnd();
        }
    }

    private void TestApi_Click(object sender, RoutedEventArgs e)
    {
        var provider = (ProviderCombo.SelectedItem as System.Windows.Controls.ComboBoxItem)?.Content?.ToString() ?? "deepseek";
        
        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new Models.ProviderConfig();
            
        cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        cfg.Providers[provider].Model = ModelBox.Text;
        Services.ConfigService.Save(cfg);

        ApiStatus.Text = "Đang test...";
        ApiStatus.Foreground = System.Windows.Media.Brushes.Yellow;
        
        // Show Spinner
        ApiSpinner.Visibility = Visibility.Visible;
        var spinAnim = new DoubleAnimation(0, 360, TimeSpan.FromSeconds(1)) { RepeatBehavior = RepeatBehavior.Forever };
        ApiSpinnerRotate.BeginAnimation(RotateTransform.AngleProperty, spinAnim);

        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var (ok, msg) = await service.TestConnectionAsync(provider);
            Dispatcher.Invoke(() =>
            {
                // Hide Spinner
                ApiSpinnerRotate.BeginAnimation(RotateTransform.AngleProperty, null);
                ApiSpinner.Visibility = Visibility.Collapsed;

                ApiStatus.Text = ok ? $"OK: {msg}" : $"Lỗi: {msg}";
                ApiStatus.Foreground = ok
                    ? System.Windows.Media.Brushes.LightGreen
                    : System.Windows.Media.Brushes.LightCoral;
                
                ShowToast(ok ? "Kiểm tra kết nối thành công!" : "Lỗi kết nối API!", !ok);
            });
        });
    }

    private async void ShowToast(string message, bool isError = false)
    {
        ToastMessage.Text = message;
        ToastIcon.Text = isError ? "\uE783" : "\uE73E"; // Error icon or Check icon
        ToastIcon.Foreground = isError ? System.Windows.Media.Brushes.LightCoral : (System.Windows.Media.Brush)FindResource("PrimaryBrush");
        
        var animIn = new DoubleAnimation(0, -50, TimeSpan.FromSeconds(0.3)) { EasingFunction = new CircleEase { EasingMode = EasingMode.EaseOut } };
        ToastTransform.BeginAnimation(TranslateTransform.YProperty, animIn);

        await Task.Delay(3000);

        var animOut = new DoubleAnimation(-50, 50, TimeSpan.FromSeconds(0.3)) { EasingFunction = new CircleEase { EasingMode = EasingMode.EaseIn } };
        ToastTransform.BeginAnimation(TranslateTransform.YProperty, animOut);
    }

    private static string FindProjectRoot()
    {
        var dir = System.AppDomain.CurrentDomain.BaseDirectory;
        while (dir != null)
        {
            if (System.IO.File.Exists(System.IO.Path.Combine(dir, "TranslateBook.csproj")))
                return System.IO.Path.GetDirectoryName(dir)!;
            dir = System.IO.Path.GetDirectoryName(dir);
        }
        return System.AppDomain.CurrentDomain.BaseDirectory;
    }

    private void PreviewEpub_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button btn && btn.DataContext is Models.BookStatus book)
        {
            var projectRoot = FindProjectRoot();
            var epubPath = System.IO.Path.Combine(projectRoot, "output", "books", book.Slug, "trilingual.epub");
            
            if (System.IO.File.Exists(epubPath))
            {
                var previewWindow = new EpubPreviewWindow(epubPath) { Owner = this };
                previewWindow.Show();
            }
            else
            {
                ShowToast($"Không tìm thấy file EPUB", true);
            }
        }
    }
}
