using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using TranslateBook.Models;
using VersOne.Epub;

namespace TranslateBook.Views
{
    public partial class EpubPreviewWindow : Window
    {
        private string _epubFilePath;
        private string _tempExtractPath;
        
        private MediaPlayer? _mediaPlayer;
        private DispatcherTimer? _timer;
        private List<string> _audioFiles = new();
        private int _currentTrackIndex = -1;
        private bool _isDraggingSlider = false;

        public EpubPreviewWindow(string epubFilePath)
        {
            InitializeComponent();
            _epubFilePath = epubFilePath;
            _tempExtractPath = Path.Combine(Path.GetTempPath(), "TranslateBook_EpubPreview_" + Guid.NewGuid().ToString());
            
            Loaded += EpubPreviewWindow_Loaded;
            Closed += EpubPreviewWindow_Closed;
        }

        private async void EpubPreviewWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                await WebView.EnsureCoreWebView2Async(null);
                
                // Read and extract EPUB
                EpubBook book = await EpubReader.ReadBookAsync(_epubFilePath);
                
                if (Directory.Exists(_tempExtractPath))
                    Directory.Delete(_tempExtractPath, true);
                
                ZipFile.ExtractToDirectory(_epubFilePath, _tempExtractPath);

                var toc = new List<TocItem>();
                if (book.Navigation != null)
                {
                    foreach (var navItem in book.Navigation)
                    {
                        toc.Add(MapNavigationItem(navItem));
                    }
                }
                
                TocTreeView.ItemsSource = toc;

                // Build reading order
                if (book.ReadingOrder != null)
                {
                    foreach (var roItem in book.ReadingOrder)
                    {
                        if (roItem != null && !string.IsNullOrEmpty(roItem.FilePath))
                        {
                            _readingOrderPaths.Add(roItem.FilePath);
                        }
                    }
                }

                // Generate fullbook.html
                _fullBookHtmlPath = Path.Combine(_tempExtractPath, "fullbook.html");
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>");

                int chapterIndex = 0;
                foreach (var relativePath in _readingOrderPaths)
                {
                    string absolutePath = Path.GetFullPath(Path.Combine(_tempExtractPath, relativePath));
                    if (File.Exists(absolutePath))
                    {
                        string html = File.ReadAllText(absolutePath);
                        var match = System.Text.RegularExpressions.Regex.Match(html, @"<body[^>]*>(.*?)</body>", System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.Singleline);
                        
                        string body = match.Success ? match.Groups[1].Value : html;
                        
                        string fileDir = Path.GetDirectoryName(absolutePath)!;
                        body = System.Text.RegularExpressions.Regex.Replace(body, @"(src|href)\s*=\s*['""]([^'""#:]+)['""]", m =>
                        {
                            string attr = m.Groups[1].Value;
                            string val = m.Groups[2].Value;
                            if (val.StartsWith("http", StringComparison.OrdinalIgnoreCase) || val.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
                                return m.Value;
                            
                            try
                            {
                                string targetAbsPath = Path.GetFullPath(Path.Combine(fileDir, val));
                                string newRelativePath = Path.GetRelativePath(_tempExtractPath, targetAbsPath).Replace("\\", "/");
                                return $"{attr}=\"{newRelativePath}\"";
                            }
                            catch
                            {
                                return m.Value;
                            }
                        });

                        sb.AppendLine($"<div id='chap_{chapterIndex}'>");
                        sb.AppendLine(body);
                        sb.AppendLine("</div>");
                    }
                    chapterIndex++;
                }
                sb.AppendLine("</body></html>");
                File.WriteAllText(_fullBookHtmlPath, sb.ToString());

                // Navigate to the full book
                WebView.CoreWebView2.SetVirtualHostNameToFolderMapping("translatebook.local", _tempExtractPath, Microsoft.Web.WebView2.Core.CoreWebView2HostResourceAccessKind.Allow);

                InitAudioPlayer();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Lỗi khi mở EPUB: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private TocItem MapNavigationItem(EpubNavigationItem navItem)
        {
            var item = new TocItem
            {
                Title = navItem.Title,
                FilePath = navItem.HtmlContentFile?.FilePath ?? ""
            };

            if (navItem.NestedItems != null)
            {
                foreach (var nested in navItem.NestedItems)
                {
                    item.NestedItems.Add(MapNavigationItem(nested));
                }
            }

            return item;
        }

        private void TocTreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            if (e.NewValue is TocItem selectedItem && !string.IsNullOrEmpty(selectedItem.FilePath))
            {
                ScrollToChapter(selectedItem.FilePath);
            }
        }

        private List<string> _readingOrderPaths = new();
        private string _fullBookHtmlPath = "";

