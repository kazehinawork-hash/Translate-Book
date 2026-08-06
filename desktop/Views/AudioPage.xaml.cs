using System.Windows;
using System.Windows.Controls;

namespace TranslateBook.Views;

public partial class AudioPage : Page
{
    public AudioPage()
    {
        InitializeComponent();
    }

    private void Page_Loaded(object sender, RoutedEventArgs e)
    {
        if (DataContext == null)
            DataContext = Window.GetWindow(this)?.DataContext;
    }
}