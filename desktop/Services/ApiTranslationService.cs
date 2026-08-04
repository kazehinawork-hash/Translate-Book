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

    public async Task<TranslationResult> TranslateAsync(
        string text, string providerName, string glossary = "", string context = "",
        CancellationToken ct = default)
    {
        var config = ConfigService.GetProvider(providerName)
            ?? throw new Exception($"Provider '{providerName}' not configured");

        if (string.IsNullOrEmpty(config.ApiKey))
            throw new Exception("Chua nhap API key");

        var prompt = BuildPrompt(text, glossary, context);

        return providerName switch
        {
            "gemini" => await TranslateGeminiAsync(config, prompt, ct),
            "deepseek" or "custom" => await TranslateOpenAICompatAsync(config, prompt, ct),
            _ => throw new Exception($"Provider '{providerName}' khong ho tro")
        };
    }

    public async Task<(bool ok, string message)> TestConnectionAsync(string providerName)
    {
        try
        {
            var config = ConfigService.GetProvider(providerName);
            if (config == null || string.IsNullOrEmpty(config.ApiKey))
                return (false, "Chua cau hinh API key");

            var result = await TranslateAsync("Say OK", providerName);
            return (true, $"OK — Model: {config.Model}");
        }
        catch (Exception ex)
        {
            return (false, $"Loi: {ex.Message}");
        }
    }

    private async Task<TranslationResult> TranslateGeminiAsync(
        ProviderConfig config, string prompt, CancellationToken ct)
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
        ProviderConfig config, string prompt, CancellationToken ct)
    {
        var baseUrl = string.IsNullOrEmpty(config.BaseUrl)
            ? "https://api.openai.com/v1"
            : config.BaseUrl.TrimEnd('/');

        var url = $"{baseUrl}/chat/completions";
        _http.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", config.ApiKey);

        var body = new
        {
            model = config.Model,
            messages = new[]
            {
                new { role = "system", content = "You are a professional translator." },
                new { role = "user", content = prompt }
            },
            temperature = 0.7
        };
        var json = JsonSerializer.Serialize(body);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var resp = await _http.PostAsync(url, content, ct);
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

    private static string BuildPrompt(string text, string glossary, string context)
    {
        var sb = new StringBuilder();
        if (!string.IsNullOrEmpty(glossary))
            sb.AppendLine("GLOSSARY:").AppendLine(glossary).AppendLine();
        if (!string.IsNullOrEmpty(context))
            sb.AppendLine("CONTEXT:").AppendLine(context).AppendLine();
        sb.AppendLine("TEXT TO TRANSLATE:").Append(text);
        return sb.ToString();
    }
}
