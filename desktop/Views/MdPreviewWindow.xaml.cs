using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
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
    public class MdTocItem
    {
        public string Title { get; set; } = "";
        public string AnchorId { get; set; } = "";
        public int Level { get; set; } = 1;
        public ObservableCollection<MdTocItem> NestedItems { get; set; } = new();
    }

    public partial class MdPreviewWindow : FluentWindow
    {
        private string _mdFilePath = "";
        private string _rawViText = "";       // Nội dung bản dịch Việt
        private string _rawSrcText = "";      // Nội dung bản gốc (Hán/Anh) — nếu có
        private string _rawPinyinText = "";   // Pinyin (nếu có, sách Trung)
        private string _bookTitle = "";
        private string _bookSlug = "";
        private readonly ObservableCollection<MdTocItem> _tocItems = new();
        private bool _isTocVisible = true;
        private bool _isPinyinVisible = true;
        private bool _isFindBarVisible = false;
        private string _lastFindQuery = "";

        public MdPreviewWindow(string mdFilePath = "", string bookTitle = "", string bookSlug = "")
        {
            InitializeComponent();
            SystemThemeWatcher.Watch(this, WindowBackdropType.Mica, true);
            _mdFilePath = mdFilePath;
            _bookTitle = bookTitle;
            _bookSlug = bookSlug;

            if (!string.IsNullOrEmpty(bookTitle))
                TitleBar.Title = $"Preview: {bookTitle}";

            TocTreeView.ItemsSource = _tocItems;

            Loaded += MdPreviewWindow_Loaded;
            Closed += MdPreviewWindow_Closed;
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

                core.WebMessageReceived -= Core_WebMessageReceived;
                core.WebMessageReceived += Core_WebMessageReceived;

                // Đọc toàn bộ nội dung từ các file và nạp đầy đủ dữ liệu
                LoadAllBookLayers();

                // Render chế độ mặc định (Bản dịch thuần Việt)
                RenderMode("vi");
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Lỗi khi mở preview: {ex.Message}", "Lỗi",
                    System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void LoadAllBookLayers()
        {
            var projectRoot = Services.ProjectHelper.FindProjectRoot();

            // 1. Nếu có file ban đầu, nạp và bóc tách
            if (File.Exists(_mdFilePath))
            {
                var content = File.ReadAllText(_mdFilePath);
                ExtractLayersFromText(content);
            }

            // 2. Tìm kiếm thêm dữ liệu đa ngữ từ output/books/<title>/final/ hoặc output/books/<slug>/final/
            if (!string.IsNullOrEmpty(projectRoot))
            {
                var candidateDirs = new List<string>
                {
                    Path.Combine(projectRoot, "output", "books", _bookTitle, "final"),
                    Path.Combine(projectRoot, "output", "books", _bookSlug, "final")
                };

                foreach (var fDir in candidateDirs)
                {
                    if (!Directory.Exists(fDir)) continue;

                    var tamnguPath = Path.Combine(fDir, "tamngu.md");
                    var rawFinalPath = Path.Combine(fDir, "raw.md");
                    var viPath = Path.Combine(fDir, "vi.md");

                    if (File.Exists(tamnguPath) && (string.IsNullOrEmpty(_rawSrcText) || string.IsNullOrEmpty(_rawPinyinText)))
                    {
                        ExtractLayersFromText(File.ReadAllText(tamnguPath));
                    }
                    if (File.Exists(rawFinalPath) && string.IsNullOrEmpty(_rawSrcText))
                    {
                        _rawSrcText = File.ReadAllText(rawFinalPath);
                    }
                    if (File.Exists(viPath) && string.IsNullOrEmpty(_rawViText))
                    {
                        _rawViText = CleanHtmlBlocks(File.ReadAllText(viPath));
                    }
                }

                // 3. Tìm từ working/extracted/<slug>/raw.md nếu thiếu bản gốc
                if (string.IsNullOrEmpty(_rawSrcText) && !string.IsNullOrEmpty(_bookSlug))
                {
                    var rawPath = Path.Combine(projectRoot, "working", "extracted", _bookSlug, "raw.md");
                    if (File.Exists(rawPath))
                    {
                        _rawSrcText = File.ReadAllText(rawPath);
                    }
                }

                // 4. Tìm từ working/progress/<slug>/ nếu vẫn chưa có đủ
                if ((string.IsNullOrEmpty(_rawViText) || string.IsNullOrEmpty(_rawSrcText) || string.IsNullOrEmpty(_rawPinyinText)) && !string.IsNullOrEmpty(_bookSlug))
                {
                    var progDir = Path.Combine(projectRoot, "working", "progress", _bookSlug);
                    if (Directory.Exists(progDir))
                    {
                        try
                        {
                            var pFiles = Directory.GetFiles(progDir, "chunk_*.json").OrderBy(x => x).ToList();
                            var sList = new List<string>();
                            var pList = new List<string>();
                            var vList = new List<string>();
                            foreach (var pf in pFiles)
                            {
                                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(pf));
                                if (doc.RootElement.TryGetProperty("original_text", out var ot) && !string.IsNullOrEmpty(ot.GetString()))
                                    sList.Add(ot.GetString()!);
                                else if (doc.RootElement.TryGetProperty("source_text", out var st) && !string.IsNullOrEmpty(st.GetString()))
                                    sList.Add(st.GetString()!);

                                if (doc.RootElement.TryGetProperty("pinyin_text", out var pt) && !string.IsNullOrEmpty(pt.GetString()))
                                    pList.Add(pt.GetString()!);

                                if (doc.RootElement.TryGetProperty("translated_text", out var tt) && !string.IsNullOrEmpty(tt.GetString()))
                                    vList.Add(tt.GetString()!);
                            }
                            if (string.IsNullOrEmpty(_rawSrcText) && sList.Count > 0) _rawSrcText = string.Join("\n\n", sList);
                            if (string.IsNullOrEmpty(_rawPinyinText) && pList.Count > 0) _rawPinyinText = string.Join("\n\n", pList);
                            if (string.IsNullOrEmpty(_rawViText) && vList.Count > 0) _rawViText = string.Join("\n\n", vList);
                        }
                        catch { }
                    }
                }
            }
        }

        private void ExtractLayersFromText(string content)
        {
            if (string.IsNullOrWhiteSpace(content)) return;

            // Kiểm tra xem có chứa các đoạn p tag tam ngữ/song ngữ (<p class="src-zh"> hoặc tri-block hoặc bi-block)
            if (content.Contains("src-zh") || content.Contains("pinyin") || content.Contains("tri-block") || content.Contains("bi-block"))
            {
                var srcLines = new StringBuilder();
                var pinLines = new StringBuilder();
                var viLines = new StringBuilder();

                var lines = content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);

                foreach (var line in lines)
                {
                    var trimmed = line.Trim();
                    if (string.IsNullOrWhiteSpace(trimmed)) continue;
                    if (trimmed.StartsWith("<div") || trimmed.StartsWith("</div>")) continue;

                    var mSrc = Regex.Match(trimmed, @"<p class=[""']src-.*?[""']>(.*?)</p>", RegexOptions.Singleline);
                    var mPin = Regex.Match(trimmed, @"<p class=[""']pinyin[""']>(.*?)</p>", RegexOptions.Singleline);
                    var mVi = Regex.Match(trimmed, @"<p class=[""']vi[""']>(.*?)</p>", RegexOptions.Singleline);

                    if (mSrc.Success)
                    {
                        srcLines.AppendLine(mSrc.Groups[1].Value);
                    }
                    else if (mPin.Success)
                    {
                        pinLines.AppendLine(mPin.Groups[1].Value);
                    }
                    else if (mVi.Success)
                    {
                        viLines.AppendLine(mVi.Groups[1].Value);
                    }
                    else if (!trimmed.StartsWith("<"))
                    {
                        // Dòng tiêu đề hoặc ảnh markdown thông thường (# Tiêu đề, ![](ảnh))
                        srcLines.AppendLine(trimmed);
                        pinLines.AppendLine(trimmed);
                        viLines.AppendLine(trimmed);
                    }
                }

                if (srcLines.Length > 0) _rawSrcText = srcLines.ToString();
                if (pinLines.Length > 0) _rawPinyinText = pinLines.ToString();
                if (viLines.Length > 0) _rawViText = viLines.ToString();
                return;
            }

            // Nếu là markdown thông thường (vi.md hoặc raw.md)
            if (string.IsNullOrEmpty(_rawViText))
                _rawViText = content;
        }

        private static string CleanHtmlBlocks(string text)
        {
            if (string.IsNullOrEmpty(text)) return "";
            // Xoá các thẻ bọc thừa nếu có
            return Regex.Replace(text, @"</?(div|p)[^>]*>", "");
        }

        /// <summary>Được MainViewModel gọi để bổ sung source/pinyin từ progress JSON.</summary>
        public void SetSourceContent(string srcText, string pinyinText)
        {
            if (!string.IsNullOrEmpty(srcText)) _rawSrcText = srcText;
            if (!string.IsNullOrEmpty(pinyinText)) _rawPinyinText = pinyinText;
        }

        private async void CmbMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (WebView?.CoreWebView2 == null) return;
            var item = CmbMode.SelectedItem as ComboBoxItem;
            var tag = item?.Tag?.ToString() ?? "vi";
            var modeName = item?.Content?.ToString() ?? "chế độ";

            // Bật hiệu ứng loading overlay
            if (LoadingOverlay != null)
            {
                if (TxtLoadingStatus != null)
                    TxtLoadingStatus.Text = $"Đang tải {modeName}...";
                LoadingOverlay.Visibility = Visibility.Visible;
            }

            // Chờ 1 tick UI để hiệu ứng loading hiển thị trước khi tính toán HTML
            await Task.Yield();
            RenderMode(tag);
        }

        private void RenderMode(string mode)
        {
            string html;
            string targetContent;
            switch (mode)
            {
                case "src":
                    targetContent = !string.IsNullOrEmpty(_rawSrcText) ? _rawSrcText : _rawViText;
                    html = BuildHtml(targetContent, "Bản gốc nguyên tác");
                    break;
                case "split":
                    targetContent = !string.IsNullOrEmpty(_rawViText) ? _rawViText : _rawSrcText;
                    html = BuildSplitViewHtml(
                        !string.IsNullOrEmpty(_rawSrcText) ? _rawSrcText : _rawViText,
                        targetContent);
                    break;
                case "bi":
                    targetContent = !string.IsNullOrEmpty(_rawViText) ? _rawViText : _rawSrcText;
                    html = BuildBilingualHtml(
                        !string.IsNullOrEmpty(_rawSrcText) ? _rawSrcText : _rawViText,
                        targetContent);
                    break;
                case "tri":
                    targetContent = !string.IsNullOrEmpty(_rawViText) ? _rawViText : _rawSrcText;
                    html = BuildTrilingualHtml(
                        !string.IsNullOrEmpty(_rawSrcText) ? _rawSrcText : _rawViText,
                        !string.IsNullOrEmpty(_rawPinyinText) ? _rawPinyinText : "",
                        targetContent);
                    break;
                case "vi":
                default:
                    targetContent = !string.IsNullOrEmpty(_rawViText) ? _rawViText : _rawSrcText;
                    html = BuildHtml(targetContent, "Bản dịch (Thuần Việt)");
                    break;
            }

            BuildTocFromContent(targetContent);

            if (WebView?.CoreWebView2 != null)
            {
                WebView.CoreWebView2.NavigateToString(html);
            }
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
                /* Split View (Song song 2 Cột) */
                .split-wrapper {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 24px;
                    width: 100%;
                    max-width: 100% !important;
                }}
                .split-col {{
                    padding: 16px;
                    background: rgba(128,128,128,0.03);
                    border-radius: 8px;
                    border: 1px solid rgba(128,128,128,0.12);
                }}
                .split-col-header {{
                    font-size: 0.9em;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    color: var(--link-color);
                    margin-bottom: 12px;
                    padding-bottom: 6px;
                    border-bottom: 1px solid rgba(128,128,128,0.2);
                }}
                .split-row {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 16px;
                    padding-bottom: 14px;
                    border-bottom: 1px dashed rgba(128,128,128,0.15);
                }}
                .split-row:last-child {{
                    border-bottom: none;
                }}
                .split-cell-src {{
                    color: var(--fg-secondary-color);
                }}
                .split-cell-vi {{
                    color: var(--fg-color);
                }}
                /* Tùy biến ẩn hiện dòng Pinyin */
                body.hide-pinyin .pinyin {{
                    display: none !important;
                }}
                /* Search highlight styling */
                mark.find-match {{
                    background-color: #FFD54F !important;
                    color: #000000 !important;
                    border-radius: 2px;
                    padding: 0 2px;
                }}
                mark.find-match.find-current {{
                    background-color: #FF7043 !important;
                    color: #FFFFFF !important;
                    outline: 2px solid #D84315;
                }}
                ::-webkit-scrollbar {{ width: 8px; }}
                ::-webkit-scrollbar-track {{ background: rgba(128,128,128,0.1); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb {{ background: rgba(128,128,128,0.3); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: rgba(128,128,128,0.5); }}
            ";
        }

        private string BuildSplitViewHtml(string srcMd, string viMd)
        {
            string css = BuildEpubCss();
            var body = new StringBuilder();
            body.AppendLine($"<div class='book-title'>📖 {EscapeHtml(_bookTitle)} — Song song Đối chiếu (Side-by-Side)</div>");

            var srcBlocks = SplitIntoBlocks(srcMd);
            var viBlocks = SplitIntoBlocks(viMd);

            body.AppendLine("<div class='split-container'>");
            body.AppendLine("  <div class='split-row' style='font-weight: bold; border-bottom: 2px solid var(--link-color); padding-bottom: 8px;'>");
            body.AppendLine("    <div class='split-col-header'>📄 BẢN GỐC (NGUỒN)</div>");
            body.AppendLine("    <div class='split-col-header'>✨ BẢN DỊCH (VIỆT)</div>");
            body.AppendLine("  </div>");

            int n = Math.Max(srcBlocks.Count, viBlocks.Count);
            for (int i = 0; i < n; i++)
            {
                string s = i < srcBlocks.Count ? srcBlocks[i] : "";
                string v = i < viBlocks.Count ? viBlocks[i] : "";
                if (string.IsNullOrWhiteSpace(s) && string.IsNullOrWhiteSpace(v)) continue;

                body.AppendLine("  <div class='split-row'>");
                body.AppendLine("    <div class='split-cell-src'>");
                body.AppendLine(MarkdownToHtml(s));
                body.AppendLine("    </div>");
                body.AppendLine("    <div class='split-cell-vi'>");
                body.AppendLine(MarkdownToHtml(v));
                body.AppendLine("    </div>");
                body.AppendLine("  </div>");
            }
            body.AppendLine("</div>");

            return $@"<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Preview Side-by-Side</title>
<style>{css}</style>
</head>
<body style='max-width: 95%;'>
{body}
</body>
</html>";
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

        /// <summary>Tách markdown thành các block theo đoạn văn bản tự nhiên (heading hoặc paragraph).</summary>
        private static System.Collections.Generic.List<string> SplitIntoBlocks(string md)
        {
            var result = new System.Collections.Generic.List<string>();
            if (string.IsNullOrWhiteSpace(md)) return result;

            // Chuẩn hóa xuống dòng
            var text = md.Replace("\r\n", "\n").Replace("\r", "\n");
            var rawParagraphs = text.Split(new[] { "\n\n" }, StringSplitOptions.RemoveEmptyEntries);

            foreach (var p in rawParagraphs)
            {
                var trimmed = p.Trim();
                if (string.IsNullOrWhiteSpace(trimmed)) continue;

                // Nếu trong 1 paragraph có chứa nhiều dòng riêng lẻ bắt đầu bằng # (Heading)
                var lines = trimmed.Split('\n');
                var current = new StringBuilder();
                foreach (var line in lines)
                {
                    var lTrim = line.TrimEnd();
                    if (Regex.IsMatch(lTrim, @"^#{1,6}\s") && current.Length > 0)
                    {
                        result.Add(current.ToString().Trim());
                        current.Clear();
                    }
                    current.AppendLine(lTrim);
                }
                if (current.Length > 0)
                {
                    result.Add(current.ToString().Trim());
                }
            }

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
                    var anchorId = GenerateAnchorId(text);
                    sb.AppendLine($"<h{level} id='{anchorId}'>{InlineMarkdown(text)}</h{level}>");
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
                InjectScrollSpy();
            }

            // Tắt hiệu ứng loading overlay khi trình duyệt đã render xong
            if (LoadingOverlay != null)
            {
                LoadingOverlay.Visibility = Visibility.Collapsed;
            }
        }

        private void InjectScrollSpy()
        {
            if (WebView?.CoreWebView2 == null) return;

            string js = @"
                (function() {
                    if (window._scrollSpyAttached) return;
                    window._scrollSpyAttached = true;

                    var lastActiveId = '';
                    var scrollTimeout = null;

                    window.addEventListener('scroll', function() {
                        if (scrollTimeout) clearTimeout(scrollTimeout);
                        scrollTimeout = setTimeout(function() {
                            var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                            if (!headings || headings.length === 0) return;

                            var currentId = '';
                            var scrollY = window.scrollY || window.pageYOffset;

                            for (var i = 0; i < headings.length; i++) {
                                var h = headings[i];
                                var top = h.offsetTop;
                                if (top <= scrollY + 120) {
                                    currentId = h.id || '';
                                } else {
                                    break;
                                }
                            }

                            if (!currentId && headings.length > 0) {
                                currentId = headings[0].id || '';
                            }

                            if (currentId && currentId !== lastActiveId) {
                                lastActiveId = currentId;
                                if (window.chrome && window.chrome.webview) {
                                    window.chrome.webview.postMessage(JSON.stringify({ type: 'headingActive', id: currentId }));
                                }
                            }
                        }, 100);
                    });
                })();
            ";

            WebView.CoreWebView2.ExecuteScriptAsync(js);
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
            else if (e.Key == Key.T && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
            {
                ToggleToc();
                e.Handled = true;
            }
            else if (e.Key == Key.F && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
            {
                ToggleFindBar();
                e.Handled = true;
            }
            else if (e.Key == Key.F3)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Shift) == ModifierKeys.Shift)
                    NavigateFindMatch(-1);
                else
                    NavigateFindMatch(1);
                e.Handled = true;
            }
            else if (e.Key == Key.Escape && _isFindBarVisible)
            {
                CloseFindBar();
                e.Handled = true;
            }
        }

        private void BtnToggleToc_Click(object sender, RoutedEventArgs e)
        {
            ToggleToc();
        }

        private double _lastTocWidth = 260;

        private void ToggleToc()
        {
            _isTocVisible = !_isTocVisible;
            if (_isTocVisible)
            {
                if (ColToc != null)
                    ColToc.Width = new GridLength(_lastTocWidth > 100 ? _lastTocWidth : 260);
                if (ColSplitter != null)
                    ColSplitter.Width = new GridLength(5);
                if (TocSidebar != null)
                    TocSidebar.Visibility = Visibility.Visible;
                if (TocSplitter != null)
                    TocSplitter.Visibility = Visibility.Visible;
            }
            else
            {
                if (ColToc != null)
                {
                    if (ColToc.ActualWidth > 100)
                        _lastTocWidth = ColToc.ActualWidth;
                    ColToc.Width = new GridLength(0);
                }
                if (ColSplitter != null)
                    ColSplitter.Width = new GridLength(0);
                if (TocSidebar != null)
                    TocSidebar.Visibility = Visibility.Collapsed;
                if (TocSplitter != null)
                    TocSplitter.Visibility = Visibility.Collapsed;
            }
        }

        private static string GenerateAnchorId(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return "sec-top";
            var clean = Regex.Replace(text.Trim().ToLowerInvariant(), @"[^a-z0-9\u00C0-\u1EF9]+", "-").Trim('-');
            if (string.IsNullOrEmpty(clean)) clean = "heading";
            return "sec-" + clean;
        }

        private void BuildTocFromContent(string markdown)
        {
            _tocItems.Clear();
            var list = new List<MdTocItem>();

            if (!string.IsNullOrWhiteSpace(markdown))
            {
                var lines = markdown.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);
                foreach (var line in lines)
                {
                    var trimmed = line.Trim();
                    var m = Regex.Match(trimmed, @"^(#{1,3})\s+(.*)$");
                    if (m.Success)
                    {
                        int level = m.Groups[1].Value.Length;
                        string title = m.Groups[2].Value.Trim();
                        // Bỏ định dạng inline markdown như **bold**, *italic* khỏi tiêu đề TOC
                        title = Regex.Replace(title, @"[\*_`~]", "");
                        if (string.IsNullOrWhiteSpace(title)) continue;

                        list.Add(new MdTocItem
                        {
                            Title = title,
                            AnchorId = GenerateAnchorId(title),
                            Level = level
                        });
                    }
                }
            }

            // Nếu không tìm thấy heading nào từ markdown nhưng có chunk files
            if (list.Count == 0 && !string.IsNullOrEmpty(_bookSlug))
            {
                var projectRoot = Services.ProjectHelper.FindProjectRoot();
                if (!string.IsNullOrEmpty(projectRoot))
                {
                    var chunksDir = Path.Combine(projectRoot, "working", "chunks", _bookSlug);
                    if (Directory.Exists(chunksDir))
                    {
                        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                        foreach (var f in Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(x => x))
                        {
                            try
                            {
                                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(f));
                                if (doc.RootElement.TryGetProperty("chapter", out var ch))
                                {
                                    var cName = ch.GetString();
                                    if (!string.IsNullOrWhiteSpace(cName) && seen.Add(cName))
                                    {
                                        list.Add(new MdTocItem
                                        {
                                            Title = cName,
                                            AnchorId = GenerateAnchorId(cName),
                                            Level = 1
                                        });
                                    }
                                }
                            }
                            catch { }
                        }
                    }
                }
            }

            // Xây dựng cây phân cấp (H1 chứa H2, H2 chứa H3)
            MdTocItem? currentH1 = null;
            MdTocItem? currentH2 = null;

            foreach (var item in list)
            {
                if (item.Level == 1)
                {
                    _tocItems.Add(item);
                    currentH1 = item;
                    currentH2 = null;
                }
                else if (item.Level == 2)
                {
                    if (currentH1 != null)
                    {
                        currentH1.NestedItems.Add(item);
                    }
                    else
                    {
                        _tocItems.Add(item);
                    }
                    currentH2 = item;
                }
                else
                {
                    if (currentH2 != null)
                    {
                        currentH2.NestedItems.Add(item);
                    }
                    else if (currentH1 != null)
                    {
                        currentH1.NestedItems.Add(item);
                    }
                    else
                    {
                        _tocItems.Add(item);
                    }
                }
            }

            // Tự động mở rộng cây mục lục
            Dispatcher.BeginInvoke(new Action(() =>
            {
                ExpandAllTocItems(TocTreeView);
            }), System.Windows.Threading.DispatcherPriority.Loaded);
        }

        private static void ExpandAllTocItems(ItemsControl itemsControl)
        {
            if (itemsControl == null) return;
            foreach (var item in itemsControl.Items)
            {
                if (itemsControl.ItemContainerGenerator.ContainerFromItem(item) is System.Windows.Controls.TreeViewItem container)
                {
                    container.IsExpanded = true;
                    if (container.HasItems)
                        ExpandAllTocItems(container);
                }
            }
        }

        private bool _isProgrammaticTocSelection = false;

        private void TocTreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            if (_isProgrammaticTocSelection) return;
            if (e.NewValue is MdTocItem item)
            {
                ScrollToHeading(item.AnchorId, item.Title);
            }
        }

        private void Core_WebMessageReceived(object? sender, Microsoft.Web.WebView2.Core.CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                var rawJson = e.TryGetWebMessageAsString();
                if (string.IsNullOrEmpty(rawJson)) return;

                using var doc = System.Text.Json.JsonDocument.Parse(rawJson);
                if (doc.RootElement.TryGetProperty("type", out var typeProp) && typeProp.GetString() == "headingActive")
                {
                    if (doc.RootElement.TryGetProperty("id", out var idProp))
                    {
                        var activeId = idProp.GetString();
                        if (!string.IsNullOrEmpty(activeId))
                        {
                            Dispatcher.Invoke(() => SelectTocItemById(activeId));
                        }
                    }
                }
            }
            catch { }
        }

        private void SelectTocItemById(string anchorId)
        {
            if (TocTreeView == null || _tocItems == null || _tocItems.Count == 0) return;

            MdTocItem? FindInList(IEnumerable<MdTocItem> items, string id)
            {
                foreach (var it in items)
                {
                    if (string.Equals(it.AnchorId, id, StringComparison.OrdinalIgnoreCase)) return it;
                    var found = FindInList(it.NestedItems, id);
                    if (found != null) return found;
                }
                return null;
            }

            var target = FindInList(_tocItems, anchorId);
            if (target == null) return;

            _isProgrammaticTocSelection = true;
            try
            {
                // Tìm container TreeViewItem tương ứng và đánh dấu IsSelected
                void SelectContainer(ItemsControl parent, MdTocItem item)
                {
                    var container = parent.ItemContainerGenerator.ContainerFromItem(item) as System.Windows.Controls.TreeViewItem;
                    if (container != null)
                    {
                        container.IsSelected = true;
                        container.BringIntoView();
                        return;
                    }

                    foreach (var child in parent.Items)
                    {
                        if (parent.ItemContainerGenerator.ContainerFromItem(child) is System.Windows.Controls.TreeViewItem childContainer)
                        {
                            SelectContainer(childContainer, item);
                        }
                    }
                }

                SelectContainer(TocTreeView, target);
            }
            finally
            {
                _isProgrammaticTocSelection = false;
            }
        }

        private void ScrollToHeading(string anchorId, string title)
        {
            if (WebView?.CoreWebView2 == null) return;

            string cleanAnchor = EscapeJsString(anchorId);
            string cleanTitle = EscapeJsString(title.Trim());

            string js = $@"
                (function() {{
                    // 1. Thử cuộn theo ID anchor
                    var el = document.getElementById('{cleanAnchor}');
                    if (el) {{
                        el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        return;
                    }}

                    // 2. Thử tìm kiếm theo textContent của heading
                    var title = '{cleanTitle}'.toLowerCase();
                    var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    for (var i = 0; i < headings.length; i++) {{
                        var text = headings[i].textContent.trim().toLowerCase();
                        if (text === title || text.indexOf(title) >= 0 || title.indexOf(text) >= 0) {{
                            headings[i].scrollIntoView({{behavior: 'smooth', block: 'start'}});
                            return;
                        }}
                    }}

                    // 3. Fallback: tìm theo chuỗi slug ID mờ
                    var slug = '{cleanAnchor}'.replace(/^sec-/, '');
                    for (var j = 0; j < headings.length; j++) {{
                        if (headings[j].id && headings[j].id.indexOf(slug) >= 0) {{
                            headings[j].scrollIntoView({{behavior: 'smooth', block: 'start'}});
                            return;
                        }}
                    }}
                }})();
            ";

            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private static string EscapeJsString(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\").Replace("'", "\\'").Replace("\n", "\\n").Replace("\r", "\\r");
        }

        private void MdPreviewWindow_Closed(object? sender, EventArgs e)
        {
            // Giải phóng WebView2 khi đóng để không giữ handle file (tránh lỗi xóa sách sau khi xem preview)
            try
            {
                WebView?.CoreWebView2?.RemoveHostObjectFromScript("TranslateBookBridge");
                WebView?.Dispose();
            }
            catch { }
        }

        #region In-Page Find (Tìm kiếm trong trang) & Pinyin Toggle

        private void BtnToggleFind_Click(object sender, RoutedEventArgs e)
        {
            ToggleFindBar();
        }

        private void ToggleFindBar()
        {
            _isFindBarVisible = !_isFindBarVisible;
            if (_isFindBarVisible)
            {
                FindBar.Visibility = Visibility.Visible;
                TxtFindQuery.Focus();
                TxtFindQuery.SelectAll();
                if (!string.IsNullOrWhiteSpace(TxtFindQuery.Text))
                {
                    PerformFind(TxtFindQuery.Text);
                }
            }
            else
            {
                CloseFindBar();
            }
        }

        private void CloseFindBar()
        {
            _isFindBarVisible = false;
            FindBar.Visibility = Visibility.Collapsed;
            ClearFindHighlights();
            WebView.Focus();
        }

        private void BtnFindClose_Click(object sender, RoutedEventArgs e)
        {
            CloseFindBar();
        }

        private void TxtFindQuery_TextChanged(object sender, TextChangedEventArgs e)
        {
            var query = TxtFindQuery.Text.Trim();
            if (string.IsNullOrEmpty(query))
            {
                ClearFindHighlights();
                TxtFindCount.Text = "0/0";
            }
            else
            {
                PerformFind(query);
            }
        }

        private void TxtFindQuery_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Shift) == ModifierKeys.Shift)
                    NavigateFindMatch(-1);
                else
                    NavigateFindMatch(1);
                e.Handled = true;
            }
            else if (e.Key == Key.Escape)
            {
                CloseFindBar();
                e.Handled = true;
            }
        }

        private void BtnFindPrev_Click(object sender, RoutedEventArgs e)
        {
            NavigateFindMatch(-1);
        }

        private void BtnFindNext_Click(object sender, RoutedEventArgs e)
        {
            NavigateFindMatch(1);
        }

        private async void PerformFind(string query)
        {
            if (WebView?.CoreWebView2 == null) return;
            _lastFindQuery = query;
            string clean = EscapeJsString(query);

            string js = $@"
                (function() {{
                    // Xóa các highlight cũ
                    var oldMarks = document.querySelectorAll('mark.find-match');
                    for (var i = 0; i < oldMarks.length; i++) {{
                        var parent = oldMarks[i].parentNode;
                        parent.replaceChild(document.createTextNode(oldMarks[i].textContent), oldMarks[i]);
                        parent.normalize();
                    }}

                    var query = '{clean}'.toLowerCase();
                    if (!query) return JSON.stringify({{ count: 0, index: 0 }});

                    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {{
                        acceptNode: function(node) {{
                            if (node.parentNode && (node.parentNode.nodeName === 'SCRIPT' || node.parentNode.nodeName === 'STYLE'))
                                return NodeFilter.FILTER_REJECT;
                            return NodeFilter.FILTER_ACCEPT;
                        }}
                    }});

                    var nodes = [];
                    while (walker.nextNode()) nodes.push(walker.currentNode);

                    var count = 0;
                    for (var n = 0; n < nodes.length; n++) {{
                        var node = nodes[n];
                        var text = node.nodeValue;
                        var lower = text.toLowerCase();
                        var idx = lower.indexOf(query);
                        if (idx >= 0) {{
                            var frag = document.createDocumentFragment();
                            var lastIdx = 0;
                            while (idx >= 0) {{
                                if (idx > lastIdx) {{
                                    frag.appendChild(document.createTextNode(text.substring(lastIdx, idx)));
                                }}
                                var mark = document.createElement('mark');
                                mark.className = 'find-match';
                                mark.setAttribute('data-find-index', count);
                                mark.textContent = text.substring(idx, idx + query.length);
                                frag.appendChild(mark);
                                count++;
                                lastIdx = idx + query.length;
                                idx = lower.indexOf(query, lastIdx);
                            }}
                            if (lastIdx < text.length) {{
                                frag.appendChild(document.createTextNode(text.substring(lastIdx)));
                            }}
                            node.parentNode.replaceChild(frag, node);
                        }}
                    }}

                    window._findMatchesCount = count;
                    window._currentFindIndex = count > 0 ? 0 : -1;

                    if (count > 0) {{
                        var first = document.querySelector('mark.find-match[data-find-index=""0""]');
                        if (first) {{
                            first.classList.add('find-current');
                            first.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        }}
                    }}

                    return JSON.stringify({{ count: count, index: count > 0 ? 1 : 0 }});
                }})();
            ";

            try
            {
                var resultJson = await WebView.CoreWebView2.ExecuteScriptAsync(js);
                if (!string.IsNullOrEmpty(resultJson))
                {
                    // ExecuteScriptAsync trả về chuỗi JSON được bọc string literal
                    var unescaped = System.Text.Json.JsonSerializer.Deserialize<string>(resultJson);
                    if (!string.IsNullOrEmpty(unescaped))
                    {
                        using var doc = System.Text.Json.JsonDocument.Parse(unescaped);
                        int count = doc.RootElement.GetProperty("count").GetInt32();
                        int idx = doc.RootElement.GetProperty("index").GetInt32();
                        TxtFindCount.Text = count > 0 ? $"{idx}/{count}" : "0/0";
                    }
                }
            }
            catch { }
        }

        private async void NavigateFindMatch(int delta)
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = $@"
                (function() {{
                    var count = window._findMatchesCount || 0;
                    if (count === 0) return JSON.stringify({{ count: 0, index: 0 }});

                    var current = window._currentFindIndex;
                    var oldMark = document.querySelector('mark.find-match[data-find-index=""' + current + '""]');
                    if (oldMark) oldMark.classList.remove('find-current');

                    var next = (current + {delta} + count) % count;
                    window._currentFindIndex = next;

                    var nextMark = document.querySelector('mark.find-match[data-find-index=""' + next + '""]');
                    if (nextMark) {{
                        nextMark.classList.add('find-current');
                        nextMark.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}

                    return JSON.stringify({{ count: count, index: next + 1 }});
                }})();
            ";

            try
            {
                var resultJson = await WebView.CoreWebView2.ExecuteScriptAsync(js);
                if (!string.IsNullOrEmpty(resultJson))
                {
                    var unescaped = System.Text.Json.JsonSerializer.Deserialize<string>(resultJson);
                    if (!string.IsNullOrEmpty(unescaped))
                    {
                        using var doc = System.Text.Json.JsonDocument.Parse(unescaped);
                        int count = doc.RootElement.GetProperty("count").GetInt32();
                        int idx = doc.RootElement.GetProperty("index").GetInt32();
                        TxtFindCount.Text = $"{idx}/{count}";
                    }
                }
            }
            catch { }
        }

        private void ClearFindHighlights()
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = @"
                (function() {
                    var oldMarks = document.querySelectorAll('mark.find-match');
                    for (var i = 0; i < oldMarks.length; i++) {
                        var parent = oldMarks[i].parentNode;
                        parent.replaceChild(document.createTextNode(oldMarks[i].textContent), oldMarks[i]);
                        parent.normalize();
                    }
                    window._findMatchesCount = 0;
                    window._currentFindIndex = -1;
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void BtnTogglePinyin_Click(object sender, RoutedEventArgs e)
        {
            _isPinyinVisible = !_isPinyinVisible;
            if (WebView?.CoreWebView2 != null)
            {
                string js = _isPinyinVisible
                    ? "document.body.classList.remove('hide-pinyin');"
                    : "document.body.classList.add('hide-pinyin');";
                WebView.CoreWebView2.ExecuteScriptAsync(js);
            }
        }

        #endregion
    }
}
