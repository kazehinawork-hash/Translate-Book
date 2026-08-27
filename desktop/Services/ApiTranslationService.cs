using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using TranslateBook.Models;

namespace TranslateBook.Services;

public class ApiTranslationService
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(100) };

    public record TranslationResult(string Text, string Model, string Provider,
        int TokensIn = 0, int TokensOut = 0);

    public static string LoadGlossary(string slug, string projectRoot)
    {
        var masterPath = Path.Combine(projectRoot, "glossary", "master.csv");
        if (!File.Exists(masterPath))
            return "";
        try
        {
            var lines = File.ReadAllLines(masterPath, Encoding.UTF8);
            var sb = new StringBuilder();
            bool isFirst = true;
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                if (isFirst) { sb.AppendLine(line); isFirst = false; continue; }

                // Nếu là dòng glossary chung hoặc thuộc đúng sách này
                var parts = line.Split(',');
                if (parts.Length >= 5)
                {
                    var bookCol = parts[4].Trim();
                    if (string.IsNullOrEmpty(bookCol) || bookCol.Equals(slug, StringComparison.OrdinalIgnoreCase))
                    {
                        sb.AppendLine(line);
                    }
                }
                else
                {
                    sb.AppendLine(line);
                }
            }
            return sb.ToString();
        }
        catch
        {
            return "";
        }
    }

    public async Task<TranslationResult> TranslateAsync(
        string text, string providerName, string glossary = "", string context = "",
        string sourceLang = "English", string targetLang = "Vietnamese",
        bool trilingual = false, Action<string>? onStatusLog = null, CancellationToken ct = default)
    {
        var config = ConfigService.GetProvider(providerName)
            ?? throw new Exception($"Provider '{providerName}' chưa được cấu hình");

        if (string.IsNullOrEmpty(config.ApiKey))
            throw new Exception("Chưa nhập API key");

        var prompt = BuildPrompt(text, glossary, context, sourceLang, targetLang, trilingual);

        TranslationResult? rawResult = null;
        Exception? lastEx = null;
        for (int attempt = 1; attempt <= 5; attempt++)
        {
            try
            {
                rawResult = providerName switch
                {
                    "gemini" => await TranslateGeminiAsync(config, prompt, ct, trilingual),
                    "deepseek" or "custom" => await TranslateOpenAICompatAsync(config, prompt, ct, trilingual),
                    _ => throw new Exception($"Provider '{providerName}' không hỗ trợ")
                };
                break;
            }
            catch (Exception ex) when (!ct.IsCancellationRequested)
            {
                lastEx = ex;
                var errMsg = ex.InnerException?.Message ?? ex.Message;
                bool isRateLimit = errMsg.Contains("429") || errMsg.Contains("RESOURCE_EXHAUSTED") || errMsg.Contains("Quota exceeded", StringComparison.OrdinalIgnoreCase);

                if (isRateLimit && attempt < 5)
                {
                    onStatusLog?.Invoke($"⏳ [Chạm giới hạn API] Đang tự động chờ 35 giây để phục hồi hạn mức (Lần thử {attempt}/5)...");
                    await Task.Delay(35000, ct);
                }
                else if (attempt < 3)
                {
                    await Task.Delay(2500, ct);
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

            // Parse các dòng có dạng [1] text, [2] text...
            var lines = rawResult.Text.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None);
            foreach (var l in lines)
            {
                var match = System.Text.RegularExpressions.Regex.Match(l, @"^\[(\d+)\]\s*(.*)$");
                if (match.Success)
                {
                    if (int.TryParse(match.Groups[1].Value, out var idx) && idx >= 1 && idx <= originalLines.Length)
                    {
                        alignedLines[idx - 1] = match.Groups[2].Value.Trim();
                    }
                }
            }

            // Fallback cho các dòng chưa match
            for (int i = 0; i < originalLines.Length; i++)
            {
                if (string.IsNullOrWhiteSpace(alignedLines[i]))
                {
                    if (i < lines.Length && !lines[i].StartsWith("["))
                        alignedLines[i] = lines[i].Trim();
                    else
                        alignedLines[i] = originalLines[i]; // Giữ nguyên heading/link ảnh nếu AI bỏ sót
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
                var resp = await _http.SendAsync(req, ct);
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
            else // deepseek, openai, custom
            {
                var rootUrl = string.IsNullOrWhiteSpace(baseUrl)
                    ? (providerName == "deepseek" ? "https://api.deepseek.com/v1" : "https://api.openai.com/v1")
                    : baseUrl.TrimEnd('/');
                var url = $"{rootUrl}/models";

                using var req = new HttpRequestMessage(HttpMethod.Get, url);
                req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
                var resp = await _http.SendAsync(req, ct);
                if (resp.IsSuccessStatusCode)
                {
                    var json = await resp.Content.ReadAsStringAsync(ct);
                    using var doc = JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("data", out var dataArr))
                    {
                        foreach (var m in dataArr.EnumerateArray())
                        {
                            var id = m.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? "" : "";
                            if (!string.IsNullOrEmpty(id)) list.Add(id);
                        }
                    }
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

                var resp = await _http.SendAsync(req);
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

                var resp = await _http.SendAsync(req);
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

        var body = new
        {
            contents = new[] { new { parts = new[] { new { text = prompt } } } }
        };
        var json = JsonSerializer.Serialize(body);
        
        using var request = new HttpRequestMessage(HttpMethod.Post, $"{url}?key={apiKey}");
        request.Headers.Add("x-goog-api-key", apiKey);
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await _http.SendAsync(request, ct);
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
        var baseUrl = string.IsNullOrEmpty(config.BaseUrl)
            ? "https://api.deepseek.com/v1"
            : config.BaseUrl.TrimEnd('/');

        var url = $"{baseUrl}/chat/completions";

        var systemPrompt = trilingualMode
            ? "Bạn là một dịch giả chuyên nghiệp. Dịch từng dòng, giữ nguyên số dòng."
            : "Bạn là một dịch giả chuyên nghiệp.";

        var body = new
        {
            model = string.IsNullOrWhiteSpace(config.Model) ? "deepseek-chat" : config.Model,
            messages = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = prompt }
            },
            temperature = 0.7
        };
        var json = JsonSerializer.Serialize(body);

        using var request = new HttpRequestMessage(HttpMethod.Post, url);
        request.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", config.ApiKey?.Trim());
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await _http.SendAsync(request, ct);
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
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString() ?? "";

        var tokensIn = doc.RootElement.TryGetProperty("usage", out var usage) &&
            usage.TryGetProperty("prompt_tokens", out var pt) ? pt.GetInt32() : 0;
        var tokensOut = usage.TryGetProperty("completion_tokens", out var ct2) ? ct2.GetInt32() : 0;

        return new TranslationResult(text, config.Model, config.BaseUrl ?? "openai",
            tokensIn, tokensOut);
    }

    private static string BuildPrompt(string text, string glossary, string context,
        string sourceLang, string targetLang, bool trilingualMode)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Bạn là một dịch giả văn học chuyên nghiệp hàng đầu.");
        sb.AppendLine($"NHIỆM VỤ TỐI CAO: Dịch toàn bộ văn bản sau từ {sourceLang} sang {targetLang} (TIẾNG VIỆT).");
        sb.AppendLine("⚠️ YÊU CẦU SỐ 1: BẢN DỊCH PHẢI LÀ 100% TIẾNG VIỆT. TUYỆT ĐỐI KHÔNG ĐƯỢC GIỮ LẠI CHỮ HÁN / TIẾNG TRUNG!");
        sb.AppendLine();

        if (!string.IsNullOrEmpty(glossary))
            sb.AppendLine("## THUẬT NGỮ CỐ ĐỊNH (BẮT BUỘC DÙNG ĐÚNG):").AppendLine(glossary).AppendLine();
        if (!string.IsNullOrEmpty(context))
            sb.AppendLine("## NGỮ CẢNH TRƯỚC:").AppendLine(context).AppendLine();

        sb.AppendLine("## TIÊU CHUẨN VĂN CHƯƠNG LÁNG (LITERARY QUALITY — GIỮ HỒN NGUYÊN TÁC):");
        sb.AppendLine("1. Dịch CẢ CÂU, CẢ ĐOẠN — không dịch thô từng từ; câu từ phải tự nhiên, mượt mà như văn phong của một nhà văn Việt Nam thực thụ.");
        sb.AppendLine("2. GIỮ TRỌN HỒN NGUYÊN TÁC: Tuyệt đối không thêm/bớt ý, không đổi logic, giữ nguyên giọng điệu (trữ tình, châm biếm, sâu lắng, triết lý) và thái độ tác giả.");
        sb.AppendLine("3. Nhịp điệu & âm thanh: Ưu tiên câu có nhịp điệu uyển chuyển, tránh lặp từ vô cớ; tỉnh lược đại từ thừa để văn phong thanh thoát.");
        sb.AppendLine("4. Khẩu ngữ & hội thoại: Lời thoại sống động như người Việt giao tiếp ngoài đời thực, xưng hô nhất quán theo ngữ cảnh.");
        sb.AppendLine("5. Thuần Việt: Ưu tiên từ ngữ thuần Việt giàu hình tượng; tránh lạm dụng từ Hán-Việt tối nghĩa hay cụm từ dịch máy (như 'một cách', 'những điều', 'được bởi').");
        sb.AppendLine();
        sb.AppendLine("### VÍ DỤ ĐỐI CHIẾU CHUẨN (Bản Cứng vs Bản Láng Nhà Văn):");
        sb.AppendLine("• Câu gốc: “她心里很难过，但是她强忍着没有让泪水流下来。”");
        sb.AppendLine("  - 🛡️ Dịch máy thô cứng: 'Trong lòng cô ấy rất khó chịu, nhưng cô ấy cố nén lại không để nước mắt chảy xuống.'");
        sb.AppendLine("  - ✅ Chuẩn nhà văn (Láng): 'Lòng cô quặn thắt, nhưng cô nén hết vào trong, không để một giọt nước mắt rơi xuống.'");
        sb.AppendLine("• Câu gốc: “他不停地工作，一直工作到很晚。”");
        sb.AppendLine("  - 🛡️ Dịch máy thô cứng: 'Anh ấy không ngừng làm việc, một mực làm việc đến rất muộn.'");
        sb.AppendLine("  - ✅ Chuẩn nhà văn (Láng): 'Anh miệt mài làm đến tận khuya.'");
        sb.AppendLine("=> BẢN DỊCH CỦA BẠN BẮT BUỘC PHẢI ĐẠT CHUẨN LÁNG (NHÀ VĂN) NHƯ CÁC VÍ DỤ TRÊN.");
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
