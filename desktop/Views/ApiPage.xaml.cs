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
            vm.ApiKeyInput = ApiKeyBox.Password;
    }

    private void TestApi_Click(object sender, RoutedEventArgs e)
    {
        var provider = ProviderCombo.SelectedItem is ComboBoxItem item ? item.Content?.ToString() ?? "deepseek" : "deepseek";

        var cfg = Services.ConfigService.Load();
        if (!cfg.Providers.ContainsKey(provider))
            cfg.Providers[provider] = new ProviderConfig();

        if (!string.IsNullOrEmpty(ApiKeyBox.Password))
            cfg.Providers[provider].ApiKey = ApiKeyBox.Password;
        cfg.Providers[provider].Model = ModelBox.Text;
        cfg.Providers[provider].BaseUrl = BaseUrlBox.Text;
        Services.ConfigService.Save(cfg);

        ApiStatus.Text = "Đang test...";
        ApiStatus.Foreground = Brushes.Yellow;

        _ = Task.Run(async () =>
        {
            var service = new Services.ApiTranslationService();
            var (ok, msg) = await service.TestConnectionAsync(provider);
            Dispatcher.Invoke(() =>
            {
                ApiStatus.Text = ok ? $"OK: {msg}" : $"Lỗi: {msg}";
                ApiStatus.Foreground = ok ? Brushes.LightGreen : Brushes.LightCoral;
                if (Window.GetWindow(this) is MainWindow mw)
                    mw.ShowSnackbar(ok ? "Kiểm tra kết nối thành công!" : "Lỗi kết nối API!", !ok);
            });
        });
    }
}