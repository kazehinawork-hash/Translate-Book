using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using TranslateBook.Models;

namespace TranslateBook.Views;

public partial class ApiPage : Page
{
    public ApiPage()
    {
        InitializeComponent();
    }

    private bool _isUpdatingKeyProgrammatically = false;
    private bool _isApiKeyPlainVisible = false;

    private void Page_Loaded(object sender, RoutedEventArgs e)
    {
        if (DataContext == null)
            DataContext = Window.GetWindow(this)?.DataContext;

        LoadCurrentProviderKey();
    }

    private void ProviderCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        LoadCurrentProviderKey();
    }

    private void LoadCurrentProviderKey()
    {
        var provider = ProviderCombo?.SelectedItem is ComboBoxItem item ? (item.Tag?.ToString() ?? item.Content?.ToString() ?? "gemini").ToLowerInvariant() : "gemini";
        var cfg = Services.ConfigService.GetProvider(provider);
        var key = cfg?.ApiKey ?? "";

        _isUpdatingKeyProgrammatically = true;
        try
        {
            if (ApiKeyBox != null) ApiKeyBox.Password = key;
            if (ApiKeyPlainBox != null) ApiKeyPlainBox.Text = key;

            if (KeyStatusText != null)
            {
                if (!string.IsNullOrWhiteSpace(key))
                {
                    KeyStatusText.Text = "● Đã lưu API key (đang được mã hóa bảo mật). Nhập key mới nếu muốn thay đổi.";
                    KeyStatusText.Foreground = (Brush)FindResource("AccentFillColorDefaultBrush");
                }
                else
                {
                    KeyStatusText.Text = "Chưa có API key. Vui lòng nhập mã truy cập của bạn.";
                    KeyStatusText.Foreground = (Brush)FindResource("TextFillColorSecondaryBrush");
                }
            }
        }
        finally
        {
            _isUpdatingKeyProgrammatically = false;
        }
    }

    private void ToggleApiKeyVisibility_Click(object sender, RoutedEventArgs e)
    {
        _isApiKeyPlainVisible = !_isApiKeyPlainVisible;
        if (_isApiKeyPlainVisible)
        {
            ApiKeyPlainBox.Text = ApiKeyBox.Password;
            ApiKeyPlainBox.Visibility = Visibility.Visible;
            ApiKeyBox.Visibility = Visibility.Collapsed;
            EyeIcon.Symbol = Wpf.Ui.Controls.SymbolRegular.EyeOff24;
            ApiKeyPlainBox.Focus();
            ApiKeyPlainBox.CaretIndex = ApiKeyPlainBox.Text.Length;
        }
        else
        {
            ApiKeyBox.Password = ApiKeyPlainBox.Text;
            ApiKeyBox.Visibility = Visibility.Visible;
            ApiKeyPlainBox.Visibility = Visibility.Collapsed;
            EyeIcon.Symbol = Wpf.Ui.Controls.SymbolRegular.Eye24;
            ApiKeyBox.Focus();
        }
    }

    private void ApiKeyPlainBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (_isUpdatingKeyProgrammatically) return;

        _isUpdatingKeyProgrammatically = true;
        try
        {
            ApiKeyBox.Password = ApiKeyPlainBox.Text;
        }
        finally
        {
            _isUpdatingKeyProgrammatically = false;
        }

        OnApiKeyUpdated(ApiKeyPlainBox.Text);
    }

    private void ApiKeyBox_PasswordChanged(object sender, RoutedEventArgs e)
    {
        if (_isUpdatingKeyProgrammatically) return;

        _isUpdatingKeyProgrammatically = true;
        try
        {
            ApiKeyPlainBox.Text = ApiKeyBox.Password;
        }
        finally
        {
            _isUpdatingKeyProgrammatically = false;
        }

        OnApiKeyUpdated(ApiKeyBox.Password);
    }

    private void OnApiKeyUpdated(string key)
    {
        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.ApiKeyInput = key;
            if (!string.IsNullOrWhiteSpace(key) && key.Length > 10)
            {
                TriggerFetchModels();
            }
        }

        if (KeyStatusText != null)
        {
            if (!string.IsNullOrWhiteSpace(key))
            {
                KeyStatusText.Text = "● Đã nhập API key. Bấm 'Lưu Cài Đặt' hoặc 'Kiểm Tra Kết Nối' để áp dụng.";
                KeyStatusText.Foreground = (Brush)FindResource("AccentFillColorDefaultBrush");
            }
            else
            {
                KeyStatusText.Text = "Chưa có API key. Vui lòng nhập mã truy cập của bạn.";
                KeyStatusText.Foreground = (Brush)FindResource("TextFillColorSecondaryBrush");
            }
        }
    }

    private void FetchModels_Click(object sender, RoutedEventArgs e)
    {
        TriggerFetchModels(forceNotify: true);
    }

    private void TriggerFetchModels(bool forceNotify = false)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? (item.Tag?.ToString() ?? item.Content?.ToString() ?? "gemini").ToLowerInvariant() : "gemini";
        var key = ApiKeyBox.Password;
        if (string.IsNullOrWhiteSpace(key))
        {
            var cfg = Services.ConfigService.GetProvider(provider);
            key = cfg?.ApiKey ?? "";
        }
        if (string.IsNullOrWhiteSpace(key))
        {
            if (forceNotify && Window.GetWindow(this) is MainWindow mw)
                mw.ShowSnackbar("Vui lòng nhập API key trước khi quét danh sách Model!", true);
            return;
        }

        var baseUrl = BaseUrlBox.Text;

        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var models = await service.FetchAvailableModelsAsync(provider, key, baseUrl);
            if (models.Count > 0)
            {
                Dispatcher.Invoke(() =>
                {
                    if (DataContext is ViewModels.MainViewModel vm)
                    {
                        var userSelected = ModelBox.Text?.Trim();
                        if (string.IsNullOrWhiteSpace(userSelected))
                            userSelected = vm.ModelInput?.Trim();

                        vm.AvailableModels.Clear();
                        foreach (var m in models) vm.AvailableModels.Add(m);

                        // Ưu tiên giữ đúng model người dùng đang chọn
                        if (!string.IsNullOrWhiteSpace(userSelected) && models.Contains(userSelected))
                        {
                            vm.ModelInput = userSelected;
                            ModelBox.Text = userSelected;
                        }
                        else if (models.Contains("gemini-3.6-flash"))
                        {
                            vm.ModelInput = "gemini-3.6-flash";
                            ModelBox.Text = "gemini-3.6-flash";
                        }
                        else if (!string.IsNullOrWhiteSpace(userSelected))
                        {
                            vm.ModelInput = userSelected;
                            ModelBox.Text = userSelected;
                        }
                        else
                        {
                            vm.ModelInput = models[0];
                            ModelBox.Text = models[0];
                        }

                        if (forceNotify && Window.GetWindow(this) is MainWindow mw)
                            mw.ShowSnackbar($"Đã quét thành công {models.Count} model từ API!", false);
                    }
                });
            }
            else if (forceNotify)
            {
                Dispatcher.Invoke(() =>
                {
                    if (Window.GetWindow(this) is MainWindow mw)
                        mw.ShowSnackbar("Không thể lấy danh sách Model từ API key này.", true);
                });
            }
        });
    }

    private void SaveConfig_Click(object sender, RoutedEventArgs e)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? (item.Tag?.ToString() ?? item.Content?.ToString() ?? "gemini").ToLowerInvariant() : "gemini";

        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new ProviderConfig();

        if (!string.IsNullOrEmpty(ApiKeyBox.Password))
            cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        cfg.Providers[provider].Model = ModelBox.Text?.Trim() ?? "";
        cfg.Providers[provider].BaseUrl = BaseUrlBox.Text?.Trim() ?? "";
        cfg.ActiveProvider = provider;
        Services.ConfigService.Save(cfg);

        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.ActiveProvider = provider;
            vm.SelectedProvider = provider;
        }

        LoadCurrentProviderKey();

        if (Window.GetWindow(this) is MainWindow mw)
            mw.ShowSnackbar($"Đã lưu cấu hình API {provider.ToUpper()} thành công!", false);

        TriggerFetchModels();
    }

    private void TestApi_Click(object sender, RoutedEventArgs e)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? (item.Tag?.ToString() ?? item.Content?.ToString() ?? "gemini").ToLowerInvariant() : "gemini";

        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new ProviderConfig();

        if (!string.IsNullOrEmpty(ApiKeyBox.Password))
            cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        cfg.Providers[provider].Model = ModelBox.Text?.Trim() ?? "";
        cfg.Providers[provider].BaseUrl = BaseUrlBox.Text?.Trim() ?? "";
        cfg.ActiveProvider = provider;
        Services.ConfigService.Save(cfg);

        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.ActiveProvider = provider;
            vm.SelectedProvider = provider;
        }

        LoadCurrentProviderKey();

        ApiStatus.Text = "Đang kiểm tra...";
        ApiStatus.Foreground = (Brush)FindResource("TextFillColorSecondaryBrush");
        ApiStatusIcon.Symbol = Wpf.Ui.Controls.SymbolRegular.ArrowSync24;
        ApiStatusIcon.Foreground = (Brush)FindResource("AccentFillColorDefaultBrush");

        StatusDot.Background = (Brush)FindResource("AccentFillColorDefaultBrush");
        OverallStatusText.Text = "Đang kiểm tra...";

        // Quét cập nhật danh sách model
        TriggerFetchModels();

        var sw = System.Diagnostics.Stopwatch.StartNew();
        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var (ok, msg) = await service.TestConnectionAsync(provider);
            sw.Stop();
            var elapsedMs = sw.ElapsedMilliseconds;

            Dispatcher.Invoke(() =>
            {
                if (ok)
                {
                    ApiStatus.Text = $"Kết nối tốt ({elapsedMs}ms) • {msg}";
                    ApiStatus.Foreground = new SolidColorBrush(Color.FromRgb(0x00, 0xE6, 0x76));
                    ApiStatusIcon.Symbol = Wpf.Ui.Controls.SymbolRegular.CheckmarkCircle24;
                    ApiStatusIcon.Foreground = new SolidColorBrush(Color.FromRgb(0x00, 0xE6, 0x76));

                    StatusDot.Background = new SolidColorBrush(Color.FromRgb(0x00, 0xE6, 0x76));
                    OverallStatusText.Text = $"Sẵn sàng ({elapsedMs}ms)";
                    OverallStatusText.Foreground = new SolidColorBrush(Color.FromRgb(0x00, 0xE6, 0x76));
                }
                else
                {
                    ApiStatus.Text = $"Lỗi ({elapsedMs}ms): {msg}";
                    ApiStatus.Foreground = new SolidColorBrush(Color.FromRgb(0xFF, 0x52, 0x52));
                    ApiStatusIcon.Symbol = Wpf.Ui.Controls.SymbolRegular.DismissCircle24;
                    ApiStatusIcon.Foreground = new SolidColorBrush(Color.FromRgb(0xFF, 0x52, 0x52));

                    StatusDot.Background = new SolidColorBrush(Color.FromRgb(0xFF, 0x52, 0x52));
                    OverallStatusText.Text = "Không khả dụng";
                    OverallStatusText.Foreground = new SolidColorBrush(Color.FromRgb(0xFF, 0x52, 0x52));
                }

                if (Window.GetWindow(this) is MainWindow mw)
                    mw.ShowSnackbar(ok ? $"Kiểm tra kết nối thành công ({elapsedMs}ms)!" : msg, !ok);
            });
        });
    }
}