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

    // ==================== 🧪 DEMO DỊCH THỬ (Luồng 2 - UI + API) ====================

    private void DemoEnVi_Click(object sender, RoutedEventArgs e) => LoadDemoFromButton(sender as System.Windows.Controls.Button, "English", "Vietnamese");
    private void DemoZhVi_Click(object sender, RoutedEventArgs e) => LoadDemoFromButton(sender as System.Windows.Controls.Button, "Chinese", "Vietnamese");
    private void DemoViEn_Click(object sender, RoutedEventArgs e) => LoadDemoFromButton(sender as System.Windows.Controls.Button, "Vietnamese", "English");

    /// <summary>Đổ text mẫu từ Tag của nút vào ô input, rồi gọi RunDemoTranslate.</summary>
    private void LoadDemoFromButton(System.Windows.Controls.Button? btn, string sourceLang, string targetLang)
    {
        if (btn?.Tag is string tag)
        {
            var parts = tag.Split('|', 2);
            if (parts.Length == 2) DemoSourceBox.Text = parts[1];
        }
        else
        {
            DemoSourceBox.Text = "Xin chào, hôm nay trời đẹp quá!";
        }
        _ = RunDemoTranslateAsync(sourceLang, targetLang);
    }

    private async Task RunDemoTranslateAsync(string sourceLang, string targetLang)
    {
        var text = DemoSourceBox.Text?.Trim() ?? "";
        if (string.IsNullOrEmpty(text))
        {
            DemoResultBox.Text = "(Vui lòng nhập text nguồn trước)";
            DemoStatsText.Text = "";
            return;
        }

        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? item.Content?.ToString() ?? "deepseek" : "deepseek";
        var model = ModelBox.Text?.Trim() ?? "";

        // Đảm bảo config được lưu trước khi gọi (để ApiTranslationService.TranslateAsync đọc được key mới nhất)
        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new ProviderConfig();
        if (!string.IsNullOrEmpty(ApiKeyBox.Password))
            cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        if (!string.IsNullOrEmpty(model))
            cfg.Providers[provider].Model = model;
        cfg.Providers[provider].BaseUrl = BaseUrlBox.Text?.Trim() ?? "";
        cfg.ActiveProvider = provider;
        Services.ConfigService.Save(cfg);

        DemoResultBox.Text = "⏳ Đang dịch...";
        DemoStatsText.Text = $"Đang gọi {provider} ({model})...";
        DemoStatsText.Foreground = Brushes.Yellow;

        var sw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            var service = new Services.ApiTranslationService();
            var result = await service.TranslateAsync(
                text, provider, glossary: "", context: "",
                sourceLang: sourceLang, targetLang: targetLang,
                trilingual: false);
            sw.Stop();

            DemoResultBox.Text = result.Text;
            DemoStatsText.Foreground = Brushes.LightGreen;
            DemoStatsText.Text = $"✅ {provider} / {result.Model} | {sw.ElapsedMilliseconds}ms" +
                                 $" | Token: {result.TokensIn} in / {result.TokensOut} out" +
                                 $" | {text.Length} ký tự gốc → {result.Text.Length} ký tự dịch";
        }
        catch (Exception ex)
        {
            sw.Stop();
            DemoResultBox.Text = $"❌ Lỗi: {ex.Message}";
            DemoStatsText.Foreground = Brushes.LightCoral;
            DemoStatsText.Text = $"❌ {provider} / {model} | {sw.ElapsedMilliseconds}ms | {ex.GetType().Name}";
        }
    }
}