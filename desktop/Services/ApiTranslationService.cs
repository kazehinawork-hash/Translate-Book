using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using TranslateBook.Models;

namespace TranslateBook.Services;

public class ApiTranslationService
{
    // Timeout kiểm soát theo từng loại request (không dùng 1 mức cứng toàn cục cho mọi thứ):
    // - Dịch chunk: 180s/request (chunk 1500-3000 ký tự, model thường trả trong 30-90s; 180s là dư giả)
    // - GET /models, test kết nối: 45s (tránh treo 5 phút khi endpoint chết)
    private readonly HttpClient _http = new() { Timeout = System.Threading.Timeout.InfiniteTimeSpan };

    /// <summary>Gửi request kèm timeout riêng. Hết giờ (không do user hủy) → TimeoutException để vòng retry xử lý.</summary>
    private async Task<HttpResponseMessage> SendWithTimeoutAsync(
        HttpRequestMessage request, TimeSpan timeout, CancellationToken ct)
    {
        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeoutCts.CancelAfter(timeout);
        try
        {
            return await _http.SendAsync(request, timeoutCts.Token);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw new TimeoutException($"API không phản hồi trong {timeout.TotalSeconds:0} giây");
        }
    }

    public void CancelPendingRequests()
    {
        try
        {
            _http.CancelPendingRequests();
        }
        catch { }
    }

    public record TranslationResult(string Text, string Model, string Provider,
        int TokensIn = 0, int TokensOut = 0);

    public static string LoadGlossary(string slug, string projectRoot, string filterText = "")
    {
        var glossaryDir = Path.Combine(projectRoot, "glossary");
        if (!Directory.Exists(glossaryDir)) return "";

        try
        {
            var masterFiles = Directory.GetFiles(glossaryDir, "master*.csv").OrderBy(f => f).ToList();
            if (masterFiles.Count == 0) return "";

            var normSlug = System.Text.RegularExpressions.Regex.Replace((slug ?? "").ToLower().Trim(), @"[^a-z0-9]+", "-").Trim('-');
            var allRows = new List<(string source, string target, string type, string note, string book, string author, string genre)>();

            foreach (var mf in masterFiles)
            {
                var lines = File.ReadAllLines(mf, Encoding.UTF8);
                bool isFirst = true;
                foreach (var line in lines)
                {
                    if (string.IsNullOrWhiteSpace(line)) continue;
                    if (isFirst) { isFirst = false; continue; } // Bỏ qua header

                    var parts = line.Split(',');
                    if (parts.Length >= 2)
                    {
                        var src = parts[0].Trim();
                        var tgt = parts[1].Trim();
                        var type = parts.Length > 2 ? parts[2].Trim() : "";
                        var note = parts.Length > 3 ? parts[3].Trim() : "";
                        var book = parts.Length > 4 ? System.Text.RegularExpressions.Regex.Replace(parts[4].ToLower().Trim(), @"[^a-z0-9]+", "-").Trim('-') : "";
                        var author = parts.Length > 5 ? System.Text.RegularExpressions.Regex.Replace(parts[5].ToLower().Trim(), @"[^a-z0-9]+", "-").Trim('-') : "";
                        var genre = parts.Length > 6 ? System.Text.RegularExpressions.Regex.Replace(parts[6].ToLower().Trim(), @"[^a-z0-9]+", "-").Trim('-') : "";

                        if (!string.IsNullOrEmpty(src) && !string.IsNullOrEmpty(tgt))
                        {
                            // Nếu có filterText (đoạn cần dịch), chỉ nạp thuật ngữ nếu nó thực sự có trong văn bản
                            if (!string.IsNullOrEmpty(filterText) && !filterText.Contains(src, StringComparison.OrdinalIgnoreCase))
                                continue;

                            allRows.Add((src, tgt, type, note, book, author, genre));
                        }
                    }
                }
            }

            // Tìm tác giả & thể loại của cuốn sách này từ các mục đã gán
            string authorOfBook = allRows.FirstOrDefault(r => r.book == normSlug && !string.IsNullOrEmpty(r.author)).author ?? "";
            string genreOfBook = allRows.FirstOrDefault(r => r.book == normSlug && !string.IsNullOrEmpty(r.genre)).genre ?? "";

            var sb = new StringBuilder();
            sb.AppendLine("Thuật ngữ gốc (Source) -> Bản dịch chuẩn (Target):");

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            // Ưu tiên 1: Thuật ngữ riêng của cuốn sách
            foreach (var r in allRows.Where(r => r.book == normSlug))
            {
                if (seen.Add(r.source))
                {
                    var noteStr = !string.IsNullOrEmpty(r.note) ? $" ({r.note})" : "";
                    sb.AppendLine($"• {r.source} => {r.target}{noteStr}");
                }
            }

            // Ưu tiên 2: Thuật ngữ cùng tác giả / thể loại
            foreach (var r in allRows)
            {
                bool matchAuthor = !string.IsNullOrEmpty(authorOfBook) && r.author == authorOfBook;
                bool matchGenre = !string.IsNullOrEmpty(genreOfBook) && r.genre == genreOfBook;
                if ((matchAuthor || matchGenre) && seen.Add(r.source))
                {
                    var noteStr = !string.IsNullOrEmpty(r.note) ? $" ({r.note})" : "";
                    sb.AppendLine($"• {r.source} => {r.target}{noteStr}");
                }
            }

            // Ưu tiên 3: Thuật ngữ dùng chung toàn hệ thống (book, author, genre đều rỗng)
            foreach (var r in allRows.Where(r => string.IsNullOrEmpty(r.book) && string.IsNullOrEmpty(r.author) && string.IsNullOrEmpty(r.genre)))
            {
                if (seen.Add(r.source))
                {
                    var noteStr = !string.IsNullOrEmpty(r.note) ? $" ({r.note})" : "";
                    sb.AppendLine($"• {r.source} => {r.target}{noteStr}");
                }
            }

            return seen.Count > 0 ? sb.ToString() : "";
        }
        catch
        {
            return "";
        }
    }

