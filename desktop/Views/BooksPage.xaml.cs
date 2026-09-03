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
        Unloaded += BooksPage_Unloaded;
    }

    private void BooksPage_Unloaded(object sender, RoutedEventArgs e)
    {
        ViewModels.MainViewModel.GlobalSearchQueryChanged -= OnGlobalSearchQueryChanged;
    }

    private void Page_Loaded(object sender, RoutedEventArgs e)
    {
        if (DataContext == null || DataContext is not ViewModels.MainViewModel)
        {
            var win = Window.GetWindow(this);
            if (win?.DataContext is ViewModels.MainViewModel winVm)
                DataContext = winVm;
            else if (Application.Current?.MainWindow?.DataContext is ViewModels.MainViewModel appVm)
                DataContext = appVm;
        }

        ViewModels.MainViewModel.GlobalSearchQueryChanged -= OnGlobalSearchQueryChanged;
        ViewModels.MainViewModel.GlobalSearchQueryChanged += OnGlobalSearchQueryChanged;

        if (DataContext is ViewModels.MainViewModel vm)
        {
            if (vm.InputBooks.Count == 0 && vm.OutputBooks.Count == 0)
            {
                vm.LoadBooks();
            }
            ApplySearchFilter(vm.GlobalSearchQuery ?? "");
        }
    }

    private void OnGlobalSearchQueryChanged(string query)
    {
        Dispatcher.Invoke(() => ApplySearchFilter(query));
    }

    /// <summary>Called from the titlebar global search: sets the local filter.</summary>
    public void ApplyGlobalSearch(string query)
    {
        ApplySearchFilter(query ?? "");
    }

    private void ApplySearchFilter(string text)
    {
        var searchText = (text ?? "").Trim().ToLower();

        if (InputItemsControl?.ItemsSource != null)
        {
            ICollectionView inputView = CollectionViewSource.GetDefaultView(InputItemsControl.ItemsSource);
            if (inputView != null)
            {
                if (string.IsNullOrEmpty(searchText))
                    inputView.Filter = null;
                else
                    inputView.Filter = item => Matches(item, searchText);
            }
        }

        if (OutputItemsControl?.ItemsSource != null)
        {
            ICollectionView outputView = CollectionViewSource.GetDefaultView(OutputItemsControl.ItemsSource);
            if (outputView != null)
            {
                if (string.IsNullOrEmpty(searchText))
                    outputView.Filter = null;
                else
                    outputView.Filter = item => Matches(item, searchText);
            }
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

    /// <summary>Khi mỗi ComboBox chương load, tải danh sách chapter cho sách tương ứng.
    /// Đặt trong BooksPage.xaml.cs để có thể truy cập DataContext Window.</summary>
    private void ChapterCombo_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is not System.Windows.Controls.ComboBox combo) return;
        // Lấy BookStatus từ DataContext của ComboBox (vì ComboBox nằm trong DataTemplate của BookStatus)
        if (combo.DataContext is not Models.BookStatus book) return;
        // Gọi LoadChapters qua ViewModel của Window
        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null && vm.LoadChaptersCommand.CanExecute(book))
        {
            vm.LoadChaptersCommand.Execute(book);
        }
    }

    private void SampleTranslate_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement el || el.DataContext is not Models.BookStatus book) return;
        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            _ = vm.SampleTranslateCommand.ExecuteAsync(book);
        }
    }

    private void PreviewInputBook_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement el || el.DataContext is not Models.BookStatus book) return;
        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            _ = vm.PreviewInputBookCommand.ExecuteAsync(book);
        }
    }

    private void RunPipeline_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement el || el.DataContext is not Models.BookStatus book) return;
        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            _ = vm.RunPipelineCommand.ExecuteAsync(book);
        }
    }

    private void RepairBook_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement el || el.DataContext is not Models.BookStatus book) return;
        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            _ = vm.RepairBookCommand.ExecuteAsync(book);
        }
    }

    private void ContextMenuPreview_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement fe) return;
        var book = fe.DataContext as Models.BookStatus;
        if (book == null && fe.Parent is ContextMenu cm && cm.PlacementTarget is FrameworkElement pt)
        {
            book = pt.DataContext as Models.BookStatus;
        }
        if (book == null) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            vm.PreviewTranslatedCommand.Execute(book);
        }
    }

    private void ContextMenuOpenFolder_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement fe) return;
        var book = fe.DataContext as Models.BookStatus;
        if (book == null && fe.Parent is ContextMenu cm && cm.PlacementTarget is FrameworkElement pt)
        {
            book = pt.DataContext as Models.BookStatus;
        }
        if (book == null) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            vm.OpenBookFolderCommand.Execute(book);
        }
    }

    private void ContextMenuCopyPath_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement fe) return;
        var book = fe.DataContext as Models.BookStatus;
        if (book == null && fe.Parent is ContextMenu cm && cm.PlacementTarget is FrameworkElement pt)
        {
            book = pt.DataContext as Models.BookStatus;
        }
        if (book == null) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            vm.CopyBookPathCommand.Execute(book);
        }
    }

    private void ContextMenuCleanCache_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement fe) return;
        var book = fe.DataContext as Models.BookStatus;
        if (book == null && fe.Parent is ContextMenu cm && cm.PlacementTarget is FrameworkElement pt)
        {
            book = pt.DataContext as Models.BookStatus;
        }
        if (book == null) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            vm.CleanBookCacheCommand.Execute(book);
        }
    }

    private void ContextMenuDeleteBook_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement fe) return;
        var book = fe.DataContext as Models.BookStatus;
        if (book == null && fe.Parent is ContextMenu cm && cm.PlacementTarget is FrameworkElement pt)
        {
            book = pt.DataContext as Models.BookStatus;
        }
        if (book == null) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm != null)
        {
            vm.DeleteBookCommand.Execute(book);
        }
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

    #region Drag & Drop Import Sách

    private void BooksPage_DragEnter(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            DragDropOverlay.Visibility = Visibility.Visible;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
        e.Handled = true;
    }

    private void BooksPage_DragOver(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
            if (DragDropOverlay.Visibility != Visibility.Visible)
                DragDropOverlay.Visibility = Visibility.Visible;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
        e.Handled = true;
    }

    private void BooksPage_DragLeave(object sender, DragEventArgs e)
    {
        DragDropOverlay.Visibility = Visibility.Collapsed;
        e.Handled = true;
    }

    private void BooksPage_Drop(object sender, DragEventArgs e)
    {
        DragDropOverlay.Visibility = Visibility.Collapsed;
        if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;

        var files = e.Data.GetData(DataFormats.FileDrop) as string[];
        if (files == null || files.Length == 0) return;

        var vm = DataContext as ViewModels.MainViewModel ?? Window.GetWindow(this)?.DataContext as ViewModels.MainViewModel;
        if (vm == null) return;

        var projectRoot = Services.ProjectHelper.FindProjectRoot();
        var targetDir = Path.Combine(projectRoot, "input", "chua-lam");
        if (!Directory.Exists(targetDir))
        {
            Directory.CreateDirectory(targetDir);
        }

        var validExts = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".pdf", ".epub", ".azw3", ".mobi", ".txt" };
        int importedCount = 0;

        foreach (var file in files)
        {
            if (!File.Exists(file)) continue;
            var ext = Path.GetExtension(file);
            if (!validExts.Contains(ext)) continue;

            var fileName = Path.GetFileName(file);
            var destPath = Path.Combine(targetDir, fileName);

            try
            {
                File.Copy(file, destPath, overwrite: true);
                importedCount++;
                vm.AppendLog($"[Thêm sách] Đã chép file vào input/chua-lam: {fileName}");
            }
            catch (Exception ex)
            {
                vm.AppendLog($"[Lỗi thêm sách] Không thể chép file {fileName}: {ex.Message}", "error");
            }
        }

        if (importedCount > 0)
        {
            vm.RefreshBooksCommand.Execute(null);
            vm.AppendLog($"✨ Đã thêm thành công {importedCount} file sách vào mục 'Chưa làm'!");
        }
    }

    #endregion
}