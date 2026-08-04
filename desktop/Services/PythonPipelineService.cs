using System.Diagnostics;
using System.IO;

namespace TranslateBook.Services;

public class PythonPipelineService
{
    private readonly string _projectRoot;
    private readonly string _pythonExe;

    public event Action<string>? OutputReceived;
    public event Action<string>? ErrorReceived;

    public PythonPipelineService(string projectRoot)
    {
        _projectRoot = projectRoot;
        // Tim Python trong .venv
        var venvPython = Path.Combine(projectRoot, ".venv", "Scripts", "python.exe");
        _pythonExe = File.Exists(venvPython) ? venvPython : "python";
    }

    public async Task<bool> RunScriptAsync(string scriptPath, string args = "",
        CancellationToken ct = default)
    {
        var fullPath = Path.Combine(_projectRoot, "scripts", scriptPath);
        if (!File.Exists(fullPath))
        {
            ErrorReceived?.Invoke($"Khong tim thay script: {fullPath}");
            return false;
        }

        var psi = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = $"\"{fullPath}\" {args}",
            WorkingDirectory = _projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
        };

        using var process = new Process { StartInfo = psi };

        process.OutputDataReceived += (s, e) =>
        {
            if (e.Data != null) OutputReceived?.Invoke(e.Data);
        };
        process.ErrorDataReceived += (s, e) =>
        {
            if (e.Data != null) ErrorReceived?.Invoke(e.Data);
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        await process.WaitForExitAsync(ct);
        return process.ExitCode == 0;
    }

    public async Task<bool> RunAudiobookAsync(string slug, string temperature = "0.3",
        string topK = "10", CancellationToken ct = default)
    {
        var args = $"--slug {slug} --temperature {temperature} --top-k {topK} --force";
        return await RunScriptAsync("audiobook/audiobook_long.py", args, ct);
    }

    public async Task<bool> RunTranslateHelperAsync(string chunksDir, string progressDir,
        string glossary, CancellationToken ct = default)
    {
        var args = $"--interactive --chunks-dir \"{chunksDir}\" --progress-dir \"{progressDir}\" --glossary \"{glossary}\"";
        return await RunScriptAsync("translate/translate_helper.py", args, ct);
    }

    public async Task<bool> RunGitCommandAsync(string command, CancellationToken ct = default)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "git",
            Arguments = command,
            WorkingDirectory = _projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = Process.Start(psi)!;
        var output = await process.StandardOutput.ReadToEndAsync(ct);
        OutputReceived?.Invoke(output);
        await process.WaitForExitAsync(ct);
        return process.ExitCode == 0;
    }
}
