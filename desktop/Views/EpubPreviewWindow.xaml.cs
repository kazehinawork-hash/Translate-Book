using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using System.Windows.Controls;
using TranslateBook.Models;
using TranslateBook.Services;
using VersOne.Epub;
using Wpf.Ui.Appearance;
using Wpf.Ui.Controls;
using HtmlAgilityPack;

namespace TranslateBook.Views
{
    public partial class EpubPreviewWindow : FluentWindow
    {
        private string _epubFilePath = "";
        private string _tempExtractPath = "";
        private readonly List<string> _readingOrderPaths = new();
        private string _fullBookHtmlPath = "";
        private readonly Dictionary<string, int> _pathToChapterId = new();  // EPUB path → DOM chapter ID
        private readonly List<TocItem> _flatToc = new();  // Flattened TOC for audio sync

        private MediaPlayer? _mediaPlayer;
        private DispatcherTimer? _timer;
        private List<string> _audioFiles = new();
        private int _currentTrackIndex = -1;
        private bool _isDraggingSlider = false;

        // Search state
        private bool _isSearchHighlightActive = false;

        public EpubPreviewWindow(string epubFilePath = "")
        {
            InitializeComponent();
            SystemThemeWatcher.Watch(this, WindowBackdropType.Mica, true);
            _epubFilePath = epubFilePath;
            _tempExtractPath = Path.Combine(Path.GetTempPath(), "TranslateBook_EpubPreview_" + Guid.NewGuid().ToString());

            Loaded += EpubPreviewWindow_Loaded;
            Closed += EpubPreviewWindow_Closed;
        }

        public void LoadEpubFile(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("EPUB path cannot be empty.", nameof(path));

            _epubFilePath = path;
        }

        private async void EpubPreviewWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                var userDataFolder = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "TranslateBook", "WebView2");
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

                core.Settings.IsWebMessageEnabled = true;

                // Validate EPUB path
                if (string.IsNullOrWhiteSpace(_epubFilePath))
                    throw new InvalidOperationException("Đường dẫn file EPUB trống.");

                // Read and extract EPUB
                EpubBook book = await EpubReader.ReadBookAsync(_epubFilePath);

                if (Directory.Exists(_tempExtractPath))
                    Directory.Delete(_tempExtractPath, true);

                ZipFile.ExtractToDirectory(_epubFilePath, _tempExtractPath);

                // Build TOC
                var toc = new List<TocItem>();
                if (book.Navigation != null)
                {
                    foreach (var navItem in book.Navigation)
                        toc.Add(MapNavigationItem(navItem));
                }
                TocTreeView.ItemsSource = toc;
                FlattenToc(toc);

                // Auto-expand all TOC items after layout is ready
                TocTreeView.ItemContainerGenerator.StatusChanged += (s, e) =>
                {
                    if (TocTreeView.ItemContainerGenerator.Status == System.Windows.Controls.Primitives.GeneratorStatus.ContainersGenerated)
                    {
                        ExpandAllTocItems(TocTreeView);
                    }
                };
                // Also try immediately in case containers are already generated
                Dispatcher.BeginInvoke(new Action(() => ExpandAllTocItems(TocTreeView)), System.Windows.Threading.DispatcherPriority.Loaded);

                // Build reading order
                if (book.ReadingOrder != null)
                {
                    foreach (var roItem in book.ReadingOrder)
                    {
                        if (roItem != null && !string.IsNullOrEmpty(roItem.FilePath))
                            _readingOrderPaths.Add(roItem.FilePath);
                    }
                }

                // Fallback: if no reading order, try using navigation items' file paths
                if (_readingOrderPaths.Count == 0 && book.Navigation != null)
                {
                    CollectNavigationPaths(book.Navigation, _readingOrderPaths);
                }

                System.Diagnostics.Debug.WriteLine($"ReadingOrder paths: {_readingOrderPaths.Count}");
                foreach (var p in _readingOrderPaths)
                    System.Diagnostics.Debug.WriteLine($"  {p}");

                // Build CSS (embedded in HTML head — fixes FOUC)
                string css = BuildEpubCss();

                // Generate fullbook.html with all content
                _fullBookHtmlPath = Path.Combine(_tempExtractPath, "fullbook.html");
                var sb = new StringBuilder();
                sb.AppendLine("<!DOCTYPE html><html><head><meta charset='utf-8'>");
                sb.AppendLine($"<style>{css}</style>");
                sb.AppendLine("</head><body>");

                // Build chapter content with proper ID mapping
                _pathToChapterId.Clear();
                int domChapterId = 0;

                for (int i = 0; i < _readingOrderPaths.Count; i++)
                {
                    string relativePath = _readingOrderPaths[i];

                    // Skip nav/TOC and title page — not content
                    var fileName = Path.GetFileName(relativePath).ToLowerInvariant();
                    if (fileName is "nav.xhtml" or "nav.html" or "title_page.xhtml" or "title_page.html" or "toc.xhtml" or "toc.html")
                        continue;

                    string absolutePath = Path.GetFullPath(Path.Combine(_tempExtractPath, relativePath));
                    if (File.Exists(absolutePath))
                    {
                        _pathToChapterId[relativePath] = domChapterId;

                        string html = ReadTextFileWithEncoding(absolutePath);
                        string body = ExtractBodyContent(html);           // HtmlAgilityPack
                        body = RewriteImagePaths(body, absolutePath, _tempExtractPath); // HtmlAgilityPack

                        sb.AppendLine($"<div id='chap_{domChapterId}'>");
                        sb.AppendLine(body);
                        sb.AppendLine("</div>");

                        domChapterId++;
                    }
                }

