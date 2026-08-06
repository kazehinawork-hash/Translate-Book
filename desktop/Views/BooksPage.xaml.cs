using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.ComponentModel;
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
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        var searchText = SearchBox.Text.Trim().ToLower();

        if (InputItemsControl?.ItemsSource != null)
        {
            ICollectionView inputView = CollectionViewSource.GetDefaultView(InputItemsControl.ItemsSource);
            if (inputView != null)
                inputView.Filter = item =>
                    string.IsNullOrEmpty(searchText) ||
                    item is BookStatus bs && !string.IsNullOrEmpty(bs.Slug) && bs.Slug.ToLower().Contains(searchText);
        }

        if (OutputItemsControl?.ItemsSource != null)
        {
            ICollectionView outputView = CollectionViewSource.GetDefaultView(OutputItemsControl.ItemsSource);
            if (outputView != null)
                outputView.Filter = item =>
                    string.IsNullOrEmpty(searchText) ||
                    item is BookStatus bs && !string.IsNullOrEmpty(bs.Slug) && bs.Slug.ToLower().Contains(searchText);
        }
    }

    private void PreviewEpub_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button btn && btn.DataContext is BookStatus book)
        {
            var projectRoot = Services.ProjectHelper.FindProjectRoot();
            var epubPath = System.IO.Path.Combine(projectRoot, "output", "books", book.Slug, "trilingual.epub");

            if (System.IO.File.Exists(epubPath))
            {
                var previewWindow = new EpubPreviewWindow(epubPath) { Owner = Window.GetWindow(this) };
                previewWindow.Show();
            }
            else
            {
                if (Window.GetWindow(this) is MainWindow mw)
                    mw.ShowSnackbar($"Không tìm thấy file EPUB", true);
            }
        }
    }
}