using System;
using System.Globalization;
using System.Windows.Data;

namespace TranslateBook.Converters;

/// <summary>Converts a bool to a ✓/✗ emoji-ish glyph for stat tiles.</summary>
public class BoolToEmojiConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is true ? "✓" : "✗";

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
