using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;

namespace TranslateBook.Views
{
    public partial class MdPreviewWindow : FluentWindow
    {
        private string _mdFilePath = "";
        private string _rawViText = "";       // Nội dung bản dịch Việt
        private string _rawSrcText = "";      // Nội dung bản gốc (Hán/Anh) — nếu có
        private string _rawPinyinText = "";   // Pinyin (nếu có, sách Trung)
        private string _bookTitle = "";
        private string _bookSlug = "";

        public MdPreviewWindow(string mdFilePath = "", string bookTitle = "", string bookSlug = "")
        {
            InitializeComponent();
            SystemThemeWatcher.Watch(this, WindowBackdropType.Mica, true);
            _mdFilePath = mdFilePath;
            _bookTitle = bookTitle;
            _bookSlug = bookSlug;

            if (!string.IsNullOrEmpty(bookTitle))
                TitleBar.Title = $"Preview: {bookTitle}";

            Loaded += MdPreviewWindow_Loaded;
        }

        public void LoadMdFile(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("MD path cannot be empty.", nameof(path));
            _mdFilePath = path;
        }

        private async void MdPreviewWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                var userDataFolder = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "TranslateBook", "WebView2_Md");
                Directory.CreateDirectory(userDataFolder);

                // Set CreationProperties via reflection
                var webViewType = WebView.GetType();
                var cpProp = webViewType.GetProperty("CreationProperties");
                if (cpProp != null)
                {
                    var cp = Activator.CreateInstance(cpProp.PropertyType);
                    var udfProp = cpProp.PropertyType.GetProperty("UserDataFolder");
                    udfProp?.SetValue(cp, userDataFolder);
                    cpProp.SetValue(WebView, cp);
                }

                await WebView.EnsureCoreWebView2Async();
                var core = WebView.CoreWebView2;
                if (core == null)
                    throw new InvalidOperationException("Không thể khởi tạo WebView2.");

                // Đọc bản dịch Việt từ file .md preview
                if (File.Exists(_mdFilePath))
                {
                    _rawViText = File.ReadAllText(_mdFilePath);
                }

                // Source/pinyin sẽ được MainViewModel.SetSourceContent() gọi SAU khi window mở.
                // Mặc định render bản Việt trước.
                RenderMode("vi");
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Lỗi khi mở preview: {ex.Message}", "Lỗi",
                    System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        /// <summary>Được MainViewModel gọi để bổ sung source/pinyin từ progress JSON.</summary>
        public void SetSourceContent(string srcText, string pinyinText)
        {
            _rawSrcText = srcText ?? "";
            _rawPinyinText = pinyinText ?? "";
        }

        private void CmbMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (WebView?.CoreWebView2 == null) return;
            var tag = (CmbMode.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "vi";
            RenderMode(tag);
        }

        private void RenderMode(string mode)
        {
            string html;
            switch (mode)
            {
                case "src":
                    html = BuildHtml(!string.IsNullOrEmpty(_rawSrcText) ? _rawSrcText : _rawViText, "Bản gốc");
                    break;
                case "bi":
                    if (!string.IsNullOrEmpty(_rawSrcText))
                        html = BuildBilingualHtml(_rawSrcText, _rawViText);
                    else
                        html = BuildHtml(_rawViText, "Bản dịch (chưa có bản gốc để so sánh)");
                    break;
                case "tri":
                    if (!string.IsNullOrEmpty(_rawSrcText) && !string.IsNullOrEmpty(_rawPinyinText))
                        html = BuildTrilingualHtml(_rawSrcText, _rawPinyinText, _rawViText);
                    else
                        html = BuildHtml(_rawViText, "Bản dịch (chưa đủ dữ liệu tam ngữ)");
                    break;
                case "vi":
                default:
                    html = BuildHtml(_rawViText, "Bản dịch");
                    break;
            }
            WebView.CoreWebView2.NavigateToString(html);
        }

        // === HTML Render ===

