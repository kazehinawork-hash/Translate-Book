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

    private void Page_Loaded(object sender, RoutedEventArgs e)
    {
        if (DataContext == null)
            DataContext = Window.GetWindow(this)?.DataContext;
    }

    private void ApiKeyBox_PasswordChanged(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.ApiKeyInput = ApiKeyBox.Password;
            if (!string.IsNullOrWhiteSpace(ApiKeyBox.Password) && ApiKeyBox.Password.Length > 10)
            {
                TriggerFetchModels();
            }
        }
    }

    private void FetchModels_Click(object sender, RoutedEventArgs e)
    {
        TriggerFetchModels(forceNotify: true);
    }

    private void TriggerFetchModels(bool forceNotify = false)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? item.Content?.ToString() ?? "deepseek" : "deepseek";
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

    private void TestApi_Click(object sender, RoutedEventArgs e)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? item.Content?.ToString() ?? "deepseek" : "deepseek";

        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new ProviderConfig();

        if (!string.IsNullOrEmpty(ApiKeyBox.Password))
            cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        cfg.Providers[provider].Model = ModelBox.Text?.Trim() ?? "";
        cfg.Providers[provider].BaseUrl = BaseUrlBox.Text?.Trim() ?? "";
        cfg.ActiveProvider = provider;
        Services.ConfigService.Save(cfg);

        ApiStatus.Text = "Đang kiểm tra...";
        ApiStatus.Foreground = Brushes.Yellow;

        // Quét cập nhật danh sách model
        TriggerFetchModels();

        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var (ok, msg) = await service.TestConnectionAsync(provider);
            Dispatcher.Invoke(() =>
            {
                ApiStatus.Text = ok ? $"OK: {msg}" : $"Lỗi: {msg}";
                ApiStatus.Foreground = ok ? Brushes.LightGreen : Brushes.LightCoral;
                if (Window.GetWindow(this) is MainWindow mw)
                    mw.ShowSnackbar(ok ? "Kiểm tra kết nối thành công!" : msg, !ok);
            });
        });
    }
}