    public async Task<TranslationResult> TranslateAsync(
        string text, string providerName, string glossary = "", string context = "",
        string sourceLang = "English", string targetLang = "Vietnamese",
        bool trilingual = false, string contextPreviousText = "", Action<string>? onStatusLog = null, CancellationToken ct = default)
    {
        var config = ConfigService.GetProvider(providerName)
            ?? throw new Exception($"Provider '{providerName}' chưa được cấu hình");

        if (string.IsNullOrEmpty(config.ApiKey))
            throw new Exception("Chưa nhập API key");

        var prompt = BuildPrompt(text, glossary, context, sourceLang, targetLang, trilingual, contextPreviousText);

        TranslationResult? rawResult = null;
        Exception? lastEx = null;
        for (int attempt = 1; attempt <= 6; attempt++)
        {
            try
            {
                rawResult = providerName switch
                {
                    "gemini" => await TranslateGeminiAsync(config, prompt, ct, trilingual),
                    _ when providerName == "deepseek" || providerName.StartsWith("custom") => await TranslateOpenAICompatAsync(config, prompt, ct, trilingual),
                    _ => throw new Exception($"Provider '{providerName}' không hỗ trợ")
                };
                break;
            }
            catch (Exception ex) when (!ct.IsCancellationRequested)
            {
                lastEx = ex;
                var errMsg = ex.InnerException?.Message ?? ex.Message;
                bool isRateLimit = errMsg.Contains("429") || errMsg.Contains("RESOURCE_EXHAUSTED") || errMsg.Contains("Quota exceeded", StringComparison.OrdinalIgnoreCase);
                // 408/502/503/504/522/524/529/530: upstream bận / timeout phía server (524 = Cloudflare origin timeout) → retry
                bool isUpstreamUnavailable = errMsg.Contains("408") || errMsg.Contains("502") || errMsg.Contains("503") || errMsg.Contains("504")
                    || errMsg.Contains("522") || errMsg.Contains("524") || errMsg.Contains("529") || errMsg.Contains("530")
                    || errMsg.Contains("temporarily unavailable", StringComparison.OrdinalIgnoreCase)
                    || errMsg.Contains("upstream", StringComparison.OrdinalIgnoreCase);
                bool isTimeout = ex is TaskCanceledException || ex is TimeoutException || errMsg.Contains("canceled", StringComparison.OrdinalIgnoreCase) || errMsg.Contains("timeout", StringComparison.OrdinalIgnoreCase);

                if (isRateLimit && attempt < 6)
                {
                    onStatusLog?.Invoke($"⏳ [API Rate Limit/429] Server báo quá tải hạn mức ({errMsg}). Đang tự động chờ 20 giây (Lần thử {attempt}/6)...");
                    await Task.Delay(20000 + Random.Shared.Next(0, 3000), ct); // jitter tránh nhiều chunk cùng retry 1 lúc
                }
                else if ((isUpstreamUnavailable || isTimeout) && attempt < 6)
                {
                    // Thời gian chờ giãn nở theo cấp số (5s, 10s, 20s, 35s, 50s) giúp server upstream có thời gian thở và phục hồi
                    int[] waitSteps = { 5, 10, 20, 35, 50 };
                    int waitSec = waitSteps[Math.Min(attempt - 1, waitSteps.Length - 1)];
                    string reason = isTimeout ? "Timeout chờ phản hồi" : errMsg;
                    onStatusLog?.Invoke($"⏳ [Server bận: {reason}] Tạm nghỉ {waitSec}s rồi gửi tiếp (Lần thử {attempt}/6)...");
                    await Task.Delay((waitSec * 1000) + Random.Shared.Next(0, 1500), ct);
                }
                else if (attempt < 5)
                {
                    onStatusLog?.Invoke($"⏳ [Tạm dừng kết nối: {errMsg}] Thử lại lần {attempt + 1}/6...");
                    await Task.Delay(3000, ct);
                }
                else
                {
                    break;
                }
            }
        }

        if (rawResult == null)
        {
            var msg = lastEx?.InnerException?.Message ?? lastEx?.Message ?? "Lỗi kết nối API";
            throw new Exception($"[Kết nối API thất bại] {msg}");
        }

        if (trilingual)
        {
            var originalLines = text.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
            var alignedLines = new string[originalLines.Length];

            // Parse các dòng có dạng [1] text, * [1] text, [1] -> text...
            var lines = rawResult.Text.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
            foreach (var l in lines)
            {
                var trimmed = l.Trim().TrimStart('*', '-', ' ', '\t');
                var match = System.Text.RegularExpressions.Regex.Match(trimmed, @"^\[(\d+)\]\s*(?:[→\-\:=>]\s*)?(.*)$");
                if (match.Success)
                {
                    if (int.TryParse(match.Groups[1].Value, out var idx) && idx >= 1 && idx <= originalLines.Length)
                    {
                        var content = match.Groups[2].Value.Trim();
                        // Tránh lấy nhầm dòng gốc nếu AI trả về dạng [1] Gốc -> Dịch
                        if (content.Contains("→"))
                        {
                            var parts = content.Split('→');
                            content = parts.Last().Trim();
                        }
                        alignedLines[idx - 1] = content;
                    }
                }
            }

            // Fallback cho các dòng chưa match: giữ nguyên dòng nếu là heading/ảnh hoặc chỉ có 1 dòng
            for (int i = 0; i < originalLines.Length; i++)
            {
                if (string.IsNullOrWhiteSpace(alignedLines[i]))
                {
                    var origTrim = originalLines[i].Trim();
                    if (origTrim.StartsWith("#") || origTrim.StartsWith("![") || origTrim.StartsWith("---") || string.IsNullOrWhiteSpace(origTrim))
                    {
                        alignedLines[i] = originalLines[i];
                    }
                }
            }

            var cleanText = string.Join("\n", alignedLines);
            return rawResult with { Text = cleanText };
        }

        return rawResult;
    }

