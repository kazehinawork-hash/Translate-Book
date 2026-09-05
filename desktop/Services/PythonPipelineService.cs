using System.Diagnostics;
using System.IO;

namespace TranslateBook.Services;

public class PythonPipelineService
{
    private readonly string _projectRoot;
    private readonly string _pythonExe;

    public event Action<string>? OutputReceived;
    public event Action<string>? ErrorReceived;
    public Process? CurrentProcess { get; private set; }

    public PythonPipelineService(string projectRoot)
    {
        _projectRoot = projectRoot;
        var venvPython = Path.Combine(projectRoot, ".venv", "Scripts", "python.exe");
        _pythonExe = File.Exists(venvPython) ? venvPython : "python";
    }

    public async Task<bool> RunScriptAsync(string scriptPath, string args = "",
        CancellationToken ct = default, string? pythonExe = null)
    {
        if (CurrentProcess != null)
        {
            ErrorReceived?.Invoke("Đang có script khác chạy, vui lòng đợi.");
            return false;
        }

        var fullPath = Path.Combine(_projectRoot, "scripts", scriptPath);
        if (!File.Exists(fullPath))
        {
            ErrorReceived?.Invoke($"Không tìm thấy script: {fullPath}");
            return false;
        }

        var exe = pythonExe ?? _pythonExe;
        var psi = new ProcessStartInfo
        {
            FileName = exe,
            Arguments = $"-u \"{fullPath}\" {args}",
            WorkingDirectory = _projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
        };
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        psi.EnvironmentVariables["PYTHONUTF8"] = "1";

        using var process = new Process { StartInfo = psi };

        process.OutputDataReceived += (s, e) =>
        {
            if (e.Data != null) OutputReceived?.Invoke(e.Data);
        };
        process.ErrorDataReceived += (s, e) =>
        {
            if (e.Data != null) ErrorReceived?.Invoke(e.Data);
        };

        try
        {
            process.Start();
            CurrentProcess = process;
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            await process.WaitForExitAsync(ct);
            return process.ExitCode == 0;
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(true); } catch { }
            return false;
        }
        finally
        {
            CurrentProcess = null;
        }
    }

    public void KillCurrentProcess()
    {
        CurrentProcess?.Kill(true);
        CurrentProcess = null;
    }

    public async Task<List<string>> GetChapterListAsync(string slug, string langHint = "auto")
    {
        var chapters = new List<string>();
        var chunksDir = Path.Combine(_projectRoot, "working", "chunks", slug);
        if (!Directory.Exists(chunksDir)) return chapters;

        try
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var f in Directory.GetFiles(chunksDir, "chunk-*.json").OrderBy(x => x))
            {
                try
                {
                    var json = await File.ReadAllTextAsync(f);
                    using var doc = System.Text.Json.JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("chapter", out var ch))
                    {
                        var name = ch.GetString();
                        if (!string.IsNullOrWhiteSpace(name) && seen.Add(name))
                            chapters.Add(name);
                    }
                }
                catch { }
            }
        }
        catch { }
        return chapters;
    }

    public async Task<bool> RunAudiobookAsync(string slug, string temperature = "0.3",
        string topK = "10", string bitrate = "128k", bool readTitles = true,
        bool merge = false, bool force = false, string chapters = "",
        bool useGpu = true, int batchSize = 16, bool musicAuto = true,
        double musicVolume = 0.15, bool isSample = false, int sampleChars = 400,
        CancellationToken ct = default)
    {
        var vieneuPython = Path.Combine(_projectRoot, "working", "venv-vieneu", "Scripts", "python.exe");
        if (!File.Exists(vieneuPython))
        {
            ErrorReceived?.Invoke($"[Lỗi] Không tìm thấy working/venv-vieneu. Chạy: python -m venv working/venv-vieneu && working/venv-vieneu/Scripts/pip install vieneu");
            return false;
        }

        var args = $"--slug \"{slug}\" --temperature {temperature} --top-k {topK} --bitrate {bitrate}";
        if (useGpu) args += $" --gpu --batch-size {batchSize}";
        if (musicAuto) args += $" --music-auto --music-volume {musicVolume.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)}";
        if (!readTitles) args += " --no-read-titles";
        if (merge) args += " --merge";
        if (force) args += " --force";
        if (isSample) args += $" --sample --sample-chars {sampleChars}";
        if (!string.IsNullOrWhiteSpace(chapters) && !isSample)
        {
            var parts = chapters.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length > 0)
            {
                args += " --chapter " + string.Join(" ", parts);
            }
        }
        return await RunScriptAsync("audiobook/audiobook_long.py", args, ct, vieneuPython);
    }

    public async Task<bool> RunTranslateHelperAsync(string chunksDir, string progressDir,
        string glossary, CancellationToken ct = default)
    {
        var args = $"--interactive --chunks-dir \"{chunksDir}\" --progress-dir \"{progressDir}\" --glossary \"{glossary}\"";
        return await RunScriptAsync("translate/translate_helper.py", args, ct);
    }

    public async Task<bool> RunPipelineAsync(string inputPath, string bookName, string lang = "auto",
        int fromStep = 1, int toStep = 10, bool force = false, string author = "",
        CancellationToken ct = default)
    {
        var args = $"--input \"{inputPath}\" --book \"{bookName}\" --lang {lang} " +
                   $"--from-step {fromStep} --to-step {toStep}";
        if (force) args += " --force";
        if (!string.IsNullOrWhiteSpace(author)) args += $" --author \"{author}\"";
        return await RunScriptAsync("pipeline/run_pipeline.py", args, ct);
    }

    public async Task<bool> RunExtractAsync(string inputPath, string slug, string lang = "auto",
        CancellationToken ct = default)
    {
        var ext = Path.GetExtension(inputPath).ToLower();
        if (ext == ".pdf")
        {
            var args = $"--input \"{inputPath}\" --output \"working/extracted/{slug}/raw.md\" --lang {lang} --device cuda";
            return await RunScriptAsync("extract/mineru_extract.py", args, ct);
        }
        else if (ext == ".epub")
        {
            var args = $"--input \"{inputPath}\" --output \"working/extracted/{slug}/raw.md\"";
            return await RunScriptAsync("extract/epub_extract.py", args, ct);
        }
        else
        {
            ErrorReceived?.Invoke($"Không hỗ trợ trích xuất file: {ext}");
            return false;
        }
    }

    public async Task<bool> RunPostExtractQcAsync(string rawMdPath, string reportPath, string lang = "zh", CancellationToken ct = default)
    {
        var args = $"--input \"{rawMdPath}\" --report \"{reportPath}\" --lang {lang}";
        return await RunScriptAsync("process/post_extract_qc.py", args, ct);
    }

    public async Task<bool> RunOpenccAsync(string inputRaw, string outputRaw, string config = "t2s", CancellationToken ct = default)
    {
        var args = $"--input \"{inputRaw}\" --output \"{outputRaw}\" --config {config}";
        return await RunScriptAsync("process/opencc_normalize.py", args, ct);
    }

    public async Task<bool> RunChunkAsync(string rawMdPath, string outputDir,
        CancellationToken ct = default, int minChars = 800, int maxChars = 1600, string lang = "zh")
    {
        // Lưu ý: chunk_text.py mặc định --lang en (đếm theo từ). Sách ZH phải truyền --lang zh (đếm chữ Hán)
        var args = $"--input \"{rawMdPath}\" --output-dir \"{outputDir}\" --strategy smart --lang {lang} --min-chars {minChars} --max-chars {maxChars}";
        return await RunScriptAsync("process/chunk_text.py", args, ct);
    }

    public async Task<bool> RunSkeletonAsync(string chunksDir, string progressDir,
        CancellationToken ct = default)
    {
        var args = $"--chunks-dir \"{chunksDir}\" --progress-dir \"{progressDir}\" --force";
        return await RunScriptAsync("translate/init_trilingual_skeleton.py", args, ct);
    }

    public async Task<bool> RunBookProfileAsync(string chunksDir, string progressDir, CancellationToken ct = default)
    {
        var args = $"--chunks-dir \"{chunksDir}\" --progress-dir \"{progressDir}\"";
        return await RunScriptAsync("translate/create_book_profile.py", args, ct);
    }

    public async Task<bool> RunGlossaryAsync(string sourceDir, string bookName,
        string outputPath, CancellationToken ct = default)
    {
        var args = $"--source-dir \"{sourceDir}\" --book-name \"{bookName}\" --output \"{outputPath}\"";
        return await RunScriptAsync("process/generate_glossary.py", args, ct);
    }

    public async Task<bool> RunMergeAsync(string slug, string format = "trilingual",
        string outputDir = "", bool force = true, CancellationToken ct = default)
    {
        var progressDir = Path.Combine(_projectRoot, "working", "progress", slug);
        var args = $"--progress-dir \"{progressDir}\" --book-name \"{slug}\" --format {format}";
        if (force) args += " --force";
        if (!string.IsNullOrWhiteSpace(outputDir)) args += $" --output-dir \"{outputDir}\"";
        return await RunScriptAsync("output/merge_chunks.py", args, ct);
    }

    public async Task<bool> RunMakeEpubAsync(string mdPath, string title = "",
        string author = "", string resourcePath = "", CancellationToken ct = default)
    {
        var args = $"\"{mdPath}\"";
        if (!string.IsNullOrWhiteSpace(title)) args += $" --title \"{title}\"";
        if (!string.IsNullOrWhiteSpace(author)) args += $" --author \"{author}\"";
        if (!string.IsNullOrWhiteSpace(resourcePath)) args += $" --resource-path \"{resourcePath}\"";
        return await RunScriptAsync("output/make_epub.py", args, ct);
    }

    public async Task<bool> RunQaAsync(string source, string translation, string lang,
        string glossary = "", double threshold = 5.0, string reportPath = "",
        CancellationToken ct = default)
    {
        var args = $"--source \"{source}\" --translation \"{translation}\" --lang {lang} " +
                   $"--threshold {threshold}";
        if (!string.IsNullOrWhiteSpace(glossary)) args += $" --glossary \"{glossary}\"";
        if (!string.IsNullOrWhiteSpace(reportPath)) args += $" --report \"{reportPath}\"";
        return await RunScriptAsync("qa/glossary_qa.py", args, ct);
    }

    public async Task<bool> RunBatchQaAsync(string progressDir, int chunkId, CancellationToken ct = default)
    {
        var args = $"--progress-dir \"{progressDir}\" --chunk-id {chunkId}";
        return await RunScriptAsync("qa/batch_qa.py", args, ct);
    }

    public async Task<bool> RunManageInputAsync(CancellationToken ct = default)
    {
        return await RunScriptAsync("manage_input.py", "", ct);
    }

    public async Task<bool> RunMergeSentencesAsync(string inputMdPath, CancellationToken ct = default)
    {
        var args = $"--input \"{inputMdPath}\"";
        return await RunScriptAsync("output/merge_sentences.py", args, ct);
    }

    public async Task<bool> RunManageVoiceAsync(string subArgs, CancellationToken ct = default)
    {
        var vieneuPython = Path.Combine(_projectRoot, "working", "venv-vieneu", "Scripts", "python.exe");
        if (!File.Exists(vieneuPython))
        {
            ErrorReceived?.Invoke("[Lỗi] Không tìm thấy working/venv-vieneu. Chạy: pip install vieneu");
            return false;
        }
        return await RunScriptAsync("audiobook/manage_voice.py", subArgs, ct, vieneuPython);
    }

    public async Task<List<string>> GetVoiceListAsync()
    {
        var voices = new List<string>();
        var voicesDir = Path.Combine(_projectRoot, "core", "voices");
        if (!Directory.Exists(voicesDir)) return voices;

        var activeJson = Path.Combine(voicesDir, "active.json");
        if (File.Exists(activeJson))
        {
            try
            {
                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(activeJson));
                if (doc.RootElement.TryGetProperty("name", out var n) && !string.IsNullOrEmpty(n.GetString()))
                {
                    voices.Add(n.GetString()!);
                }
            }
            catch { }
        }

        foreach (var d in Directory.GetDirectories(voicesDir).OrderBy(x => x))
        {
            var metaFile = Path.Combine(d, "metadata.json");
            if (File.Exists(metaFile))
            {
                var name = Path.GetFileName(d);
                if (!voices.Contains(name))
                    voices.Add(name);
            }
        }
        return voices;
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

        using var process = Process.Start(psi);
        if (process == null)
        {
            ErrorReceived?.Invoke("Không thể khởi động process git.");
            return false;
        }
        var output = await process.StandardOutput.ReadToEndAsync(ct);
        OutputReceived?.Invoke(output);
        await process.WaitForExitAsync(ct);
        return process.ExitCode == 0;
    }
}
