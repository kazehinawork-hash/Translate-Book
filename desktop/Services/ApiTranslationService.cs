using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using TranslateBook.Models;

namespace TranslateBook.Services;

public class ApiTranslationService
{
    private readonly HttpClient _http = new();

    public record TranslationResult(string Text, string Model, string Provider,
        int TokensIn = 0, int TokensOut = 0);

    public static string LoadGlossary(string slug, string projectRoot)
    {
        var csvPath = Path.Combine(projectRoot, "glossary", $"{slug}.csv");
        if (!File.Exists(csvPath))
            return "";
        try
        {
            var lines = File.ReadAllLines(csvPath, Encoding.UTF8);
            var sb = new StringBuilder();
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                sb.AppendLine(line);
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
        bool trilingual = false, CancellationToken ct = default)
    {
        var config = ConfigService.GetProvider(providerName)
            ?? throw new Exception($"Provider '{providerName}' chưa được cấu hình");

        if (string.IsNullOrEmpty(config.ApiKey))
            throw new Exception("Chưa nhập API key");

        var prompt = BuildPrompt(text, glossary, context, sourceLang, targetLang, trilingual);

        return providerName switch
        {
            "gemini" => await TranslateGeminiAsync(config, prompt, ct, trilingual),
            "deepseek" or "custom" => await TranslateOpenAICompatAsync(config, prompt, ct, trilingual),
            _ => throw new Exception($"Provider '{providerName}' không hỗ trợ")
        };
    }

    public async Task<(bool ok, string message)> TestConnectionAsync(string providerName)
    {
        try
        {
            var config = ConfigService.GetProvider(providerName);
            if (config == null || string.IsNullOrEmpty(config.ApiKey))
                return (false, "Chưa cấu hình API key");

            var result = await TranslateAsync("Nói OK", providerName);
            return (true, $"OK — Model: {config.Model}");
        }
        catch (Exception ex)
        {
            return (false, $"Lỗi: {ex.Message}");
        }
    }

    private async Task<TranslationResult> TranslateGeminiAsync(
        ProviderConfig config, string prompt, CancellationToken ct, bool trilingualMode = false)
    {
        var url = $"https://generativelanguage.googleapis.com/v1beta/models/{config.Model}:generateContent?key={config.ApiKey}";
        var body = new
        {
            contents = new[] { new { parts = new[] { new { text = prompt } } } }
        };
        var json = JsonSerializer.Serialize(body);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await _http.PostAsync(url, content, ct);
        resp.EnsureSuccessStatusCode();
        var result = await resp.Content.ReadAsStringAsync(ct);
        var doc = JsonDocument.Parse(result);

        var text = doc.RootElement
            .GetProperty("candidates")[0]
            .GetProperty("content")
            .GetProperty("parts")[0]
            .GetProperty("text")
            .GetString() ?? "";

        return new TranslationResult(text, config.Model, "gemini");
    }

    private async Task<TranslationResult> TranslateOpenAICompatAsync(
        ProviderConfig config, string prompt, CancellationToken ct, bool trilingualMode = false)
    {
        var baseUrl = string.IsNullOrEmpty(config.BaseUrl)
            ? "https://api.openai.com/v1"
            : config.BaseUrl.TrimEnd('/');

        var url = $"{baseUrl}/chat/completions";

        var systemPrompt = trilingualMode
            ? "Bạn là một dịch giả chuyên nghiệp. Dịch từng dòng, giữ nguyên số dòng."
            : "Bạn là một dịch giả chuyên nghiệp.";

        var body = new
        {
            model = config.Model,
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
            new AuthenticationHeaderValue("Bearer", config.ApiKey);
        request.Content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await _http.SendAsync(request, ct);
        resp.EnsureSuccessStatusCode();
        var result = await resp.Content.ReadAsStringAsync(ct);
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
        if (!string.IsNullOrEmpty(glossary))
            sb.AppendLine("GLOSSARY:").AppendLine(glossary).AppendLine();
        if (!string.IsNullOrEmpty(context))
            sb.AppendLine("CONTEXT:").AppendLine(context).AppendLine();

        if (trilingualMode)
        {
            sb.AppendLine($"Dịch từng dòng sau đây từ {sourceLang} sang {targetLang}.");
            sb.AppendLine($"QUAN TRỌNG: Số dòng trong kết quả phải Bằng đúng số dòng đầu vào.");
            sb.AppendLine($"Mỗi dòng đầu vào → đúng một dòng đầu ra. KHÔNG gộp, KHÔNG tách.");
            sb.AppendLine($"Giữ nguyên heading (#/##), giữ nguyên dòng ảnh ![...]");
            sb.AppendLine($"Bỏ các dòng /// OCR dư thừa.");
            sb.AppendLine($"Dùng glossary trên, không được chênh lệch.");
            sb.AppendLine($"Output ONLY bản dịch tiếng Việt, không giải thích.");
            sb.AppendLine();
            sb.AppendLine("TEXT TO TRANSLATE:");
            sb.Append(text);
        }
        else
        {
            sb.AppendLine($"Dịch đoạn văn sau từ {sourceLang} sang {targetLang}.");
            sb.AppendLine("Giữ nguyên heading (#/##), bảng, link, ảnh, định dạng markdown.");
            sb.AppendLine("Output ONLY bản dịch, không giải thích.");
            sb.AppendLine();
            sb.AppendLine("TEXT TO TRANSLATE:");
            sb.Append(text);
        }
        return sb.ToString();
    }
}