    public async Task<List<string>> FetchAvailableModelsAsync(string providerName, string apiKey, string baseUrl = "", CancellationToken ct = default)
    {
        var list = new List<string>();
        if (string.IsNullOrWhiteSpace(apiKey)) return list;
        apiKey = apiKey.Trim();

        try
        {
            if (providerName == "gemini")
            {
                var url = $"https://generativelanguage.googleapis.com/v1beta/models?key={apiKey}";
                using var req = new HttpRequestMessage(HttpMethod.Get, url);
                req.Headers.Add("x-goog-api-key", apiKey);
                var resp = await SendWithTimeoutAsync(req, TimeSpan.FromSeconds(45), ct);
                if (resp.IsSuccessStatusCode)
                {
                    var json = await resp.Content.ReadAsStringAsync(ct);
                    using var doc = JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("models", out var modelsArr))
                    {
                        foreach (var m in modelsArr.EnumerateArray())
                        {
                            var name = m.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                            name = name.Replace("models/", "").Trim();
                            
                            // Check if model supports text generation
                            var isGen = false;
                            if (m.TryGetProperty("supportedGenerationMethods", out var methods))
                            {
                                foreach (var method in methods.EnumerateArray())
                                {
                                    if (method.GetString() == "generateContent") { isGen = true; break; }
                                }
                            }
                            if (isGen && !string.IsNullOrEmpty(name))
                            {
                                list.Add(name);
                            }
                        }
                    }
                }
            }
            else // deepseek, openai, custom (OpenCode, CommandCode, OpenRouter, OneAPI...)
            {
                var inputBase = (baseUrl ?? "").Trim().TrimEnd('/');

                // Chuẩn bị các URL khả dĩ để quét thực tế từ server
                var candidateUrls = new List<string>();

                if (!string.IsNullOrEmpty(inputBase))
                {
                    if (inputBase.EndsWith("/models", StringComparison.OrdinalIgnoreCase))
                    {
                        candidateUrls.Add(inputBase);
                    }
                    else
                    {
                        candidateUrls.Add($"{inputBase}/models");
                        if (!inputBase.EndsWith("/v1", StringComparison.OrdinalIgnoreCase))
                        {
                            candidateUrls.Add($"{inputBase}/v1/models");
                            candidateUrls.Add($"{inputBase}/provider/v1/models");
                        }
                    }
                }
                else
                {
                    if (providerName == "deepseek")
                    {
                        candidateUrls.Add("https://api.deepseek.com/v1/models");
                    }
                    else // custom (tự động thử CommandCode, OpenRouter, OpenAI...)
                    {
                        candidateUrls.Add("https://api.commandcode.ai/provider/v1/models");
                        candidateUrls.Add("https://openrouter.ai/api/v1/models");
                        candidateUrls.Add("https://api.openai.com/v1/models");
                    }
                }

                foreach (var url in candidateUrls)
                {
                    try
                    {
                        using var req = new HttpRequestMessage(HttpMethod.Get, url);
                        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
                        req.Headers.Add("User-Agent", "OpenAI/Python 1.30.0 (Windows NT 10.0; Win64; x64)");

                        var resp = await SendWithTimeoutAsync(req, TimeSpan.FromSeconds(45), ct);
                        if (resp.IsSuccessStatusCode)
                        {
                            var json = await resp.Content.ReadAsStringAsync(ct);
                            using var doc = JsonDocument.Parse(json);

                            // Hàm phụ trích xuất model ID linh hoạt từ bất kỳ object nào
                            void ExtractModelId(JsonElement elem)
                            {
                                if (elem.ValueKind == JsonValueKind.String)
                                {
                                    var s = elem.GetString();
                                    if (!string.IsNullOrEmpty(s) && !list.Contains(s)) list.Add(s);
                                }
                                else if (elem.ValueKind == JsonValueKind.Object)
                                {
                                    string[] idProps = { "id", "name", "model", "model_name", "display_name", "slug" };
                                    foreach (var p in idProps)
                                    {
                                        if (elem.TryGetProperty(p, out var val) && val.ValueKind == JsonValueKind.String)
                                        {
                                            var s = val.GetString();
                                            if (!string.IsNullOrEmpty(s) && !list.Contains(s))
                                            {
                                                list.Add(s);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }

                            // 1. Chuẩn OpenAI: { "data": [ ... ] }
                            if (doc.RootElement.TryGetProperty("data", out var dataArr) && dataArr.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var m in dataArr.EnumerateArray()) ExtractModelId(m);
                            }
                            // 2. Chuẩn { "models": [ ... ] }
                            else if (doc.RootElement.TryGetProperty("models", out var mArr) && mArr.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var m in mArr.EnumerateArray()) ExtractModelId(m);
                            }
                            // 3. Mảng gốc: [ ... ]
                            else if (doc.RootElement.ValueKind == JsonValueKind.Array)
                            {
                                foreach (var m in doc.RootElement.EnumerateArray()) ExtractModelId(m);
                            }
                            // 4. Object chứa dict các model: { "deepseek-chat": { ... }, "gpt-4o": { ... } }
                            else if (doc.RootElement.ValueKind == JsonValueKind.Object)
                            {
                                foreach (var prop in doc.RootElement.EnumerateObject())
                                {
                                    if (prop.Value.ValueKind == JsonValueKind.Object || prop.Value.ValueKind == JsonValueKind.Array)
                                    {
                                        if (!prop.Name.Equals("error", StringComparison.OrdinalIgnoreCase) &&
                                            !prop.Name.Equals("status", StringComparison.OrdinalIgnoreCase) &&
                                            !prop.Name.Equals("success", StringComparison.OrdinalIgnoreCase))
                                        {
                                            if (prop.Value.ValueKind == JsonValueKind.Array)
                                            {
                                                foreach (var sub in prop.Value.EnumerateArray()) ExtractModelId(sub);
                                            }
                                            else
                                            {
                                                if (!list.Contains(prop.Name)) list.Add(prop.Name);
                                                ExtractModelId(prop.Value);
                                            }
                                        }
                                    }
                                }
                            }

                            if (list.Count > 0) break; // Đã quét được danh sách thực tế từ server
                        }
                    }
                    catch { }
                }
            }
        }
        catch { }

        return list;
    }

    public async Task<(bool ok, string message)> TestConnectionAsync(string providerName)
    {
        try
        {
            var config = ConfigService.GetProvider(providerName);
            if (config == null || string.IsNullOrEmpty(config.ApiKey))
                return (false, "Chưa cấu hình API key");

            var apiKey = config.ApiKey.Trim();
            var model = string.IsNullOrWhiteSpace(config.Model) ? "gemini-3.6-flash" : config.Model.Trim();

            if (providerName == "gemini")
            {
                // Kiểm tra metadata model qua HTTP GET — Tiêu tốn 0 TOKEN generate
                var url = $"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={apiKey}";
                using var req = new HttpRequestMessage(HttpMethod.Get, url);
                req.Headers.Add("x-goog-api-key", apiKey);

                var resp = await SendWithTimeoutAsync(req, TimeSpan.FromSeconds(45), CancellationToken.None);
                var result = await resp.Content.ReadAsStringAsync();
                if (!resp.IsSuccessStatusCode)
                {
                    try
                    {
                        var errDoc = JsonDocument.Parse(result);
                        if (errDoc.RootElement.TryGetProperty("error", out var errObj))
                        {
                            var errMsg = errObj.TryGetProperty("message", out var m) ? m.GetString() : errObj.ToString();
                            return (false, $"[HTTP {(int)resp.StatusCode}] {errMsg}");
                        }
                    }
                    catch { }
                    return (false, $"[HTTP {(int)resp.StatusCode}] {result}");
                }
                return (true, $"OK — Model: {model} (0 token)");
            }
            else // deepseek, openai, custom
            {
                // Kiểm tra xác thực API key qua HTTP GET /models — Tiêu tốn 0 TOKEN generate
                var rootUrl = string.IsNullOrWhiteSpace(config.BaseUrl)
                    ? (providerName == "deepseek" ? "https://api.deepseek.com/v1" : "https://api.openai.com/v1")
                    : config.BaseUrl.TrimEnd('/');
                var url = $"{rootUrl}/models";

                using var req = new HttpRequestMessage(HttpMethod.Get, url);
                req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
                req.Headers.Add("User-Agent", "OpenAI/Python 1.30.0 (Windows NT 10.0; Win64; x64)");

                var resp = await SendWithTimeoutAsync(req, TimeSpan.FromSeconds(45), CancellationToken.None);
                var result = await resp.Content.ReadAsStringAsync();
                if (!resp.IsSuccessStatusCode)
                {
                    try
                    {
                        var errDoc = JsonDocument.Parse(result);
                        if (errDoc.RootElement.TryGetProperty("error", out var errObj))
                        {
                            var errMsg = errObj.TryGetProperty("message", out var m) ? m.GetString() : errObj.ToString();
                            return (false, $"[HTTP {(int)resp.StatusCode}] {errMsg}");
                        }
                    }
                    catch { }
                    return (false, $"[HTTP {(int)resp.StatusCode}] {result}");
                }
                return (true, $"OK — Model: {model} (0 token)");
            }
        }
        catch (Exception ex)
        {
            return (false, $"Lỗi: {ex.Message}");
        }
    }

    private async Task<TranslationResult> TranslateGeminiAsync(
        ProviderConfig config, string prompt, CancellationToken ct, bool trilingualMode = false)
    {
        var apiKey = (config.ApiKey ?? "").Trim();
        var model = string.IsNullOrWhiteSpace(config.Model) ? "gemini-3.6-flash" : config.Model.Trim();
        var url = $"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent";

        // Mái an toàn chống output chạy vô hạn — ngưỡng luôn rộng hơn bản dịch thực tế (chunk 1500-3000 ký tự) nên KHÔNG cắt ngắn chất lượng
        int maxTokens = Math.Min(20000, Math.Max(4000, prompt.Length * 2));
        var body = new
        {
            contents = new[] { new { parts = new[] { new { text = prompt } } } },
            generationConfig = new { maxOutputTokens = maxTokens }
        };
        var json = JsonSerializer.Serialize(body);
        
        using var request = new HttpRequestMessage(HttpMethod.Post, $"{url}?key={apiKey}");
        request.Headers.Add("x-goog-api-key", apiKey);
        request.Headers.Add("User-Agent", "TranslateBook/1.0");
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await SendWithTimeoutAsync(request, TimeSpan.FromSeconds(180), ct);
        var result = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            try
            {
                var errDoc = JsonDocument.Parse(result);
                if (errDoc.RootElement.TryGetProperty("error", out var errObj))
                {
                    var errMsg = errObj.TryGetProperty("message", out var m) ? m.GetString() : errObj.ToString();
                    throw new Exception($"[HTTP {(int)resp.StatusCode}] {errMsg}");
                }
            }
            catch (Exception ex) when (!ex.Message.StartsWith("[HTTP")) { }
            throw new Exception($"[HTTP {(int)resp.StatusCode}] {result}");
        }
        var doc = JsonDocument.Parse(result);

        var text = doc.RootElement
            .GetProperty("candidates")[0]
            .GetProperty("content")
            .GetProperty("parts")[0]
            .GetProperty("text")
            .GetString() ?? "";

        return new TranslationResult(text, model, "gemini");
    }

