using System;
using System.Diagnostics;
using System.IO;
using System.Windows;
using Wpf.Ui.Appearance;

namespace TranslateBook;

public partial class App : Application
{
    private static readonly string LocalAppData = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "TranslateBook");

    public App()
    {
        Directory.CreateDirectory(LocalAppData);
        this.DispatcherUnhandledException += (s, e) =>
        {
            var logPath = Path.Combine(LocalAppData, "crash.log");
            File.AppendAllText(logPath, $"[UI Thread] {DateTime.Now}\n{e.Exception}\n\n");
            e.Handled = true;
            MessageBox.Show($"Đã xảy ra lỗi:\n{e.Exception.Message}", "Lỗi hệ thống", MessageBoxButton.OK, MessageBoxImage.Error);
        };
        AppDomain.CurrentDomain.UnhandledException += (s, e) =>
        {
            if (e.ExceptionObject is Exception ex)
            {
                var logPath = Path.Combine(LocalAppData, "crash.log");
                File.AppendAllText(logPath, $"[App Domain] {DateTime.Now}\n{ex}\n\n");
            }
        };
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        // Đồng bộ giao diện với theme hệ thống (dark/light) một lần.
        ApplicationThemeManager.ApplySystemTheme();
    }
}