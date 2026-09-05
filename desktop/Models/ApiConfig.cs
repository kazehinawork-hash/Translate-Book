using System.Collections.Generic;

namespace TranslateBook.Models;

public class ApiConfig
{
    public string ActiveProvider { get; set; } = "custom_1";
    public Dictionary<string, ProviderConfig> Providers { get; set; } = new()
    {
        ["gemini"] = new() { Model = "gemini-3.6-flash" },
        ["deepseek"] = new() { Model = "deepseek-chat", BaseUrl = "https://api.deepseek.com/v1" },
        ["custom_1"] = new() { Model = "minimax/minimax-m3-free", BaseUrl = "https://api.commandcode.ai/provider/v1" },
        ["custom_2"] = new() { Model = "deepseek/deepseek-chat", BaseUrl = "https://api.commandcode.ai/provider/v1" },
        ["custom_3"] = new() { Model = "qwen/qwen-2.5-72b-instruct", BaseUrl = "https://api.commandcode.ai/provider/v1" },
        ["custom_4"] = new() { Model = "claude-3-5-sonnet", BaseUrl = "https://api.commandcode.ai/provider/v1" },
        ["custom_5"] = new() { Model = "gpt-4o-mini", BaseUrl = "https://api.commandcode.ai/provider/v1" },
    };
}

public class ProviderConfig
{
    public string ApiKey { get; set; } = "";
    public string Model { get; set; } = "";
    public string BaseUrl { get; set; } = "";
    public string Name { get; set; } = ""; // Tên gợi nhớ do người dùng đặt (ví dụ: Key chính, Key dự phòng...)
}