    private async Task<TranslationResult> TranslateOpenAICompatAsync(
        ProviderConfig config, string prompt, CancellationToken ct, bool trilingualMode = false)
    {
        var inputBase = (config.BaseUrl ?? "").Trim().TrimEnd('/');
        string url;
        if (!string.IsNullOrEmpty(inputBase))
        {
            if (inputBase.EndsWith("/chat/completions", StringComparison.OrdinalIgnoreCase))
                url = inputBase;
            else if (inputBase.EndsWith("/v1", StringComparison.OrdinalIgnoreCase) || inputBase.EndsWith("/provider/v1", StringComparison.OrdinalIgnoreCase))
                url = $"{inputBase}/chat/completions";
            else
                url = $"{inputBase}/v1/chat/completions";
        }
        else
        {
            var key = (config.ApiKey ?? "").Trim();
            if (key.StartsWith("user_") || key.StartsWith("cmd_"))
                url = "https://api.commandcode.ai/provider/v1/chat/completions";
            else
                url = "https://api.deepseek.com/v1/chat/completions";
        }

        var systemPrompt = trilingualMode
            ? "Bạn là một dịch giả chuyên nghiệp. Dịch từng dòng, giữ nguyên số dòng."
            : "Bạn là một dịch giả chuyên nghiệp.";

        // Mái an toàn chống output chạy vô hạn — ngưỡng luôn rộng hơn bản dịch thực tế (chunk 1500-3000 ký tự → vài nghìn token) nên KHÔNG cắt chất lượng
        int maxTokens = Math.Min(20000, Math.Max(4000, prompt.Length * 2));
        var reqDict = new Dictionary<string, object?>
        {
            ["model"] = string.IsNullOrWhiteSpace(config.Model) ? "deepseek-chat" : config.Model,
            ["messages"] = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = prompt }
            },
            ["temperature"] = 0.3,
            ["max_tokens"] = maxTokens,
            // Tắt suy nghĩ ngầm (Thinking/Reasoning) trên các model để dịch trả về ngay trong 3-5s, chống sập timeout HTTP 524
            ["thinking"] = new { type = "disabled" }
        };
        var json = JsonSerializer.Serialize(reqDict);

        using var request = new HttpRequestMessage(HttpMethod.Post, url);
        request.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", config.ApiKey?.Trim());
        request.Headers.Add("User-Agent", "OpenAI/Python 1.30.0 (Windows NT 10.0; Win64; x64)");
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await SendWithTimeoutAsync(request, TimeSpan.FromSeconds(180), ct);
        var result = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            try
            {
                var errDoc = JsonDocument.Parse(result);
                if (errDoc.RootElement.TryGetProperty("error", out var errObj))
                {
                    var errMsg = errObj.TryGetProperty("message", out var m) ? m.GetString() : errObj.ToString();
                    throw new Exception($"[HTTP {(int)resp.StatusCode}] {errMsg}");
                }
            }
            catch (Exception ex) when (!ex.Message.StartsWith("[HTTP")) { }
            throw new Exception($"[HTTP {(int)resp.StatusCode}] {result}");
        }
        var doc = JsonDocument.Parse(result);
        var root = doc.RootElement;

        string text = "";
        if (root.TryGetProperty("choices", out var choices) && choices.ValueKind == JsonValueKind.Array && choices.GetArrayLength() > 0)
        {
            var firstChoice = choices[0];
            if (firstChoice.TryGetProperty("message", out var msg))
            {
                if (msg.TryGetProperty("content", out var contentElem) && contentElem.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(contentElem.GetString()))
                {
                    text = contentElem.GetString() ?? "";
                }
                else if (msg.TryGetProperty("reasoning_content", out var reasonElem) && reasonElem.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(reasonElem.GetString()))
                {
                    text = reasonElem.GetString() ?? "";
                }
                else if (msg.TryGetProperty("reasoning", out var rElem) && rElem.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(rElem.GetString()))
                {
                    text = rElem.GetString() ?? "";
                }
            }
            else if (firstChoice.TryGetProperty("delta", out var delta) && delta.TryGetProperty("content", out var deltaElem))
            {
                text = deltaElem.GetString() ?? "";
            }
            else if (firstChoice.TryGetProperty("text", out var textElem))
            {
                text = textElem.GetString() ?? "";
            }
        }
        else if (root.TryGetProperty("candidates", out var cands) && cands.ValueKind == JsonValueKind.Array && cands.GetArrayLength() > 0)
        {
            var firstCand = cands[0];
            if (firstCand.TryGetProperty("content", out var cObj) && cObj.TryGetProperty("parts", out var parts) && parts.ValueKind == JsonValueKind.Array && parts.GetArrayLength() > 0)
            {
                text = parts[0].TryGetProperty("text", out var ptElem) ? ptElem.GetString() ?? "" : "";
            }
        }
        else if (root.TryGetProperty("response", out var respElem))
        {
            text = respElem.GetString() ?? "";
        }
        else if (root.TryGetProperty("output", out var outElem))
        {
            text = outElem.GetString() ?? "";
        }

        if (string.IsNullOrWhiteSpace(text))
        {
            throw new Exception($"[Phản hồi không chuẩn] Server không trả về nội dung text hợp lệ: {result}");
        }

        var tokensIn = root.TryGetProperty("usage", out var usage) &&
            usage.TryGetProperty("prompt_tokens", out var pt) ? pt.GetInt32() : 0;
        var tokensOut = usage.TryGetProperty("completion_tokens", out var ct2) ? ct2.GetInt32() : 0;

        return new TranslationResult(text, config.Model, config.BaseUrl ?? "openai",
            tokensIn, tokensOut);
    }

    private static string BuildPrompt(string text, string glossary, string context,
        string sourceLang, string targetLang, bool trilingualMode, string contextPreviousText = "")
    {
        var sb = new StringBuilder();
        sb.AppendLine("Bạn là một dịch giả văn học chuyên nghiệp hàng đầu.");
        sb.AppendLine($"NHIỆM VỤ TỐI CAO: Dịch toàn bộ văn bản sau từ {sourceLang} sang {targetLang} (TIẾNG VIỆT).");
        sb.AppendLine("⚠️ YÊU CẦU SỐ 1: BẢN DỊCH PHẢI LÀ 100% TIẾNG VIỆT. TUYỆT ĐỐI KHÔNG ĐƯỢC GIỮ LẠI CHỮ HÁN / TIẾNG TRUNG!");
        sb.AppendLine();

        if (!string.IsNullOrEmpty(glossary))
            sb.AppendLine("## THUẬT NGỮ CỐ ĐỊNH (BẮT BUỘC DÙNG ĐÚNG):").AppendLine(glossary).AppendLine();
        if (!string.IsNullOrEmpty(context))
            sb.AppendLine("## HỒ SƠ VĂN CHƯƠNG (QUY TẮC XƯNG HÔ & PHONG CÁCH TÁC GIẢ):").AppendLine(context).AppendLine();
        if (!string.IsNullOrEmpty(contextPreviousText))
        {
            sb.AppendLine("## NGỮ CẢNH ĐOẠN TRƯỚC (BÁM SÁT MẠCH TRUYỆN & CẢM XÚC NHÂN VẬT):");
            sb.AppendLine(contextPreviousText);
            sb.AppendLine("*(Hãy dịch đoạn tiếp theo sao cho nối tiếp tự nhiên, mượt mà với ngữ cảnh trên)*");
            sb.AppendLine();
        }

        sb.AppendLine("## TIÊU CHUẨN VĂN HỌC (CHUẨN LÁNG):");
        sb.AppendLine("1. Dịch thoát ý cả câu/đoạn, câu từ tự nhiên, mượt mà như tác phẩm văn học Việt Nam.");
        sb.AppendLine("2. Giữ nguyên ý gốc và nét văn hóa (ví dụ: 旗袍 => sườn xám; 汉服 => Hán phục; 坐月子 => ở cữ).");
        sb.AppendLine("3. Thoại tự nhiên ngoài đời thực; xưng hô nhất quán; từ ngữ thuần Việt, giàu hình tượng, tránh lặp từ.");
        sb.AppendLine();

        if (trilingualMode)
        {
            var lines = text.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
            sb.AppendLine($"## QUY TẮC ĐỐI ỨNG DÒNG (BẮT BUỘC KHỚP {lines.Length} DÒNG 1:1):");
            sb.AppendLine($"Văn bản gốc gồm đúng {lines.Length} dòng được đánh số [1] đến [{lines.Length}].");
            sb.AppendLine("Bạn PHẢI trả về đúng từng dòng có tiền tố số thứ tự: [1] <bản dịch dòng 1>, [2] <bản dịch dòng 2>...");
            sb.AppendLine("Giữ nguyên ký hiệu heading (# hoặc ##) và link ảnh ![...] ở vị trí dòng tương ứng.");
            sb.AppendLine("CHỈ TRẢ VỀ DUY NHẤT CÁC DÒNG ĐÃ DỊCH ĐÁNH SỐ THEO THỨ TỰ. Không giải thích!");
            sb.AppendLine();
            sb.AppendLine("VĂN BẢN GỐC CẦN DỊCH:");
            for (int i = 0; i < lines.Length; i++)
            {
                sb.AppendLine($"[{i + 1}] {lines[i]}");
            }
        }
        else
        {
            sb.AppendLine("## QUY TẮC DỊCH:");
            sb.AppendLine("1. Dịch toàn bộ sang tiếng Việt trôi chảy theo chuẩn nhà văn, giữ nguyên định dạng Markdown (heading #, bảng, ảnh).");
            sb.AppendLine("2. CHỈ TRẢ VỀ DUY NHẤT BẢN DỊCH TIẾNG VIỆT. Không giải thích.");
            sb.AppendLine();
            sb.AppendLine("VĂN BẢN GỐC CẦN DỊCH SANG TIẾNG VIỆT:");
            sb.Append(text);
        }
        return sb.ToString();
    }
}
