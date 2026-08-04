"""
translate.py - CLI thân thiện cho người dùng không chuyên tech

Thay vì phải nhớ lệnh PowerShell dài, chỉ cần:
    1. Double-click file translate.bat
    2. Chọn số trong menu
    3. Làm theo hướng dẫn

KHÔNG cần nhớ:
- Đường dẫn file
- Cú pháp Python/PowerShell
- Tham số script
- Lệnh git
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

setup_encoding()

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    console = Console()
except ImportError:
    console = None
    Panel = None
    Prompt = None
    Confirm = None
    Table = None


# ============== TIỆN ÍCH HIỂN THỊ ==============

def in_thuong(text):
    """In text, dùng rich nếu có."""
    if console:
        console.print(text)
    else:
        print(text)


def in_noi_bat(text):
    """In text nổi bật (heading)."""
    if console:
        console.print(f"\n[bold cyan]{text}[/bold cyan]\n")
    else:
        print(f"\n=== {text} ===\n")


def in_loi(text):
    """In lỗi (màu đỏ)."""
    if console:
        console.print(f"[bold red]❌ {text}[/bold red]")
    else:
        print(f"[LỖI] {text}")


def in_thanh_cong(text):
    """In thành công (màu xanh)."""
    if console:
        console.print(f"[bold green]✅ {text}[/bold green]")
    else:
        print(f"[OK] {text}")


def in_canh_bao(text):
    """In cảnh báo (màu vàng)."""
    if console:
        console.print(f"[bold yellow]⚠️  {text}[/bold yellow]")
    else:
        print(f"[CẢNH BÁO] {text}")


def hoi_so(cau_hoi, mac_dinh=None, lua_chon=None):
    """Hỏi user chọn số. Trả về int."""
    if console and Prompt:
        return int(Prompt.ask(cau_hoi, default=str(mac_dinh) if mac_dinh else "", choices=[str(x) for x in lua_chon] if lua_chon else None))
    else:
        prompt = f"{cau_hoi}"
        if lua_chon:
            prompt += f" [{'/'.join(map(str, lua_chon))}]"
        if mac_dinh is not None:
            prompt += f" (mặc định: {mac_dinh})"
        prompt += ": "
        while True:
            try:
                tra_loi = input(prompt).strip()
                if not tra_loi and mac_dinh is not None:
                    return int(mac_dinh)
                gia_tri = int(tra_loi)
                if lua_chon and gia_tri not in lua_chon:
                    print(f"  Vui lòng chọn trong {lua_chon}")
                    continue
                return gia_tri
            except ValueError:
                print("  Vui lòng nhập số")


def hoi_text(cau_hoi, mac_dinh=None):
    """Hỏi user nhập text. Trả về str."""
    if console and Prompt:
        return Prompt.ask(cau_hoi, default=mac_dinh or "").strip()
    else:
        prompt = f"{cau_hoi}"
        if mac_dinh:
            prompt += f" (mặc định: {mac_dinh})"
        prompt += ": "
        tra_loi = input(prompt).strip()
        return tra_loi or (mac_dinh or "")


def hoi_yes_no(cau_hoi, mac_dinh=True):
    """Hỏi yes/no. Trả về bool."""
    if console and Confirm:
        return Confirm.ask(cau_hoi, default=mac_dinh)
    else:
        prompt = f"{cau_hoi} [{'Y/n' if mac_dinh else 'y/N'}]: "
        while True:
            tra_loi = input(prompt).strip().lower()
            if not tra_loi:
                return mac_dinh
            if tra_loi in ('y', 'yes', 'có', 'co'):
                return True
            if tra_loi in ('n', 'no', 'không', 'khong'):
                return False
            print("  Vui lòng trả lời y/n")


def mo_file_bang_app(path: Path):
    """Mở file bằng app mặc định (Windows)."""
    if sys.platform == 'win32':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


def chay_script(ten_script, args):
    """Chạy 1 script con, trả về True nếu OK."""
    script_path = PROJECT_ROOT / "scripts" / ten_script
    if not script_path.exists():
        in_loi(f"Không tìm thấy script: {ten_script}")
        return False
    cmd = [sys.executable, str(script_path)] + args
    in_thuong(f"\n$ {' '.join(cmd)}\n")
    try:
        return subprocess.run(cmd, check=True).returncode == 0
    except subprocess.CalledProcessError:
        return False


# ============== CÁC BƯỚC NGHIỆP VỤ ==============

def buoc_1_tao_du_an_moi():
    """Wizard tạo dự án dịch mới."""
    in_noi_bat("📕 BƯỚC 1: TẠO DỰ ÁN MỚI")

    # 1. Chọn file
    input_dir = PROJECT_ROOT / "input"
    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([f for f in input_dir.iterdir() if f.is_file()])
    if not files:
        in_loi(f"Không có file nào trong {input_dir}")
        in_thuong(f"\n💡 Hãy copy file gốc (.pdf, .epub, .srt, .docx, .png...) vào:")
        in_thuong(f"   {input_dir}")
        in_thuong("   rồi chạy lại tool này.\n")
        return

    in_thuong(f"File có sẵn trong {input_dir.name}\\:")
    for i, f in enumerate(files, 1):
        in_thuong(f"  {i}. {f.name}")

    chon = hoi_so(f"\nChọn file (1-{len(files)})", mac_dinh=1, lua_chon=list(range(1, len(files) + 1)))
    file_nguon = files[chon - 1]
    in_thuong(f"\n→ Đã chọn: {file_nguon.name}")

    # 2. Slug
    ten_co_so = file_nguon.stem.lower()
    ten_co_so = ''.join(c if c.isalnum() or c in '-_' else '-' for c in ten_co_so)
    ten_co_so = '-'.join(filter(None, ten_co_so.split('-')))[:50]
    slug = hoi_text(f"Slug cho sách (a-z, 0-9, dấu gạch ngang)", mac_dinh=ten_co_so)
    if not slug:
        in_loi("Slug không được rỗng")
        return

    # 3. Ngôn ngữ
    in_thuong("\nNgôn ngữ gốc:")
    in_thuong("  1. Tiếng Anh (EN)")
    in_thuong("  2. Tiếng Trung (ZH)")
    in_thuong("  3. Tự phát hiện (chỉ áp dụng cho EPUB/PDF text)")
    lang_chon = hoi_so("Chọn", mac_dinh=3, lua_chon=[1, 2, 3])
    lang_map = {1: 'en', 2: 'zh', 3: 'auto'}
    lang = lang_map[lang_chon]

    # 4. Tạo thư mục
    in_noi_bat(f"\nTạo thư mục cho '{slug}'...")
    for sub in ['extracted', 'chunks', 'progress', 'summary', 'qa']:
        d = PROJECT_ROOT / "working" / sub / slug
        d.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "books" / slug / "final").mkdir(parents=True, exist_ok=True)
    in_thanh_cong("Đã tạo thư mục")

    # 5. Copy glossary
    glos_md = PROJECT_ROOT / "glossary" / f"{slug}.md"
    glos_csv = PROJECT_ROOT / "glossary" / f"{slug}.csv"
    if not glos_md.exists():
        shutil.copy(PROJECT_ROOT / "glossary" / "_template.md", glos_md)
        shutil.copy(PROJECT_ROOT / "glossary" / "_template.csv", glos_csv)
        in_thanh_cong(f"Đã tạo glossary: glossary\\{slug}.md và .csv")
    else:
        in_thuong(f"Glossary đã tồn tại: glossary\\{slug}.md")

    # 6. Trích xuất
    in_noi_bat(f"\nTrích xuất file '{file_nguon.name}'...")
    suffix = file_nguon.suffix.lower()
    raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"

    if suffix == '.epub':
        if chay_script('epub_extract.py', ['--input', str(file_nguon), '--output', str(raw_md)]):
            in_thanh_cong("Trích xuất EPUB xong")
        else:
            in_loi("Trích xuất EPUB thất bại")
            return
    elif suffix == '.srt':
        shutil.copy(file_nguon, raw_md.with_suffix('.srt'))
        in_thanh_cong("Đã copy SRT vào working/extracted/")
    elif suffix in {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}:
        if lang == 'auto':
            lang = 'en'  # mặc định
        if chay_script('mineru_extract.py', ['--input', str(file_nguon), '--output', str(raw_md), '--lang', lang]):
            in_thanh_cong("Trích xuất xong")
        else:
            in_loi("Trích xuất thất bại")
            return
    else:
        in_loi(f"Định dạng {suffix} chưa hỗ trợ trong CLI này. Dùng script trực tiếp.")
        return

    # 7. Detect language + OpenCC (nếu ZH Phồn)
    if suffix != '.srt':
        in_noi_bat("\nPhát hiện ngôn ngữ...")
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "detect_language.py"), str(raw_md), '--quiet'],
            capture_output=True, text=True
        )
        detected = result.stdout.strip()
        in_thuong(f"Ngôn ngữ phát hiện: {detected}")

        if detected == 'zh-Hant' and chay_script('opencc_normalize.py', [
            '--input', str(raw_md),
            '--output', str(PROJECT_ROOT / "working" / "extracted" / slug / "raw-hans.md"),
            '--config', 't2s'
        ]):
            in_thanh_cong("Đã chuẩn hóa Phồn → Giản")
            raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw-hans.md"
            lang = 'zh'

    # 8. Chia chunk
    in_noi_bat("\nChia chunk...")
    min_chars = 1500 if (lang == 'zh' or detected.startswith('zh')) else 3000
    max_chars = 3000 if (lang == 'zh' or detected.startswith('zh')) else 8000
    if chay_script('chunk_text.py', [
        '--input', str(raw_md),
        '--output-dir', str(PROJECT_ROOT / "working" / "chunks" / slug),
        '--lang', 'zh' if (lang == 'zh' or detected.startswith('zh')) else 'en',
        '--min-chars', str(min_chars),
        '--max-chars', str(max_chars),
        '--overlap-chars', '200',
        '--respect-headings',
    ]):
        in_thanh_cong("Chia chunk xong")
    else:
        in_loi("Chia chunk thất bại")
        return

    # 9. Mở chunk đầu tiên
    chunks_dir = PROJECT_ROOT / "working" / "chunks" / slug
    chunks = sorted(chunks_dir.glob("chunk-*.md"))
    in_noi_bat(f"\n🎉 DỰ ÁN '{slug}' ĐÃ SẴN SÀNG!")
    in_thuong(f"  Tổng: {len(chunks)} chunk")
    in_thuong(f"  Chunk tiếp theo: chunk-001.md\n")

    if chunks and hoi_yes_no("Mở chunk-001.md bằng editor để bắt đầu dịch?"):
        mo_file_bang_app(chunks[0])
        in_thuong(f"\n💡 Bước tiếp: paste nội dung chunk vào chat AI để dịch.")
        in_thuong(f"   Xem mẫu chat trong: docs/chat-templates.md (sắp có)")


def sync_progress_to_output(slug):
    """Đồng bộ bản dịch từ working/progress/<slug> sang output/<slug>/chunk-*.md.

    Giúp CLI nhận diện chunk đã dịch và để QA/commit (menu cũ) hoạt động
    với pipeline trilingual (nguồn chính là progress JSON).
    """
    import json, re
    progress_dir = PROJECT_ROOT / "working" / "progress" / slug
    output_dir = PROJECT_ROOT / "output" / "books" / slug / "final"
    if not progress_dir.exists():
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for pf in sorted(progress_dir.glob("chunk_*.json")):
        try:
            data = json.loads(pf.read_text(encoding='utf-8'))
        except Exception:
            continue
        cid = data.get('chunk_id')
        text = (data.get('translated_text') or '').strip()
        if cid is None or not text:
            continue
        out = output_dir / f"chunk-{int(cid):03d}.md"
        out.write_text(text + '\n', encoding='utf-8')
        n += 1
    if n:
        in_thanh_cong(f"Đã đồng bộ {n} chunk vào output\\{slug}\\")
    return n


def buoc_2_tiep_tuc_du_an():
    """Tiếp tục dự án đang dịch."""
    in_noi_bat("📖 BƯỚC 2: TIẾP TỤC DỰ ÁN ĐANG DỊCH")

    import json
    chunks_root = PROJECT_ROOT / "working" / "chunks"
    if not chunks_root.exists():
        in_loi(f"Chưa có dự án nào trong {chunks_root}")
        return

    projects = sorted([d.name for d in chunks_root.iterdir() if d.is_dir()])
    if not projects:
        in_loi("Chưa có dự án nào trong working/chunks/")
        in_thuong(f"\n💡 Chạy 'Bước 1: Tạo dự án mới' trước.")
        return

    in_thuong("Dự án đang có:")
    for i, p in enumerate(projects, 1):
        # Đếm chunks (ưu tiên progress JSON — pipeline trilingual)
        pd = PROJECT_ROOT / "working" / "progress" / p
        pfiles = sorted(pd.glob("chunk_*.json")) if pd.exists() else []
        if pfiles:
            n_chunks = len(pfiles)
            n_done = 0
            for pf in pfiles:
                try:
                    d = json.loads(pf.read_text(encoding='utf-8'))
                    if (d.get('translated_text') or '').strip():
                        n_done += 1
                except Exception:
                    pass
        else:
            n_chunks = len(list((chunks_root / p).glob("chunk-*.md")))
            n_done = len(list((PROJECT_ROOT / "output" / p).glob("chunk-*.md")))
        in_thuong(f"  {i}. {p}  (đã dịch {n_done}/{n_chunks} chunks)")

    chon = hoi_so(f"\nChọn dự án (1-{len(projects)})", mac_dinh=1, lua_chon=list(range(1, len(projects) + 1)))
    slug = projects[chon - 1]
    in_thuong(f"\n→ Đã chọn: {slug}")

    import re, json

    def _load_progress(p):
        try:
            return json.loads(Path(p).read_text(encoding='utf-8'))
        except Exception:
            return None

    def _sort(files):
        return sorted(files, key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))

    chunks_md = _sort(list((chunks_root / slug).glob("chunk-*.md")))
    chunks_json = _sort(list((chunks_root / slug).glob("chunk-*.json")))
    progress_dir = PROJECT_ROOT / "working" / "progress" / slug
    progress_files = _sort(list(progress_dir.glob("chunk_*.json"))) if progress_dir.exists() else []
    output_dir = PROJECT_ROOT / "output" / "books" / slug / "final"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tìm chunk tiếp theo cần dịch (ưu tiên progress JSON — pipeline trilingual)
    chunk_id = None
    file_nguon = None
    if progress_files:
        for pf in progress_files:
            d = _load_progress(pf)
            if d and not (d.get('translated_text') or '').strip():
                chunk_id = int(d.get('chunk_id', -1))
                file_nguon = pf
                break
    if chunk_id is None and chunks_md:
        for c in chunks_md:
            if not (output_dir / c.name).exists():
                m = re.search(r'\d+', c.name)
                chunk_id = int(m.group()) if m else None
                file_nguon = c
                break

    # Nếu hết chunk: ghép file hoàn chỉnh
    if chunk_id is None:
        in_thanh_cong("Đã dịch xong tất cả chunks!")
        in_thuong(f"\n💡 Bước tiếp: ghép file hoàn chỉnh")
        if progress_files and hoi_yes_no("Ghép thành file tam ngữ hoàn chỉnh (merge_chunks)?"):
            chay_script('merge_chunks.py', [
                '--progress-dir', str(progress_dir),
                '--book-name', slug,
                '--format', 'trilingual',
                '--force',
            ])
        elif chunks_md and hoi_yes_no(f"Ghép các chunk thành {slug}-vi.md?"):
            full = output_dir / f"{slug}-vi.md"
            translations = _sort(list(output_dir.glob("chunk-*.md")))
            with open(full, 'w', encoding='utf-8') as fout:
                for t in translations:
                    fout.write(t.read_text(encoding='utf-8'))
                    fout.write('\n\n---\n\n')
            in_thanh_cong(f"Đã ghép: {full}")
        return

    total = len(progress_files) if progress_files else len(chunks_md)
    if progress_files:
        n_da_xong = sum(1 for pf in progress_files if (_load_progress(pf) or {}).get('translated_text', '').strip())
    else:
        n_da_xong = sum(1 for c in chunks_md if (output_dir / c.name).exists())

    in_noi_bat(f"\n📝 Chunk tiếp theo: {chunk_id:03d}")
    in_thuong(f"  Đã xong: {n_da_xong}/{total}")
    if file_nguon:
        in_thuong(f"  File gốc: {file_nguon}")

    in_thuong("\nCách dịch: AI chat (agent opencode) sẽ tự động dịch chunk này.")
    in_thuong("Bạn không cần copy/paste — chỉ cần nói với AI: \"dịch tiếp sách " + slug + "\"")

    if not progress_files and chunks_json:
        in_noi_bat("\nTạo skeleton progress (tách câu + pinyin)...")
        if chay_script('init_trilingual_skeleton.py', [
            '--chunks-dir', str(chunks_root / slug),
            '--progress-dir', str(progress_dir),
        ]):
            progress_files = _sort(list(progress_dir.glob("chunk_*.json"))) if progress_dir.exists() else []

    # === AI CHAT (agent opencode tự động dịch) ===
    in_thanh_cong("\nAI chat sẽ tự động dịch — bạn không cần copy/paste.")
    in_thuong("Hãy nói với opencode (AI): \"dịch tiếp sách " + slug + "\"")
    in_thuong("AI sẽ tự đọc working/progress/" + slug + "/, dịch dòng-đối-dòng từng")
    in_thuong("chunk chưa xong và lưu lại (giống các cuốn đã dịch trước đây).\n")
    if hoi_yes_no("Bản dịch đã xong (AI đã lưu vào progress JSON)?"):
        sync_progress_to_output(slug)
        in_thanh_cong("Đã đồng bộ bản dịch sang output!")
    else:
        in_thuong("OK — quay lại menu này sau khi AI dịch xong.\n")


def buoc_3_chay_qa(slug=None):
    """Chạy QA cho chunk."""
    in_noi_bat("🔍 BƯỚC 3: CHẠY QA")

    if not slug:
        chunks_root = PROJECT_ROOT / "working" / "chunks"
        projects = sorted([d.name for d in chunks_root.iterdir() if d.is_dir()])
        if not projects:
            in_loi("Chưa có dự án nào")
            return
        chon = hoi_so(f"Chọn dự án (1-{len(projects)})", mac_dinh=1, lua_chon=list(range(1, len(projects) + 1)))
        slug = projects[chon - 1]

    in_thuong(f"Đang chạy QA cho dự án: {slug}")
    # Tìm tất cả file chunk đã dịch
    output_dir = PROJECT_ROOT / "output" / "books" / slug / "final"
    qa_dir = PROJECT_ROOT / "working" / "qa" / slug
    qa_dir.mkdir(parents=True, exist_ok=True)
    glossary_csv = PROJECT_ROOT / "glossary" / f"{slug}.csv"

    # Detect genre
    genre_csv = None
    for g in (PROJECT_ROOT / "glossary" / "genres").glob("*.csv"):
        if g.stem in ['tien-hiep', 'ky-nghiep', 'ky-thuat-it']:
            # Check if any row in this CSV matches our book (rough heuristic)
            genre_csv = g
            break

    # Detect language
    raw = PROJECT_ROOT / "working" / "extracted" / slug / "raw-hans.md"
    if not raw.exists():
        raw = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
    if raw.exists():
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "detect_language.py"), str(raw), '--quiet'],
            capture_output=True, text=True
        )
        detected = result.stdout.strip()
        lang = 'zh' if detected.startswith('zh') else 'en'
    else:
        lang = hoi_text("Ngôn ngữ (en/zh)", mac_dinh='en')

    # QA từng chunk
    import re
    translations = sorted(output_dir.glob("chunk-*.md"), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    if not translations:
        in_loi(f"Chưa có bản dịch nào trong {output_dir}")
        return

    n_ok = 0
    n_loi = 0
    for t in translations:
        source = PROJECT_ROOT / "working" / "chunks" / slug / t.name
        if not source.exists():
            continue
        qa_report = qa_dir / t.name.replace('.md', '-qa.md')
        args = [
            '--source', str(source),
            '--translation', str(t),
            '--lang', lang,
            '--report', str(qa_report),
        ]
        if glossary_csv.exists():
            args.extend(['--glossary', str(glossary_csv)])
        if genre_csv:
            args.extend(['--genre-glossary', str(genre_csv)])
        if not chay_script('glossary_qa.py', args):
            n_loi += 1
        else:
            n_ok += 1

    in_thuong("")
    in_thuong(f"  QA xong: {n_ok} chunks OK, {n_loi} có lỗi")
    if n_loi > 0:
        in_canh_bao(f"Xem báo cáo chi tiết trong: {qa_dir}")
    else:
        in_thanh_cong("Tất cả chunks đều OK!")


def buoc_4_git_commit(slug=None, ten_file=None):
    """Git commit chunk vừa dịch."""
    in_noi_bat("💾 BƯỚC 4: GIT COMMIT")

    if not slug:
        chunks_root = PROJECT_ROOT / "working" / "chunks"
        projects = sorted([d.name for d in chunks_root.iterdir() if d.is_dir()])
        if not projects:
            in_loi("Chưa có dự án nào")
            return
        chon = hoi_so(f"Chọn dự án (1-{len(projects)})", mac_dinh=1, lua_chon=list(range(1, len(projects) + 1)))
        slug = projects[chon - 1]

    # Kiểm tra git
    if not (PROJECT_ROOT / ".git").exists():
        in_loi("Chưa khởi tạo git. Chạy 'Bước 6: Cài đặt' trước.")
        return

    if ten_file:
        files_to_add = [f"output/{slug}/{ten_file}"]
    else:
        files_to_add = [f"output/{slug}/chunk-*.md"]

    # Thêm glossary
    if (PROJECT_ROOT / "glossary" / f"{slug}.md").exists():
        files_to_add.append(f"glossary/{slug}.md")
    if (PROJECT_ROOT / "glossary" / f"{slug}.csv").exists():
        files_to_add.append(f"glossary/{slug}.csv")

    msg = f"feat({slug}): {ten_file or 'translation update'}"
    if not hoi_yes_no(f"Commit với message: '{msg}'?"):
        msg = hoi_text("Nhập message khác", mac_dinh=msg)

    cmd = ['git', 'add'] + files_to_add
    in_thuong(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)

    cmd = ['git', 'commit', '-m', msg]
    in_thuong(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        in_thanh_cong("Commit thành công")
    else:
        in_canh_bao("Commit có vấn đề (xem output ở trên)")


def buoc_5_them_glossary():
    """Mở file glossary để thêm thuật ngữ mới."""
    in_noi_bat("📚 BƯỚC 5: THÊM/SỬA GLOSSARY")

    glossary_dir = PROJECT_ROOT / "glossary"
    files = sorted([f for f in glossary_dir.glob("*.md") if not f.name.startswith('_')])
    if not files:
        in_loi("Chưa có glossary nào. Tạo dự án mới trước.")
        return

    in_thuong("Glossary hiện có:")
    for i, f in enumerate(files, 1):
        in_thuong(f"  {i}. {f.stem}  ({f.name})")
    in_thuong(f"  {len(files) + 1}. ➕ Tạo glossary mới (copy từ _template)")
    in_thuong(f"  {len(files) + 2}. 📖 Mở thư mục glossary")

    chon = hoi_so(f"Chọn (1-{len(files) + 2})", mac_dinh=1, lua_chon=list(range(1, len(files) + 3)))

    if chon == len(files) + 1:
        ten = hoi_text("Tên glossary (không đuôi .md)")
        if ten:
            for ext in ('.md', '.csv'):
                src = PROJECT_ROOT / "glossary" / f"_template{ext}"
                dst = PROJECT_ROOT / "glossary" / f"{ten}{ext}"
                if not dst.exists():
                    shutil.copy(src, dst)
            in_thanh_cong(f"Đã tạo: glossary\\{ten}.md và .csv")
            mo_file_bang_app(PROJECT_ROOT / "glossary" / f"{ten}.md")
        return
    elif chon == len(files) + 2:
        mo_file_bang_glossary_dir = subprocess.run(['explorer', str(glossary_dir)])
        return

    selected = files[chon - 1]
    in_thuong(f"\n→ Mở: {selected.name}")
    mo_file_bang_app(selected)

    # Mở cả CSV tương ứng nếu có
    csv_path = selected.with_suffix('.csv')
    if csv_path.exists():
        in_thuong(f"💡 Nhớ cập nhật cả {csv_path.name} (song song với {selected.name})")
        if hoi_yes_no("Mở luôn file CSV?"):
            mo_file_bang_app(csv_path)


def buoc_6_cai_dat():
    """Cài đặt: kiểm tra môi trường."""
    in_noi_bat("🔧 BƯỚC 6: KIỂM TRA MÔI TRƯỜNG")

    in_thuong("1. Python:")
    in_thuong(f"   {sys.version}")

    in_thuong("\n2. Virtual env (.venv):")
    if (PROJECT_ROOT / ".venv").exists():
        in_thanh_cong("   Có .venv")
    else:
        in_canh_bao("   Chưa có .venv")
        if hoi_yes_no("Tạo .venv và cài packages?"):
            subprocess.run([sys.executable, '-m', 'venv', '.venv'], cwd=PROJECT_ROOT, check=True)
            pip_path = PROJECT_ROOT / ".venv" / "Scripts" / "pip.exe"
            subprocess.run([str(pip_path), 'install', '-r', 'requirements.txt'], cwd=PROJECT_ROOT, check=True)
            in_thanh_cong("Đã tạo .venv + cài packages")

    in_thuong("\n3. Git:")
    result = subprocess.run(['git', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        in_thanh_cong(f"   {result.stdout.strip()}")
        if (PROJECT_ROOT / ".git").exists():
            in_thanh_cong("   Đã có git repo")
        else:
            in_canh_bao("   Chưa có git repo")
            if hoi_yes_no("Khởi tạo git repo?"):
                subprocess.run(['git', 'init'], cwd=PROJECT_ROOT, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Tên của bạn'], cwd=PROJECT_ROOT, check=False)
                subprocess.run(['git', 'config', 'user.email', 'email@example.com'], cwd=PROJECT_ROOT, check=False)
                in_thanh_cong("Đã init git. Nhớ set user.name/email.")
    else:
        in_loi("   Git chưa cài. Tải tại https://git-scm.com/download/win")

    in_thuong("\n4. MinerU:")
    mineru_path = shutil.which('mineru')
    if mineru_path:
        in_thanh_cong(f"   Đã cài: {mineru_path}")
    else:
        in_canh_bao("   Chưa cài MinerU CLI")
        in_thuong("   Cài bằng: pip install -U mineru (rồi chạy mineru-models-download)")

    in_thuong("\n5. Cấu trúc thư mục:")
    for sub in ['input', 'output', 'working', 'glossary', 'prompts', 'scripts']:
        d = PROJECT_ROOT / sub
        status = "✅" if d.exists() else "❌"
        in_thuong(f"   {status} {sub}/")


def buoc_0_thoat():
    in_thuong("\n👋 Tạm biệt! Chúc dịch vui.\n")
    sys.exit(0)


def buoc_7_song_ngu():
    """Tạo file song ngữ (gốc + dịch xen kẽ)."""
    in_noi_bat("📗 BƯỚC 7: TẠO FILE SONG NGỮ")

    output_dir = PROJECT_ROOT / "output" / "books"
    if not output_dir.exists():
        in_loi("Chưa có output nào")
        return

    projects = sorted([d.name for d in output_dir.iterdir() if d.is_dir()])
    if not projects:
        in_loi("Chưa có dự án nào trong output/books/")
        return

    in_thuong("Dự án có bản dịch:")
    for i, p in enumerate(projects, 1):
        vi_file = output_dir / p / "final" / "vi.md"
        exists = "✓" if vi_file.exists() else "✗"
        in_thuong(f"  {i}. {p}  [{exists}]")

    chon = hoi_so(f"\nChọn dự án (1-{len(projects)})", mac_dinh=1, lua_chon=list(range(1, len(projects) + 1)))
    slug = projects[chon - 1]

    # Find source file
    raw_candidates = [
        PROJECT_ROOT / "working" / "extracted" / slug / "raw-hans.md",
        PROJECT_ROOT / "working" / "extracted" / slug / "raw.md",
    ]
    source = None
    for c in raw_candidates:
        if c.exists():
            source = c
            break

    if not source:
        in_loi(f"Không tìm thấy file gốc trong working/extracted/{slug}/")
        return

    vi_file = output_dir / slug / f"{slug}-vi.md"
    if not vi_file.exists():
        in_loi(f"Không tìm thấy bản dịch: {vi_file}")
        return

    out_file = output_dir / slug / f"{slug}-songngu.md"

    # Detect language
    in_thuong("\nNgôn ngữ gốc:")
    in_thuong("  1. Tiếng Anh (EN)")
    in_thuong("  2. Tiếng Trung (ZH) — có Pinyin")
    lang_chon = hoi_so("Chọn", mac_dinh=1, lua_chon=[1, 2])
    lang = 'en' if lang_chon == 1 else 'zh'

    in_thuong(f"\nĐang tạo file song ngữ...")
    in_thuong(f"  Gốc: {source.name}")
    in_thuong(f"  Dịch: {vi_file.name}")
    in_thuong(f"  Output: {out_file.name}")

    cmd = [
        sys.executable, str(PROJECT_ROOT / "scripts" / "make_bilingual.py"),
        '--source', str(source),
        '--translation', str(vi_file),
        '--output', str(out_file),
        '--lang', lang,
    ]
    in_thuong(f"$ {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            in_thanh_cong(f"Đã tạo: {out_file}")
            if hoi_yes_no("Mở file song ngữ?"):
                mo_file_bang_app(out_file)
    except subprocess.CalledProcessError:
        in_loi("Tạo file song ngữ thất bại")


# ============== MENU CHÍNH ==============

def hien_menu_chinh():
    in_thuong("")
    if console:
        console.print(Panel.fit(
            "[bold cyan]📚 DỊCH SÁCH - Translate Book CLI[/bold cyan]\n"
            "[dim]Dành cho người không chuyên tech - hỏi đáp, không cần nhớ lệnh[/dim]",
            border_style="cyan"
        ))
    else:
        in_thuong("=" * 50)
        in_thuong("  DỊCH SÁCH - Translate Book CLI")
        in_thuong("  Dành cho người không chuyên tech")
        in_thuong("=" * 50)

    menu = [
        ("1", "📕", "Dịch sách MỚI (PDF / EPUB / SRT)"),
        ("2", "📖", "Tiếp tục sách ĐANG dịch"),
        ("3", "🔍", "Chạy QA tự động cho bản dịch"),
        ("4", "💾", "Git commit (lưu phiên bản)"),
        ("5", "📚", "Thêm/sửa Glossary (thuật ngữ)"),
        ("6", "🔧", "Kiểm tra môi trường (cài đặt)"),
        ("7", "📗", "Tạo file song ngữ (gốc + dịch xen kẽ)"),
        ("8", "❓", "Trợ giúp (đọc USAGE.md)"),
        ("0", "🚪", "Thoát"),
    ]
    for so, icon, mo_ta in menu:
        in_thuong(f"  [{so}] {icon}  {mo_ta}")
    in_thuong("")

    hanh_dong = {
        '1': buoc_1_tao_du_an_moi,
        '2': buoc_2_tiep_tuc_du_an,
        '3': buoc_3_chay_qa,
        '4': buoc_4_git_commit,
        '5': buoc_5_them_glossary,
        '6': buoc_6_cai_dat,
        '7': buoc_7_song_ngu,
        '8': lambda: mo_file_bang_app(PROJECT_ROOT / "USAGE.md"),
        '0': buoc_0_thoat,
    }

    lua_chon = hoi_so("Chọn [0-8]", mac_dinh=0, lua_chon=list(range(0, 9)))
    in_thuong("")
    hanh_dong[str(lua_chon)]()


def main():
    in_thuong("📚 DỊCH SÁCH - Translate Book CLI")
    in_thuong(f"   Thư mục: {PROJECT_ROOT}\n")

    while True:
        try:
            hien_menu_chinh()
        except KeyboardInterrupt:
            in_thuong("\n\n👋 Đã thoát.\n")
            break
        except EOFError:
            break

        in_thuong("\n" + "-" * 50)
        if not hoi_yes_no("Quay lại menu chính?", mac_dinh=True):
            break

    buoc_0_thoat()


if __name__ == '__main__':
    main()
