using Microsoft.Win32;
using System;
using System.IO;
using System.Windows;

namespace TranslateBook;

public partial class App : Application
{
    public App()
    {
        InitializeTheme();
        SystemEvents.UserPreferenceChanged += (s, e) => {
            if (e.Category == UserPreferenceCategory.General)
                InitializeTheme();
        };

        this.DispatcherUnhandledException += (s, e) =>
        {
            File.AppendAllText("crash.log", $"[UI Thread] {DateTime.Now}\n{e.Exception}\n\n");
            e.Handled = true;
            MessageBox.Show($"Đã xảy ra lỗi:\n{e.Exception.Message}", "Lỗi hệ thống", MessageBoxButton.OK, MessageBoxImage.Error);
        };
        AppDomain.CurrentDomain.UnhandledException += (s, e) =>
        {
            if (e.ExceptionObject is Exception ex)
            {
                File.AppendAllText("crash.log", $"[App Domain] {DateTime.Now}\n{ex}\n\n");
            }
        };
    }

    private void InitializeTheme()
    {
        bool isLight = false;
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
            if (key?.GetValue("AppsUseLightTheme") is int val)
            {
                isLight = val > 0;
            }
        }
        catch { }

        string themeDict = isLight ? "Themes/LightTheme.xaml" : "Themes/DarkTheme.xaml";
        
        var dict = new ResourceDictionary { Source = new Uri(themeDict, UriKind.Relative) };
        
        // Cập nhật từ điển đầu tiên (do trong App.xaml ta để Theme ở index 0)
        if (Current.Resources.MergedDictionaries.Count > 0)
        {
            Current.Resources.MergedDictionaries[0] = dict;
        }
    }
}