        private void ScrollToChapter(string tocFilePath)
        {
            if (string.IsNullOrEmpty(tocFilePath)) return;

            string pathOnly = tocFilePath;
            string anchor = "";
            if (pathOnly.Contains("#"))
            {
                var parts = pathOnly.Split('#');
                pathOnly = parts[0];
                anchor = parts[1];
            }

            int idx = _readingOrderPaths.IndexOf(pathOnly);
            if (idx >= 0)
            {
                string js = "";
                if (!string.IsNullOrEmpty(anchor))
                {
                    js = $"var el = document.getElementById('{anchor}'); if(el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}}); else document.getElementById('chap_{idx}').scrollIntoView({{behavior: 'smooth', block: 'start'}});";
                }
                else
                {
                    js = $"document.getElementById('chap_{idx}').scrollIntoView({{behavior: 'smooth', block: 'start'}});";
                }
                WebView.CoreWebView2.ExecuteScriptAsync(js);
            }
        }

        private async void WebView_NavigationCompleted(object sender, Microsoft.Web.WebView2.Core.CoreWebView2NavigationCompletedEventArgs e)
        {
            if (e.IsSuccess)
            {
                // Inject CSS for Dark Mode and Styling
                string css = @"
                    body {
                        background-color: #202020 !important;
                        color: #E0E0E0 !important;
                        font-family: 'Segoe UI', Arial, sans-serif !important;
                        line-height: 1.6 !important;
                        margin: 0 auto !important;
                        padding: 20px !important;
                        overflow-y: auto !important;
                        overflow-x: hidden !important;
                        max-width: 800px !important;
                    }
                    a { color: #60CDFF !important; }
                    img { max-width: 100% !important; height: auto !important; }
                ";
                
                string injectScript = $@"
                    var style = document.createElement('style');
                    style.innerHTML = `{css}`;
                    document.head.appendChild(style);
                ";

                await WebView.CoreWebView2.ExecuteScriptAsync(injectScript);
            }
        }

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ClickCount == 2)
                ToggleMaximize();
            else
                DragMove();
        }

        private void BtnMinimize_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
        
        private void BtnMaximize_Click(object sender, RoutedEventArgs e) => ToggleMaximize();
        
        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();

        private void ToggleMaximize()
        {
            if (WindowState == WindowState.Maximized)
            {
                WindowState = WindowState.Normal;
                BtnMaximize.Content = "☐";
            }
            else
            {
                WindowState = WindowState.Maximized;
                BtnMaximize.Content = "❐";
            }
        }

        // ==========================================
        // AUDIO PLAYER LOGIC
        // ==========================================

        private void InitAudioPlayer()
        {
            try
            {
                var bookDir = Path.GetDirectoryName(_epubFilePath);
                if (bookDir != null)
                {
                    var audioDir = Path.Combine(bookDir, "audiobook");
                    if (Directory.Exists(audioDir))
                    {
                        var files = Directory.GetFiles(audioDir, "*.mp3").OrderBy(f => f).ToList();
                        if (files.Count > 0)
                        {
                            _audioFiles = files;
                            
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
                    }
                }
            }
            catch { }
        }

        private void LoadTrack(int index)
        {
            if (index >= 0 && index < _audioFiles.Count && _mediaPlayer != null)
            {
                _currentTrackIndex = index;
                _mediaPlayer.Open(new Uri(_audioFiles[index]));
                AudioChapterName.Text = Path.GetFileNameWithoutExtension(_audioFiles[index]);
                AudioSlider.Value = 0;
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
            BtnAudioNext_Click(null, null);
        }

        private void Timer_Tick(object? sender, EventArgs e)
        {
            if (!_isDraggingSlider && _mediaPlayer != null && _mediaPlayer.Source != null && _mediaPlayer.NaturalDuration.HasTimeSpan)
            {
                AudioSlider.Value = _mediaPlayer.Position.TotalSeconds;
                AudioTimeCurrent.Text = _mediaPlayer.Position.ToString(@"mm\:ss");
            }
        }

        private void BtnAudioPlayPause_Click(object sender, RoutedEventArgs e)
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
                if (wasPlaying && _mediaPlayer != null) { _mediaPlayer.Play(); }
            }
        }

        private void BtnAudioNext_Click(object? sender, RoutedEventArgs e)
        {
            if (_currentTrackIndex < _audioFiles.Count - 1)
            {
                bool wasPlaying = _timer?.IsEnabled ?? false;
                LoadTrack(_currentTrackIndex + 1);
                if (wasPlaying && _mediaPlayer != null) { _mediaPlayer.Play(); }
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
            {
                _mediaPlayer.Position = TimeSpan.FromSeconds(AudioSlider.Value);
            }
        }

        private void AudioSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_isDraggingSlider && _mediaPlayer != null)
            {
                AudioTimeCurrent.Text = TimeSpan.FromSeconds(AudioSlider.Value).ToString(@"mm\:ss");
            }
        }

        private void VolumeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_mediaPlayer != null)
            {
                _mediaPlayer.Volume = VolumeSlider.Value;
            }
        }

        private void EpubPreviewWindow_Closed(object? sender, EventArgs e)
        {
            try
            {
                if (_mediaPlayer != null)
                {
                    _mediaPlayer.Stop();
                    _mediaPlayer.Close();
                }
                
                if (Directory.Exists(_tempExtractPath))
                    Directory.Delete(_tempExtractPath, true);
            }
            catch { }
        }
    }
}