                sb.AppendLine("</body></html>");
                File.WriteAllText(_fullBookHtmlPath, sb.ToString(), Encoding.UTF8);

                // Navigate to the full book
                core.SetVirtualHostNameToFolderMapping("translatebook.local", _tempExtractPath,
                    Microsoft.Web.WebView2.Core.CoreWebView2HostResourceAccessKind.Allow);

                // Ensure file exists before navigating
                if (!File.Exists(_fullBookHtmlPath))
                {
                    // Re-create empty file if missing
                    File.WriteAllText(_fullBookHtmlPath, "<html><body><p>No content found.</p></body></html>", Encoding.UTF8);
                }

                core.Navigate($"https://translatebook.local/fullbook.html");

                InitAudioPlayer();
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Lỗi khi mở EPUB: {ex.Message}", "Lỗi", System.Windows.MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private string BuildEpubCss()
        {
            // WPF-UI theme brushes may not resolve correctly here (they can come back as
            // white/near-transparent defaults), so validate luminance and fall back to a
            // fixed dark-theme palette that matches the app's dark UI.
            var bg = GetSafeColor("ControlFillColorTertiaryBrush", Color.FromRgb(0x1e, 0x1e, 0x1e), allowLight: false);
            var fg = GetSafeColor("TextFillColorPrimaryBrush", Color.FromRgb(0xe0, 0xe0, 0xe0), allowLight: true, maxLuminance: 240);
            var fgSecondary = GetSafeColor("TextFillColorSecondaryBrush", Color.FromRgb(0xb0, 0xb0, 0xb0), allowLight: true, maxLuminance: 200);
            var link = (Application.Current.Resources["AccentFillColorDefaultBrush"] as SolidColorBrush)?.Color ?? Color.FromRgb(0x60, 0xa5, 0xfa);

            string bgHex = ColorToHex(bg);
            string fgHex = ColorToHex(fg);
            string fgSecondaryHex = ColorToHex(fgSecondary);
            string linkHex = ColorToHex(link);

            return $@"
                :root {{
                    --bg-color: {bgHex};
                    --fg-color: {fgHex};
                    --fg-secondary-color: {fgSecondaryHex};
                    --link-color: {linkHex};
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
                h4 {{ font-size: calc(var(--font-size) * 1.15); }}
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
                    color: var(--fg-color);
                }}
                pre code {{
                    padding: 0;
                    background: none;
                    display: block;
                    overflow-x: auto;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                }}
                th, td {{
                    border: 1px solid {fgSecondaryHex};
                    padding: 0.4em 0.6em;
                    text-align: left;
                }}
                th {{ font-weight: 600; color: var(--fg-color); }}
                ul, ol {{ margin: 0.5em 0; padding-left: 2em; }}
                li {{ margin: 0.2em 0; }}
                img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 1.5em auto;
                    border-radius: 4px;
                }}
                figcaption {{
                    text-align: center;
                    color: var(--fg-secondary-color);
                    font-size: 0.9em;
                    margin: 0.5em 0;
                }}
                a {{ color: var(--link-color); text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                ruby {{ ruby-position: under; ruby-align: auto; }}
                rt {{ font-size: 0.7em; color: var(--fg-secondary-color); }}
                div[id^='chap_'] {{ margin-bottom: 2.5em; }}
                .search-highlight {{
                    background-color: rgba(255, 230, 0, 0.4);
                    scroll-margin-top: 24px;
                }}
                ::-webkit-scrollbar {{ width: 8px; }}
                ::-webkit-scrollbar-track {{ background: rgba(128,128,128,0.1); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb {{ background: rgba(128,128,128,0.3); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: rgba(128,128,128,0.5); }}
            ";
        }

        /// <summary>
        /// Reads an XHTML chapter with BOM/encoding detection so Vietnamese and CJK
        /// characters are never mis-decoded (mojibake) when the file is not UTF-8.
        /// </summary>
        private static string ReadTextFileWithEncoding(string path)
        {
            var bytes = File.ReadAllBytes(path);
            // UTF-16 BOM (LE/FE FF / FF FE)
            if (bytes.Length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE)
                return Encoding.Unicode.GetString(bytes, 2, bytes.Length - 2);
            if (bytes.Length >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF)
                return Encoding.BigEndianUnicode.GetString(bytes, 2, bytes.Length - 2);
            // UTF-8 BOM
            if (bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF)
                return Encoding.UTF8.GetString(bytes, 3, bytes.Length - 3);
            // Fallback: strict UTF-8; if the bytes are not valid UTF-8, fall back to
            // the system ANSI codepage so legacy-encoded chapters still decode.
            try
            {
                return new UTF8Encoding(false, true).GetString(bytes);
            }
            catch (DecoderFallbackException)
            {
                return Encoding.Default.GetString(bytes);
            }
        }

        private string ExtractBodyContent(string html)
        {
            try
            {
                var doc = new HtmlDocument();
                doc.LoadHtml(html);
                var body = doc.DocumentNode.Descendants("body").FirstOrDefault();
                if (body != null)
                    return body.InnerHtml;

                // Fallback: return content inside <html> or the whole doc
                var htmlNode = doc.DocumentNode.Descendants("html").FirstOrDefault();
                if (htmlNode != null && htmlNode.InnerHtml.Length > 0)
                    return htmlNode.InnerHtml;

                return html;
            }
            catch
            {
                // Ultimate fallback: regex
                var match = System.Text.RegularExpressions.Regex.Match(
                    html, @"<body[^>]*>(.*?)</body\s*>",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase |
                    System.Text.RegularExpressions.RegexOptions.Singleline);
                return match.Success ? match.Groups[1].Value : html;
            }
        }

        private string RewriteImagePaths(string html, string fileDir, string basePath)
        {
            try
            {
                var doc = new HtmlDocument();
                doc.LoadHtml(html);

                foreach (var node in doc.DocumentNode.Descendants())
                {
                    string? attrName = null;

                    // Only rewrite image src, not link hrefs (nav/TOC links)
                    if (node.Name == "img")
                        attrName = "src";
                    else if (node.Name == "link")
                        attrName = "href";
                    // Skip <a> hrefs — they are navigation, not resources

                    if (attrName != null && node.Attributes.Contains(attrName))
                    {
                        string val = node.GetAttributeValue(attrName, "");

                        // Skip absolute URLs, data URIs, and anchors
                        if (val.StartsWith("http", StringComparison.OrdinalIgnoreCase) ||
                            val.StartsWith("data:", StringComparison.OrdinalIgnoreCase) ||
                            val.StartsWith("#") ||
                            val.StartsWith("mailto:") ||
                            val.StartsWith("tel:"))
                            continue;

                        // Split query string and fragment
                        string pathPart = val;
                        string queryPart = "";
                        string fragmentPart = "";

                        int queryIdx = val.IndexOf('?');
                        int fragIdx = val.IndexOf('#');

                        if (fragIdx >= 0)
                        {
                            fragmentPart = val.Substring(fragIdx);
                            if (queryIdx < 0 || queryIdx > fragIdx)
                                pathPart = val.Substring(0, fragIdx);
                            else
                            {
                                pathPart = val.Substring(0, queryIdx);
                                queryPart = val.Substring(queryIdx, fragIdx - queryIdx);
                            }
                        }
                        else if (queryIdx >= 0)
                        {
                            pathPart = val.Substring(0, queryIdx);
                            queryPart = val.Substring(queryIdx);
                        }

                        try
                        {
                            string targetAbsPath = Path.GetFullPath(Path.Combine(fileDir, pathPart));
                            string newRelativePath = Path.GetRelativePath(basePath, targetAbsPath).Replace("\\", "/");
                            node.SetAttributeValue(attrName, newRelativePath + queryPart + fragmentPart);
                        }
                        catch
                        {
                            // Keep original if path resolution fails
                        }
                    }
                }

                return doc.DocumentNode.InnerHtml;
            }
            catch
            {
                return html;
            }
        }

        private TocItem MapNavigationItem(EpubNavigationItem navItem)
        {
            var filePath = navItem.HtmlContentFile?.FilePath ?? "";
            var anchor = "";

            // Parse anchor from FilePath (e.g., "text/ch001.xhtml#chapter-6" → path + anchor)
            if (filePath.Contains('#'))
            {
                var parts = filePath.Split('#');
                filePath = parts[0];
                anchor = parts[1];
            }

            var item = new TocItem
            {
                Title = navItem.Title,
                FilePath = filePath,
                Anchor = anchor
            };

            if (navItem.NestedItems != null)
            {
                foreach (var nested in navItem.NestedItems)
                    item.NestedItems.Add(MapNavigationItem(nested));
            }

            return item;
        }

        private void FlattenToc(IEnumerable<TocItem> items)
        {
            foreach (var item in items)
            {
                _flatToc.Add(item);
                if (item.NestedItems != null && item.NestedItems.Any())
                    FlattenToc(item.NestedItems);
            }
        }

        private static void ExpandAllTocItems(ItemsControl itemsControl)
        {
            foreach (var item in itemsControl.Items)
            {
                var container = itemsControl.ItemContainerGenerator.ContainerFromItem(item) as System.Windows.Controls.TreeViewItem;
                if (container != null)
                {
                    container.IsExpanded = true;
                    if (container.HasItems)
                        ExpandAllTocItems(container);
                }
            }
        }

        private static void CollectNavigationPaths(IEnumerable<EpubNavigationItem> items, List<string> paths)
        {
            foreach (var item in items)
            {
                if (item.HtmlContentFile != null && !string.IsNullOrEmpty(item.HtmlContentFile.FilePath))
                    paths.Add(item.HtmlContentFile.FilePath);
                if (item.NestedItems != null)
                    CollectNavigationPaths(item.NestedItems, paths);
            }
        }

        private void TocTreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            if (e.NewValue is TocItem selectedItem)
            {
                // PRIMARY: always use title-based scroll (most reliable for single-file EPUBs)
                ScrollToChapterByTitle(selectedItem.Title);

                // Sync audio: find track by anchor or title
                SyncAudioToChapter(selectedItem);
            }

            // Clear search highlights on manual TOC navigation
            if (_isSearchHighlightActive)
                ClearSearchHighlights();
        }

        private void ScrollToChapterByTitle(string title)
        {
            if (WebView?.CoreWebView2 == null || string.IsNullOrEmpty(title)) return;

            string escaped = EscapeJsString(title);
            string js = $@"
                (function() {{
                    var title = '{escaped}';
                    // Method 1: find heading with exact text match
                    var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    for (var i = 0; i < headings.length; i++) {{
                        var text = headings[i].textContent.trim();
                        if (text === title || text.indexOf(title) === 0) {{
                            headings[i].scrollIntoView({{behavior: 'smooth', block: 'start'}});
                            return;
                        }}
                    }}
                    // Method 2: find by partial text match
                    for (var i = 0; i < headings.length; i++) {{
                        if (headings[i].textContent.indexOf(title) >= 0) {{
                            headings[i].scrollIntoView({{behavior: 'smooth', block: 'start'}});
                            return;
                        }}
                    }}
                    // Method 3: find by id containing title
                    var id = title.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
                    var el = document.getElementById(id);
                    if (!el) {{
                        var all = document.querySelectorAll('[id]');
                        for (var i = 0; i < all.length; i++) {{
                            if (all[i].id.indexOf(id) >= 0) {{
                                all[i].scrollIntoView({{behavior: 'smooth', block: 'start'}});
                                return;
                            }}
                        }}
                    }}
                    if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                }})();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void ScrollToChapter(string tocFilePath, string title = "")
        {
            if (WebView?.CoreWebView2 == null) return;
            if (string.IsNullOrEmpty(tocFilePath)) return;

            string pathOnly = tocFilePath;
            string anchor = "";
            if (pathOnly.Contains("#"))
            {
                var parts = pathOnly.Split('#');
                pathOnly = parts[0];
                anchor = parts[1];
            }

            System.Diagnostics.Debug.WriteLine($"ScrollToChapter: path={pathOnly}, anchor={anchor}, title={title}");
            System.Diagnostics.Debug.WriteLine($"  _pathToChapterId count={_pathToChapterId.Count}, keys=[{string.Join(", ", _pathToChapterId.Keys)}]");

            // Normalize path separators for matching
            string normalizedPath = pathOnly.Replace("\\", "/").ToLowerInvariant();

            // Try exact match first
            if (_pathToChapterId.TryGetValue(pathOnly, out int chapterId))
            {
                System.Diagnostics.Debug.WriteLine($"  Exact match: chapterId={chapterId}");
                ScrollToChapterId(chapterId, anchor, title);
                return;
            }

            // Try normalized match
            foreach (var kvp in _pathToChapterId)
            {
                if (kvp.Key.Replace("\\", "/").ToLowerInvariant() == normalizedPath)
                {
                    System.Diagnostics.Debug.WriteLine($"  Normalized match: chapterId={kvp.Value}");
                    ScrollToChapterId(kvp.Value, anchor, title);
                    return;
                }
            }

            System.Diagnostics.Debug.WriteLine($"  NO MATCH FOUND for path={pathOnly}");
        }

        private void ScrollToChapterId(int chapterId, string anchor = "", string title = "")
        {
            if (WebView?.CoreWebView2 == null) return;

            string js;
            if (!string.IsNullOrEmpty(anchor))
            {
                // Try multiple ways to find the element (URL-decoded, exact, partial)
                var decodedAnchor = Uri.UnescapeDataString(anchor).Replace("+", " ");
                var escapedTitle = EscapeJsString(title);
                js = $@"
                    (function() {{
                        var id = '{EscapeJsString(anchor)}';
                        var decoded = '{EscapeJsString(decodedAnchor)}';
                        var title = '{escapedTitle}';
                        // Try 1: exact ID
                        var el = document.getElementById(id);
                        // Try 2: URL-decoded ID
                        if (!el) el = document.getElementById(decoded);
                        // Try 3: querySelector with attribute contains
                        if (!el) {{
                            var all = document.querySelectorAll('[id]');
                            for (var i = 0; i < all.length; i++) {{
                                if (all[i].id.indexOf(decoded) >= 0 || all[i].id.indexOf(id) >= 0) {{
                                    el = all[i];
                                    break;
                                }}
                            }}
                        }}
                        // Try 4: find heading by text content
                        if (!el && title) {{
                            var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                            for (var i = 0; i < headings.length; i++) {{
                                if (headings[i].textContent.indexOf(title) >= 0) {{
                                    el = headings[i];
                                    break;
                                }}
                            }}
                        }}
                        if (el) {{
                            el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        }} else {{
                            // Final fallback: scroll to chapter div
                            var chap = document.getElementById('chap_{chapterId}');
                            if (chap) chap.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        }}
                    }})();
                ";
            }
            else
            {
                js = $"document.getElementById('chap_{chapterId}').scrollIntoView({{behavior: 'smooth', block: 'start'}});";
            }
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void SyncAudioToChapter(TocItem tocItem)
        {
            if (_audioFiles.Count == 0) return;

            int audioIndex = -1;

            // Extract chapter number from title (e.g., "Chương 3: Tâm tư..." → 3)
            if (!string.IsNullOrEmpty(tocItem.Title))
            {
                var match = System.Text.RegularExpressions.Regex.Match(tocItem.Title, @"Chương\s+(\d+)", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                if (match.Success && int.TryParse(match.Groups[1].Value, out int chapterNum))
                {
                    // Audio files: ch01.mp3, ch02.mp3, ... → index = chapterNum - 1
                    audioIndex = chapterNum - 1;
                }
            }

            if (audioIndex >= 0 && audioIndex < _audioFiles.Count)
            {
                _currentTrackIndex = audioIndex;
                LoadTrack(audioIndex);
                // Show play button (don't auto-play when switching chapters)
                if (_timer?.IsEnabled == true)
                {
                    _mediaPlayer?.Pause();
                    _timer.Stop();
                }
                BtnAudioPlay.Content = "\uE768"; // Play icon (triangle)
            }
        }

        private void WebView_NavigationCompleted(object sender, Microsoft.Web.WebView2.Core.CoreWebView2NavigationCompletedEventArgs e)
        {
            if (e.IsSuccess)
            {
                // Re-apply theme CSS variables (for manual refresh)
                ReapplyThemeColors();
                // Apply typography settings from Toolbar
                ApplyTypographySettings();
                // Inject keyboard navigation script and scroll observer
                InjectKeyboardNavScript();
                // Restore previous reading position
                RestoreReadingProgressAsync();
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

        private void CmbFont_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            ApplyTypographySettings();
        }

        private void CmbWidth_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            ApplyTypographySettings();
        }

        private void CmbLineHeight_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            ApplyTypographySettings();
        }

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

        /// <summary>
        /// Reads a theme brush from application resources, but only trusts it when the
        /// color is actually usable (not white/near-transparent defaults). Falls back to
        /// a fixed dark-theme palette otherwise, so the reader pane never renders
        /// white-on-white even if the WPF-UI resource doesn't resolve correctly.
        /// </summary>
        private static Color GetSafeColor(string resourceKey, Color fallback, bool allowLight, double maxLuminance = 255)
        {
            try
            {
                if (Application.Current.Resources[resourceKey] is SolidColorBrush brush)
                {
                    var c = brush.Color;
                    // Near-transparent colors (alpha near 0) are unresolved defaults
                    if (c.A < 0x40) return fallback;
                    double lum = (0.299 * c.R + 0.587 * c.G + 0.114 * c.B);
                    if (!allowLight && lum > 128) return fallback;   // background must stay dark
                    if (allowLight && lum > maxLuminance) return fallback; // reject over-bright fg
                    return c;
                }
            }
            catch
            {
                // fall through to fallback
            }
            return fallback;
        }

        private static string ColorToHex(Color color) =>
            "#" + color.R.ToString("X2") + color.G.ToString("X2") + color.B.ToString("X2");

        private void InjectKeyboardNavScript()
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = @"
                (function() {
                    if (window.__keyNavInjected) return;
                    window.__keyNavInjected = true;

                    // Keyboard navigation
                    document.addEventListener('keydown', function(e) {
                        var active = document.activeElement;
                        if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) return;

                        if (e.key === 'ArrowDown') {
                            window.chrome.webview.postMessage(JSON.stringify({action: 'nextChapter'}));
                            e.preventDefault();
                        } else if (e.key === 'ArrowUp') {
                            window.chrome.webview.postMessage(JSON.stringify({action: 'prevChapter'}));
                            e.preventDefault();
                        } else if (e.key === ' ') {
                            window.chrome.webview.postMessage(JSON.stringify({action: 'playPause'}));
                            e.preventDefault();
                        } else if (e.key === 'Escape') {
                            window.chrome.webview.postMessage(JSON.stringify({action: 'escape'}));
                            e.preventDefault();
                        }
                    });

                    // Scroll tracking for Auto-Resume Bookmark
                    var scrollDebounceTimer;
                    window.addEventListener('scroll', function() {
                        clearTimeout(scrollDebounceTimer);
                        scrollDebounceTimer = setTimeout(function() {
                            var y = window.pageYOffset || document.documentElement.scrollTop;
                            var total = document.documentElement.scrollHeight - window.innerHeight;
                            var pct = total > 0 ? Math.min(100, Math.max(0, Math.round((y / total) * 100))) : 0;
                            window.chrome.webview.postMessage(JSON.stringify({
                                action: 'updateScrollPosition',
                                scrollY: y,
                                percent: pct
                            }));
                        }, 400);
                    });
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void WebView_WebMessageReceived(object sender, Microsoft.Web.WebView2.Core.CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                var msg = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(e.WebMessageAsJson);
                if (msg != null && msg.TryGetValue("action", out JsonElement actionElem) && actionElem.ValueKind == JsonValueKind.String)
                {
                    string? action = actionElem.GetString();
                    switch (action)
                    {
                        case "nextChapter":
                            ScrollToNextChapter();
                            break;
                        case "prevChapter":
                            ScrollToPrevChapter();
                            break;
                        case "playPause":
                            BtnAudioPlayPause_Click(null, new RoutedEventArgs());
                            break;
                        case "escape":
                            Close();
                            break;
                        case "updateScrollPosition":
                            if (msg.TryGetValue("scrollY", out JsonElement yElem) && yElem.TryGetDouble(out double scrollY))
                            {
                                int pct = 0;
                                if (msg.TryGetValue("percent", out JsonElement pctElem))
                                    pct = pctElem.GetInt32();
                                SaveReadingProgress(scrollY, pct);
                            }
                            break;
                    }
                }
            }
            catch
            {
                // Ignore malformed messages
            }
        }

        private static string GetProgressFilePath()
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TranslateBook");
            Directory.CreateDirectory(dir);
            return Path.Combine(dir, "reading_bookmarks.json");
        }

        private void SaveReadingProgress(double scrollY, int percent)
        {
            if (string.IsNullOrEmpty(_epubFilePath)) return;

            TxtReadingProgress.Text = $"Tiến độ: {percent}%";

            Task.Run(() =>
            {
                try
                {
                    var file = GetProgressFilePath();
                    Dictionary<string, double> dict = new();
                    if (File.Exists(file))
                    {
                        var json = File.ReadAllText(file);
                        dict = JsonSerializer.Deserialize<Dictionary<string, double>>(json) ?? new();
                    }
                    dict[_epubFilePath] = scrollY;
                    File.WriteAllText(file, JsonSerializer.Serialize(dict));
                }
                catch
                {
                    // Ignore background bookmark write failures
                }
            });
        }

        private async void RestoreReadingProgressAsync()
        {
            if (string.IsNullOrEmpty(_epubFilePath) || WebView?.CoreWebView2 == null) return;

            try
            {
                var file = GetProgressFilePath();
                if (!File.Exists(file)) return;

                var json = await File.ReadAllTextAsync(file);
                var dict = JsonSerializer.Deserialize<Dictionary<string, double>>(json);
                if (dict != null && dict.TryGetValue(_epubFilePath, out double savedScrollY) && savedScrollY > 10)
                {
                    // Delay slightly to ensure DOM layout is fully stable
                    await Task.Delay(250);
                    string js = $"window.scrollTo({{top: {savedScrollY}, behavior: 'smooth'}});";
                    await WebView.CoreWebView2.ExecuteScriptAsync(js);
                }
            }
            catch
            {
                // Ignore restore errors
            }
        }

        private void ScrollToNextChapter()
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = @"
                (function() {
                    var current = window.pageYOffset || document.documentElement.scrollTop;
                    var chapters = document.querySelectorAll('div[id^=""chap_""]');
                    var next = null;
                    for (var i = 0; i < chapters.length; i++) {
                        var rect = chapters[i].getBoundingClientRect();
                        var offsetTop = rect.top + window.pageYOffset;
                        if (offsetTop > current + 50) {
                            next = chapters[i];
                            break;
                        }
                    }
                    if (next) next.scrollIntoView({behavior: 'smooth', block: 'start'});
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void ScrollToPrevChapter()
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = @"
                (function() {
                    var current = window.pageYOffset || document.documentElement.scrollTop;
                    var chapters = document.querySelectorAll('div[id^=""chap_""]');
                    var prev = null;
                    for (var i = chapters.length - 1; i >= 0; i--) {
                        var rect = chapters[i].getBoundingClientRect();
                        var offsetTop = rect.top + window.pageYOffset;
                        if (offsetTop < current - 50) {
                            prev = chapters[i];
                        }
                    }
                    if (prev) prev.scrollIntoView({behavior: 'smooth', block: 'start'});
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Handled) return;

            switch (e.Key)
            {
                case Key.F5:
                    ReapplyThemeColors();
                    ZoomPercent.Text = $"{(int)ZoomSlider.Value}%";
                    e.Handled = true;
                    break;
            }
        }

        // --- Search ---

        private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            string searchTerm = SearchBox.Text.Trim();
            if (string.IsNullOrEmpty(searchTerm))
            {
                ClearSearchHighlights();
                _isSearchHighlightActive = false;
            }
            else
            {
                HighlightSearchTerm(searchTerm);
                _isSearchHighlightActive = true;
            }
        }

        private void ClearSearchHighlights()
        {
            if (WebView?.CoreWebView2 == null) return;
            string js = @"
                (function() {
                    var highlights = document.querySelectorAll('.search-highlight');
                    highlights.forEach(function(el) {
                        var parent = el.parentNode;
                        if (parent) {
                            var text = document.createTextNode(el.textContent);
                            while (el.firstChild) {
                                text.appendChild(el.firstChild);
                            }
                            parent.replaceChild(text, el);
                        }
                    });
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void HighlightSearchTerm(string term)
        {
            if (WebView?.CoreWebView2 == null) return;
            ClearSearchHighlights();
            string escaped = EscapeJsString(term);

            string js = $@"
                (function() {{
                    var term = '{escaped}';
                    if (!term) return;
                    var safeTerm = term.replace(/[.*+?^${{}}()|[\]\\]/g, '\\$&');
                    var regex = new RegExp(safeTerm, 'gi');
                    var body = document.querySelector('body');
                    if (!body) return;
                    var walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null, false);
                    var nodes = [];
                    var node;
                    while (node = walker.nextNode()) {{
                        if (node.nodeValue && node.nodeValue.trim().length > 0 && regex.test(node.nodeValue))
                            nodes.push(node);
                    }}
                    regex.lastIndex = 0;
                    nodes.forEach(function(textNode) {{
                        var content = textNode.nodeValue;
                        var matches = [];
                        var match;
                        var re = new RegExp(safeTerm, 'gi');
                        while (match = re.exec(content)) {{
                            matches.push({{start: match.index, end: match.index + match[0].length}});
                        }}
                        if (matches.length === 0) return;

                        var frag = document.createDocumentFragment();
                        var lastIndex = 0;
                        matches.forEach(function(m) {{
                            if (m.start > lastIndex)
                                frag.appendChild(document.createTextNode(content.slice(lastIndex, m.start)));
                            var span = document.createElement('span');
                            span.className = 'search-highlight';
                            span.textContent = content.slice(m.start, m.end);
                            frag.appendChild(span);
                            lastIndex = m.end;
                        }});
                        if (lastIndex < content.length)
                            frag.appendChild(document.createTextNode(content.slice(lastIndex)));
                        textNode.parentNode.replaceChild(frag, textNode);
                    }});
                }})();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void BtnSearchNext_Click(object sender, RoutedEventArgs e)
        {
            if (!_isSearchHighlightActive) return;
            if (WebView?.CoreWebView2 == null) return;

            string js = @"
                (function() {
                    var highlights = document.querySelectorAll('.search-highlight');
                    if (highlights.length === 0) return;
                    var current = window.pageYOffset || document.documentElement.scrollTop;
                    var best = null;
                    var bestDist = Infinity;
                    for (var i = 0; i < highlights.length; i++) {
                        var r = highlights[i].getBoundingClientRect();
                        var offsetTop = r.top + window.pageYOffset;
                        var dist = offsetTop - current;
                        if (dist >= -50 && dist < bestDist) {
                            bestDist = dist;
                            best = highlights[i];
                        }
                    }
                    if (!best) best = highlights[0];
                    best.scrollIntoView({behavior: 'smooth', block: 'center'});
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        private void BtnSearchPrev_Click(object sender, RoutedEventArgs e)
        {
            if (!_isSearchHighlightActive) return;
            if (WebView?.CoreWebView2 == null) return;

            string js = @"
                (function() {
                    var highlights = document.querySelectorAll('.search-highlight');
                    if (highlights.length === 0) return;
                    var current = window.pageYOffset || document.documentElement.scrollTop;
                    var best = null;
                    var bestDist = Infinity;
                    for (var i = highlights.length - 1; i >= 0; i--) {
                        var r = highlights[i].getBoundingClientRect();
                        var offsetTop = r.top + window.pageYOffset;
                        var dist = current - offsetTop;
                        if (dist >= -50 && dist < bestDist) {
                            bestDist = dist;
                            best = highlights[i];
                        }
                    }
                    if (!best) best = highlights[highlights.length - 1];
                    best.scrollIntoView({behavior: 'smooth', block: 'center'});
                })();
            ";
            WebView.CoreWebView2.ExecuteScriptAsync(js);
        }

        // --- Zoom ---

        private void ZoomSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            int percent = (int)e.NewValue;
            if (ZoomPercent != null)
                ZoomPercent.Text = $"{percent}%";

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

            if (core.Source != null)
                core.Reload();
            else
                ReapplyThemeColors();
        }

        // --- Helper ---

        private static string EscapeJsString(string s)
        {
            return s.Replace("\\", "\\\\").Replace("'", "\\'").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "");
        }

        // --- Audio Player ---

        private void InitAudioPlayer()
        {
            try
            {
                var bookDir = Path.GetDirectoryName(_epubFilePath);
                if (bookDir == null) return;

                var audioDir = Path.Combine(bookDir, "audiobook");
                if (Directory.Exists(audioDir))
                {
                    var files = Directory.GetFiles(audioDir, "*.mp3").OrderBy(f => f).ToList();
                    if (files.Count > 0)
                        _audioFiles = files;
                }

                if (_audioFiles.Count == 0) return;

                _mediaPlayer = new MediaPlayer();
                _mediaPlayer.MediaEnded += MediaPlayer_MediaEnded;
                _mediaPlayer.MediaOpened += MediaPlayer_MediaOpened;

                _timer = new DispatcherTimer();
                _timer.Interval = TimeSpan.FromMilliseconds(500);
                _timer.Tick += Timer_Tick;

                AudioBar.Visibility = Visibility.Visible;
                VolumeSlider.Value = 0.8;
                _mediaPlayer.Volume = 0.8;

                LoadTrack(0);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Audio init error: {ex.Message}");
            }
        }

        private void LoadTrack(int index)
        {
            if (index < 0 || index >= _audioFiles.Count || _mediaPlayer == null) return;

            _currentTrackIndex = index;

            try
            {
                _mediaPlayer.Open(new Uri(_audioFiles[index]));
                AudioSlider.Value = 0;

                // Get chapter name from audio file → find matching TOC title
                var audioName = Path.GetFileNameWithoutExtension(_audioFiles[index]);
                var numMatch = System.Text.RegularExpressions.Regex.Match(audioName, @"(\d+)");
                if (numMatch.Success && int.TryParse(numMatch.Groups[1].Value, out int chNum))
                {
                    // Find TOC item with matching chapter number
                    var tocItem = _flatToc.FirstOrDefault(t =>
                        System.Text.RegularExpressions.Regex.IsMatch(t.Title, $@"Chương\s+{chNum}\b",
                            System.Text.RegularExpressions.RegexOptions.IgnoreCase));
                    AudioChapterName.Text = tocItem?.Title ?? $"Chương {chNum}";
                }
                else
                {
                    AudioChapterName.Text = audioName;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading audio track {index}: {ex.Message}");
            }
        }

        private void MediaPlayer_MediaOpened(object? sender, EventArgs e)
        {
            if (_mediaPlayer != null && _mediaPlayer.NaturalDuration.HasTimeSpan)
            {
                AudioSlider.Maximum = _mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds;
                AudioTimeTotal.Text = _mediaPlayer.NaturalDuration.TimeSpan.ToString(@"mm\:ss");
            }
        }

        private void MediaPlayer_MediaEnded(object? sender, EventArgs e)
        {
            BtnAudioNext_Click(this, new RoutedEventArgs());
        }

        private void Timer_Tick(object? sender, EventArgs e)
        {
            if (!_isDraggingSlider && _mediaPlayer != null && _mediaPlayer.Source != null && _mediaPlayer.NaturalDuration.HasTimeSpan)
            {
                AudioSlider.Value = _mediaPlayer.Position.TotalSeconds;
                AudioTimeCurrent.Text = _mediaPlayer.Position.ToString(@"mm\:ss");
            }
        }

        private void BtnAudioPlayPause_Click(object? sender, RoutedEventArgs e)
        {
            if (_mediaPlayer == null || _timer == null) return;

            if (_timer.IsEnabled)
            {
                _mediaPlayer.Pause();
                _timer.Stop();
                BtnAudioPlay.Content = "\uE768"; // Play icon
            }
            else
            {
                _mediaPlayer.Play();
                _timer.Start();
                BtnAudioPlay.Content = "\uE769"; // Pause icon
            }
        }

        private void BtnAudioPrev_Click(object? sender, RoutedEventArgs e)
        {
            if (_currentTrackIndex > 0)
            {
                bool wasPlaying = _timer?.IsEnabled ?? false;
                LoadTrack(_currentTrackIndex - 1);
                if (wasPlaying && _mediaPlayer != null) _mediaPlayer.Play();
            }
        }

        private void BtnAudioNext_Click(object? sender, RoutedEventArgs e)
        {
            if (_currentTrackIndex < _audioFiles.Count - 1)
            {
                bool wasPlaying = _timer?.IsEnabled ?? false;
                LoadTrack(_currentTrackIndex + 1);
                if (wasPlaying && _mediaPlayer != null) _mediaPlayer.Play();
            }
            else
            {
                // Reached the end of the book
                if (_mediaPlayer != null) _mediaPlayer.Stop();
                if (_timer?.IsEnabled == true) _timer.Stop();
                BtnAudioPlay.Content = "\uE768"; // Play icon
            }
        }

        private void AudioSlider_DragStarted(object sender, System.Windows.Controls.Primitives.DragStartedEventArgs e)
        {
            _isDraggingSlider = true;
        }

        private void AudioSlider_DragCompleted(object sender, System.Windows.Controls.Primitives.DragCompletedEventArgs e)
        {
            _isDraggingSlider = false;
            if (_mediaPlayer != null && _mediaPlayer.Source != null)
                _mediaPlayer.Position = TimeSpan.FromSeconds(AudioSlider.Value);
        }

        private void AudioSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_isDraggingSlider && _mediaPlayer != null)
                AudioTimeCurrent.Text = TimeSpan.FromSeconds(AudioSlider.Value).ToString(@"mm\:ss");
        }

        private void VolumeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_mediaPlayer != null)
                _mediaPlayer.Volume = VolumeSlider.Value;
        }

        private void EpubPreviewWindow_Closed(object? sender, EventArgs e)
        {
            try
            {
                _timer?.Stop();

                if (_mediaPlayer != null)
                {
                    _mediaPlayer.MediaEnded -= MediaPlayer_MediaEnded;
                    _mediaPlayer.MediaOpened -= MediaPlayer_MediaOpened;
                    _mediaPlayer.Stop();
                    _mediaPlayer.Close();
                    _mediaPlayer = null;
                }

                if (Directory.Exists(_tempExtractPath))
                    Directory.Delete(_tempExtractPath, true);
            }
            catch
            {
                // Best effort cleanup
            }
        }
    }
}
