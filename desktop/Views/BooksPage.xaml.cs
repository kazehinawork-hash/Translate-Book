using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Animation;
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