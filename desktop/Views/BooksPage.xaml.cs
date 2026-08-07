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

    private void TabInput_Click(object sender, RoutedEventArgs e)
    {
        if (InputPanel != null) InputPanel.Visibility = Visibility.Visible;
        if (OutputPanel != null) OutputPanel.Visibility = Visibility.Collapsed;
    }

    private void TabOutput_Click(object sender, RoutedEventArgs e)
    {
        if (InputPanel != null) InputPanel.Visibility = Visibility.Collapsed;
        if (OutputPanel != null) OutputPanel.Visibility = Visibility.Visible;
    }

}