        private string BuildEpubCss()
        {
            // Tái sử dụng cùng pattern dark theme như EpubPreviewWindow
            var bg = GetSafeColor("ControlFillColorTertiaryBrush", Color.FromRgb(0x1e, 0x1e, 0x1e), allowLight: false);
            var fg = GetSafeColor("TextFillColorPrimaryBrush", Color.FromRgb(0xe0, 0xe0, 0xe0), allowLight: true, maxLuminance: 240);
            var fgSecondary = GetSafeColor("TextFillColorSecondaryBrush", Color.FromRgb(0xb0, 0xb0, 0xb0), allowLight: true, maxLuminance: 200);
            var link = (Application.Current.Resources["AccentFillColorDefaultBrush"] as SolidColorBrush)?.Color ?? Color.FromRgb(0x60, 0xa5, 0xfa);
            var success = (Application.Current.Resources["SystemFillColorSuccessBrush"] as SolidColorBrush)?.Color ?? Color.FromRgb(0x6c, 0xc7, 0x6c);

            string bgHex = ColorToHex(bg);
            string fgHex = ColorToHex(fg);
            string fgSecondaryHex = ColorToHex(fgSecondary);
            string linkHex = ColorToHex(link);
            string successHex = ColorToHex(success);

            return $@"
                :root {{
                    --bg-color: {bgHex};
                    --fg-color: {fgHex};
                    --fg-secondary-color: {fgSecondaryHex};
                    --link-color: {linkHex};
                    --success-color: {successHex};
                    --font-size: 18px;
                    --font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
                    --line-height: 1.8;
                    --max-width: 800px;
                }}
                body {{
                    background-color: var(--bg-color);
                    color: var(--fg-color);
                    font-family: var(--font-family);
                    line-height: var(--line-height);
                    margin: 0 auto;
                    padding: 24px;
                    max-width: var(--max-width);
                    font-size: var(--font-size);
                    transition: max-width 0.2s ease, font-size 0.15s ease;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: var(--fg-color);
                    margin: 1.2em 0 0.5em 0;
                    line-height: 1.3;
                    font-weight: 600;
                }}
                h1 {{ font-size: calc(var(--font-size) * 1.8); }}
                h2 {{ font-size: calc(var(--font-size) * 1.5); }}
                h3 {{ font-size: calc(var(--font-size) * 1.3); }}
                p {{ margin: 0 0 1em 0; }}
                blockquote {{
                    margin: 1em 0;
                    padding: 0.5em 1.2em;
                    border-left: 3px solid var(--link-color);
                    background: rgba(128,128,128,0.08);
                    font-style: italic;
                    border-radius: 0 4px 4px 0;
                }}
                pre {{
                    background: rgba(0,0,0,0.1);
                    padding: 1em;
                    overflow-x: auto;
                    border-radius: 4px;
                    margin: 1em 0;
                }}
                code {{
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 0.9em;
                    padding: 0.1em 0.35em;
                    border-radius: 2px;
                    background: rgba(128,128,128,0.15);
                }}
                img {{ max-width: 100%; height: auto; display: block; margin: 1.5em auto; border-radius: 4px; }}
                hr {{ border: 0; border-top: 1px solid var(--fg-secondary-color); margin: 2em 0; }}
                .book-title {{
                    color: var(--link-color);
                    font-size: calc(var(--font-size) * 1.1);
                    font-weight: 600;
                    margin-bottom: 1.5em;
                    padding-bottom: 0.8em;
                    border-bottom: 1px dashed var(--fg-secondary-color);
                }}
                .tri-block {{
                    margin-bottom: 1.5em;
                    padding: 0.6em 0.8em;
                    border-left: 3px solid var(--link-color);
                    background: rgba(128,128,128,0.04);
                    border-radius: 0 4px 4px 0;
                }}
                .tri-block .src-zh {{
                    color: var(--fg-color);
                    margin: 0 0 0.2em 0;
                    font-weight: 500;
                }}
                .tri-block .pinyin {{
                    color: var(--success-color);
                    font-size: 0.88em;
                    font-style: italic;
                    margin: 0 0 0.4em 0;
                }}
                .tri-block .vi {{
                    color: var(--fg-color);
                    margin: 0;
                }}
                .bi-block {{
                    margin-bottom: 1.5em;
                    padding: 0.6em 0.8em;
                    border-left: 3px solid var(--link-color);
                    background: rgba(128,128,128,0.04);
                    border-radius: 0 4px 4px 0;
                }}
                .bi-block .src {{
                    color: var(--fg-secondary-color);
                    margin: 0 0 0.4em 0;
                }}
                .bi-block .vi {{
                    color: var(--fg-color);
                    margin: 0;
                }}
                .empty-notice {{
                    text-align: center;
                    padding: 3em 1em;
                    color: var(--fg-secondary-color);
                    font-style: italic;
                }}
                ::-webkit-scrollbar {{ width: 8px; }}
                ::-webkit-scrollbar-track {{ background: rgba(128,128,128,0.1); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb {{ background: rgba(128,128,128,0.3); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: rgba(128,128,128,0.5); }}
            ";
        }

        private string BuildHtml(string markdown, string modeLabel)
        {
            string css = BuildEpubCss();
            var body = new StringBuilder();
            body.AppendLine($"<div class='book-title'>📖 {EscapeHtml(_bookTitle)} — {EscapeHtml(modeLabel)}</div>");

            if (string.IsNullOrWhiteSpace(markdown))
            {
                body.AppendLine("<div class='empty-notice'>Chưa có nội dung.</div>");
            }
            else
            {
                body.AppendLine(MarkdownToHtml(markdown));
            }

            return $@"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Preview</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>";
        }

        private string BuildBilingualHtml(string srcMd, string viMd)
        {
            string css = BuildEpubCss();
            var body = new StringBuilder();
            body.AppendLine($"<div class='book-title'>📖 {EscapeHtml(_bookTitle)} — Song ngữ (Gốc + Việt)</div>");

            // Group thành block: mỗi heading là 1 block, các paragraph tiếp theo cùng block
            var srcBlocks = SplitIntoBlocks(srcMd);
            var viBlocks = SplitIntoBlocks(viMd);

            int n = Math.Max(srcBlocks.Count, viBlocks.Count);
            for (int i = 0; i < n; i++)
            {
                string s = i < srcBlocks.Count ? srcBlocks[i] : "";
                string v = i < viBlocks.Count ? viBlocks[i] : "";
                if (string.IsNullOrWhiteSpace(s) && string.IsNullOrWhiteSpace(v)) continue;

                body.AppendLine("<div class='bi-block'>");
                if (!string.IsNullOrWhiteSpace(s))
                {
                    body.AppendLine("<div class='src'>");
                    body.AppendLine(MarkdownToHtml(s));
                    body.AppendLine("</div>");
                }
                if (!string.IsNullOrWhiteSpace(v))
                {
                    body.AppendLine("<div class='vi'>");
                    body.AppendLine(MarkdownToHtml(v));
                    body.AppendLine("</div>");
                }
                body.AppendLine("</div>");
            }

            return $@"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Preview</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>";
        }

        private string BuildTrilingualHtml(string srcMd, string pinyinMd, string viMd)
        {
            string css = BuildEpubCss();
            var body = new StringBuilder();
            body.AppendLine($"<div class='book-title'>📖 {EscapeHtml(_bookTitle)} — Tam ngữ (Gốc + Pinyin + Việt)</div>");

            var srcBlocks = SplitIntoBlocks(srcMd);
            var pinBlocks = SplitIntoBlocks(pinyinMd);
            var viBlocks = SplitIntoBlocks(viMd);

            int n = Math.Max(srcBlocks.Count, Math.Max(pinBlocks.Count, viBlocks.Count));
            for (int i = 0; i < n; i++)
            {
                string s = i < srcBlocks.Count ? srcBlocks[i] : "";
                string p = i < pinBlocks.Count ? pinBlocks[i] : "";
                string v = i < viBlocks.Count ? viBlocks[i] : "";
                if (string.IsNullOrWhiteSpace(s) && string.IsNullOrWhiteSpace(p) && string.IsNullOrWhiteSpace(v)) continue;

                body.AppendLine("<div class='tri-block'>");
                if (!string.IsNullOrWhiteSpace(s))
                {
                    body.AppendLine("<div class='src-zh'>");
                    body.AppendLine(MarkdownToHtml(s));
                    body.AppendLine("</div>");
                }
                if (!string.IsNullOrWhiteSpace(p))
                {
                    body.AppendLine("<div class='pinyin'>");
                    body.AppendLine(MarkdownToHtml(p));
                    body.AppendLine("</div>");
                }
                if (!string.IsNullOrWhiteSpace(v))
                {
                    body.AppendLine("<div class='vi'>");
                    body.AppendLine(MarkdownToHtml(v));
                    body.AppendLine("</div>");
                }
                body.AppendLine("</div>");
            }

            return $@"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Preview</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>";
        }

        /// <summary>Tách markdown thành các block theo heading (paragraph-level).</summary>
        private static System.Collections.Generic.List<string> SplitIntoBlocks(string md)
        {
            var result = new System.Collections.Generic.List<string>();
            if (string.IsNullOrWhiteSpace(md)) return result;

            var lines = md.Split('\n');
            var current = new StringBuilder();
            foreach (var line in lines)
            {
                var trimmed = line.TrimEnd();
                // Heading mới → flush block cũ
                if (Regex.IsMatch(trimmed, @"^#{1,6}\s") && current.Length > 0)
                {
                    result.Add(current.ToString().Trim());
                    current.Clear();
                }
                current.AppendLine(trimmed);
            }
            if (current.Length > 0) result.Add(current.ToString().Trim());

            return result;
        }

        /// <summary>Markdown rất đơn giản → HTML. Hỗ trợ: # heading, **bold**, *italic*, code, link, image, paragraph.</summary>
        private static string MarkdownToHtml(string md)
        {
            if (string.IsNullOrWhiteSpace(md)) return "";

            var sb = new StringBuilder();
            var lines = md.Split('\n');
            bool inParagraph = false;
            var paragraphBuf = new StringBuilder();
            bool inCodeBlock = false;
            var codeBuf = new StringBuilder();

            void FlushParagraph()
            {
                if (paragraphBuf.Length > 0)
                {
                    sb.AppendLine($"<p>{InlineMarkdown(paragraphBuf.ToString().Trim())}</p>");
                    paragraphBuf.Clear();
                }
                inParagraph = false;
            }

            foreach (var rawLine in lines)
            {
                var line = rawLine.TrimEnd();

                // Code block
                if (line.TrimStart().StartsWith("```"))
                {
                    if (inCodeBlock)
                    {
                        sb.AppendLine($"<pre><code>{EscapeHtml(codeBuf.ToString())}</code></pre>");
                        codeBuf.Clear();
                        inCodeBlock = false;
                    }
                    else
                    {
                        FlushParagraph();
                        inCodeBlock = true;
                    }
                    continue;
                }
                if (inCodeBlock)
                {
                    codeBuf.AppendLine(line);
                    continue;
                }

                // Empty line → paragraph break
                if (string.IsNullOrWhiteSpace(line))
                {
                    FlushParagraph();
                    continue;
                }

                // Heading
                var headingMatch = Regex.Match(line, @"^(#{1,6})\s+(.*)$");
                if (headingMatch.Success)
                {
                    FlushParagraph();
                    int level = headingMatch.Groups[1].Value.Length;
                    var text = headingMatch.Groups[2].Value.Trim();
                    sb.AppendLine($"<h{level}>{InlineMarkdown(text)}</h{level}>");
                    continue;
                }

                // Image
                var imgMatch = Regex.Match(line, @"^!\[([^\]]*)\]\(([^)]+)\)\s*$");
                if (imgMatch.Success)
                {
                    FlushParagraph();
                    var alt = EscapeHtml(imgMatch.Groups[1].Value);
                    var src = EscapeHtml(imgMatch.Groups[2].Value);
                    sb.AppendLine($"<img src='{src}' alt='{alt}' />");
                    continue;
                }

                // Horizontal rule
                if (Regex.IsMatch(line.Trim(), @"^[-*_]{3,}$"))
                {
                    FlushParagraph();
                    sb.AppendLine("<hr/>");
                    continue;
                }

                // Blockquote
                if (line.TrimStart().StartsWith(">"))
                {
                    FlushParagraph();
                    var bq = Regex.Replace(line.TrimStart(), @"^>\s*", "");
                    sb.AppendLine($"<blockquote>{InlineMarkdown(bq)}</blockquote>");
                    continue;
                }

                // Default: paragraph text
                if (inParagraph) paragraphBuf.Append(' ');
                paragraphBuf.Append(line.Trim());
                inParagraph = true;
            }

            if (inCodeBlock && codeBuf.Length > 0)
            {
                sb.AppendLine($"<pre><code>{EscapeHtml(codeBuf.ToString())}</code></pre>");
            }
            FlushParagraph();

            return sb.ToString();
        }

        private static string InlineMarkdown(string text)
        {
            if (string.IsNullOrEmpty(text)) return "";
            text = EscapeHtml(text);
            // Bold **text**
            text = Regex.Replace(text, @"\*\*([^*]+)\*\*", "<strong>$1</strong>");
            // Italic *text* (không xung đột với bold)
            text = Regex.Replace(text, @"(?<!\*)\*([^*]+)\*(?!\*)", "<em>$1</em>");
            // Inline code `text`
            text = Regex.Replace(text, @"`([^`]+)`", "<code>$1</code>");
            // Link [text](url)
            text = Regex.Replace(text, @"\[([^\]]+)\]\(([^)]+)\)", "<a href='$2' target='_blank'>$1</a>");
            return text;
        }

        private static string EscapeHtml(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;").Replace("'", "&#39;");
        }

        // === Theme helpers (giống EpubPreviewWindow) ===

        private static Color GetSafeColor(string resourceKey, Color fallback, bool allowLight, double maxLuminance = 255)
        {
            try
            {
                if (Application.Current.Resources[resourceKey] is SolidColorBrush brush)
                {
                    var c = brush.Color;
                    if (c.A < 0x40) return fallback;
                    double lum = (0.299 * c.R + 0.587 * c.G + 0.114 * c.B);
                    if (!allowLight && lum > 128) return fallback;
                    if (allowLight && lum > maxLuminance) return fallback;
                    return c;
                }
            }
            catch { }
            return fallback;
        }

        private static string ColorToHex(Color color) =>
            "#" + color.R.ToString("X2") + color.G.ToString("X2") + color.B.ToString("X2");

        // === Zoom / Typography / Theme ===

        private void WebView_NavigationCompleted(object sender, Microsoft.Web.WebView2.Core.CoreWebView2NavigationCompletedEventArgs e)
        {
            if (e.IsSuccess)
            {
                ReapplyThemeColors();
                ApplyTypographySettings();
            }
        }

        private void ApplyTypographySettings()
        {
            if (WebView?.CoreWebView2 == null) return;
            string fontTag = (CmbFont?.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "'Segoe UI', 'Microsoft YaHei', Arial, sans-serif";
            string widthTag = (CmbWidth?.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "800px";
            string lineHeightTag = (CmbLineHeight?.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "1.8";
            string js = $@"
                var root = document.documentElement;
                root.style.setProperty('--font-family', ""{fontTag}"");
                root.style.setProperty('--max-width', ""{widthTag}"");
                root.style.setProperty('--line-height', ""{lineHeightTag}"");
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void CmbFont_SelectionChanged(object sender, SelectionChangedEventArgs e) => ApplyTypographySettings();
        private void CmbWidth_SelectionChanged(object sender, SelectionChangedEventArgs e) => ApplyTypographySettings();
        private void CmbLineHeight_SelectionChanged(object sender, SelectionChangedEventArgs e) => ApplyTypographySettings();

        private void ReapplyThemeColors()
        {
            if (WebView?.CoreWebView2 == null) return;
            var bg = GetSafeColor("ControlFillColorTertiaryBrush", Color.FromRgb(0x1e, 0x1e, 0x1e), allowLight: false);
            var fg = GetSafeColor("TextFillColorPrimaryBrush", Color.FromRgb(0xe0, 0xe0, 0xe0), allowLight: true, maxLuminance: 240);
            var link = (Application.Current.Resources["AccentFillColorDefaultBrush"] as SolidColorBrush)?.Color ?? Color.FromRgb(0x60, 0xa5, 0xfa);
            string bgHex = ColorToHex(bg);
            string fgHex = ColorToHex(fg);
            string linkHex = ColorToHex(link);
            string js = $@"var root = document.documentElement; root.style.setProperty('--bg-color', '{bgHex}'); root.style.setProperty('--fg-color', '{fgHex}'); root.style.setProperty('--link-color', '{linkHex}');";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void ZoomSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            int percent = (int)e.NewValue;
            if (ZoomPercent != null) ZoomPercent.Text = $"{percent}%";
            if (WebView?.CoreWebView2 != null)
            {
                double fontSize = 18.0 * (percent / 100.0);
                string js = $"document.documentElement.style.setProperty('--font-size', '{fontSize:F1}px');";
                WebView.CoreWebView2.ExecuteScriptAsync(js);
            }
        }

        private void BtnRefreshTheme_Click(object sender, RoutedEventArgs e)
        {
            var core = WebView?.CoreWebView2;
            if (core == null) return;
            if (core.Source != null) core.Reload();
            else ReapplyThemeColors();
        }

        private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.F5)
            {
                ReapplyThemeColors();
                ZoomPercent.Text = $"{(int)ZoomSlider.Value}%";
                e.Handled = true;
            }
        }
    }
}
