using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.ComponentModel;
using System.IO;
using TranslateBook.Models;

namespace TranslateBook.Views;

public partial class BooksPage : Page
{
    public BooksPage()
    {
        InitializeComponent();
    }

    private void Page_Loaded(object sender, RoutedEventArgs e)
    {
        if (DataContext == null)
            DataContext = Window.GetWindow(this)?.DataContext;

        if (DataContext is ViewModels.MainViewModel vm)
        {
            // Apply the titlebar global search query when this page (re)loads.
            if (!string.IsNullOrEmpty(vm.GlobalSearchQuery))
                ApplyGlobalSearch(vm.GlobalSearchQuery);

            // Ctrl+F: focus the search box.
            if (vm.FocusSearchRequested)
            {
                vm.FocusSearchRequested = false;
                Dispatcher.BeginInvoke(new Action(() => SearchBox.Focus()));
            }
        }
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        ApplySearchFilter(SearchBox.Text);
    }

    /// <summary>Called from the titlebar global search: sets the local filter.</summary>
    public void ApplyGlobalSearch(string query)
    {
        SearchBox.Text = query ?? "";
        ApplySearchFilter(query ?? "");
    }

    private void ApplySearchFilter(string text)
    {
        var searchText = (text ?? "").Trim().ToLower();

        if (InputItemsControl?.ItemsSource != null)
        {
            ICollectionView inputView = CollectionViewSource.GetDefaultView(InputItemsControl.ItemsSource);
            if (inputView != null)
                inputView.Filter = item => Matches(item, searchText);
        }

        if (OutputItemsControl?.ItemsSource != null)
        {
            ICollectionView outputView = CollectionViewSource.GetDefaultView(OutputItemsControl.ItemsSource);
            if (outputView != null)
                outputView.Filter = item => Matches(item, searchText);
        }
    }

    private static bool Matches(object item, string searchText)
    {
        if (string.IsNullOrEmpty(searchText)) return true;
        if (item is not BookStatus bs) return false;
        if (bs.Slug.ToLower().Contains(searchText)) return true;
        if (bs.DisplayTitle.ToLower().Contains(searchText)) return true;
        if (bs.Initial.ToLower() == searchText) return true;
        // Also match against the raw file name (keeps CJK/Vietnamese titles findable).
        if (!string.IsNullOrEmpty(bs.FilePath) &&
            System.IO.Path.GetFileName(bs.FilePath).ToLower().Contains(searchText)) return true;
        return false;
    }

    private void OpenInputFolder_Click(object sender, RoutedEventArgs e)
    {
        var projectRoot = Services.ProjectHelper.FindProjectRoot();
        if (string.IsNullOrEmpty(projectRoot)) return;
        var inputDir = Path.Combine(projectRoot, "input");
        Directory.CreateDirectory(inputDir);
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
        {
            FileName = inputDir,
            UseShellExecute = true
        });
    }

    private void TabInput_Click(object sender, RoutedEventArgs e)
    {
        if (OutputPanel != null) OutputPanel.Visibility = Visibility.Collapsed;
        if (InputPanel != null) AnimatePanelIn(InputPanel);
    }

    private void TabOutput_Click(object sender, RoutedEventArgs e)
    {
        if (InputPanel != null) InputPanel.Visibility = Visibility.Collapsed;
        if (OutputPanel != null) AnimatePanelIn(OutputPanel);
    }

    /// <summary>Fades the target panel in with a slight upward slide.</summary>
    private static void AnimatePanelIn(UIElement panel)
    {
        panel.Visibility = Visibility.Visible;
        panel.Opacity = 0;
        panel.RenderTransformOrigin = new Point(0.5, 0.5);
        panel.RenderTransform = new TranslateTransform(0, 12);

        var fade = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(180))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        var slide = new DoubleAnimation(12, 0, TimeSpan.FromMilliseconds(180))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        panel.BeginAnimation(OpacityProperty, fade);
        panel.RenderTransform.BeginAnimation(TranslateTransform.YProperty, slide);
    }

}