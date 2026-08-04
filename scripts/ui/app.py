"""
Translate Book — TUI Manager
Giao diện terminal đẹp cho quản lý dự án dịch sách.

Usage:
    python scripts/ui/app.py
"""
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import PROJECT_ROOT, setup_encoding

setup_encoding()

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.live import Live
    from rich.status import Status
except ImportError:
    print("Cần cài Rich: pip install rich")
    sys.exit(1)

console = Console(force_terminal=True)

# ─── Helpers ─────────────────────────────────────────────────────────────

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input_books():
    """Liệt kê file trong input/."""
    input_dir = PROJECT_ROOT / "input"
    if not input_dir.exists():
        return []
    return sorted([f.name for f in input_dir.iterdir()
                   if f.suffix.lower() in ('.pdf', '.epub', '.docx')])

def get_books_status():
    """Kiểm tra trạng thái từng cuốn sách."""
    books_dir = PROJECT_ROOT / "output" / "books"
    progress_dir = PROJECT_ROOT / "working" / "progress"
    chunks_dir = PROJECT_ROOT / "working" / "chunks"

    statuses = []

    # Sách có trong output (đã dịch xong)
    if books_dir.exists():
        for d in sorted(books_dir.iterdir()):
            if not d.is_dir():
                continue
            slug = d.name
            vi_md = d / "final" / "vi.md"
            epub = d / "trilingual.epub"
            audiobook_dir = d / "audiobook"
            mp3_count = len(list(audiobook_dir.glob("ch*.mp3"))) if audiobook_dir.exists() else 0

            # Đếm progress
            progress_count = 0
            total_chunks = 0
            progress_slug = progress_dir / slug
            if progress_slug.exists():
                progress_count = len(list(progress_slug.glob("chunk_*.json")))
            chunks_slug = chunks_dir / slug
            if chunks_slug.exists():
                total_chunks = len(list(chunks_slug.glob("chunk-*.json")))

            # Đếm audiobook progress
            audio_progress = PROJECT_ROOT / "working" / "progress_audio" / f"{slug}.json"
            audio_chapters = []
            if audio_progress.exists():
                import json
                try:
                    ap = json.loads(audio_progress.read_text(encoding='utf-8'))
                    audio_chapters = ap.get("completed_chapters", [])
                except Exception:
                    pass

            total_chapters = 0
            if vi_md.exists():
                # Đếm chapters từ vi.md
                content = vi_md.read_text(encoding='utf-8')
                import re
                total_chapters = len(re.findall(r'^# ', content, re.MULTILINE))

            statuses.append({
                "slug": slug,
                "has_vi_md": vi_md.exists(),
                "has_epub": epub.exists(),
                "mp3_count": mp3_count,
                "total_chapters": total_chapters,
                "progress_count": progress_count,
                "total_chunks": total_chunks,
                "audio_done": len(audio_chapters),
                "audio_total": total_chapters,
            })

    # Sách trong input nhưng chưa có output
    for f in get_input_books():
        slug = Path(f).stem.lower().replace(' ', '-')
        if not any(s["slug"] == slug for s in statuses):
            statuses.append({
                "slug": f"(input: {f})",
                "has_vi_md": False,
                "has_epub": False,
                "mp3_count": 0,
                "total_chapters": 0,
                "progress_count": 0,
                "total_chunks": 0,
                "audio_done": 0,
                "audio_total": 0,
            })

    return statuses

# ─── Screens ─────────────────────────────────────────────────────────────

def show_banner():
    banner = Text()
    banner.append("  ================================\n", style="bold cyan")
    banner.append("  |   TRANSLATE BOOK  v2.0       |\n", style="bold white")
    banner.append("  |   Dich sach tu dong bang AI   |\n", style="dim")
    banner.append("  ================================\n", style="bold cyan")
    console.print(banner)

def show_main_menu():
    console.print()
    table = Table(show_header=False, border_style="cyan", padding=(0, 2))
    table.add_column("STT", style="bold yellow", width=4)
    table.add_column("Tác vụ", style="white")
    table.add_row("1", "📖  Xem trạng thái sách")
    table.add_row("2", "🚀  Dịch sách mới")
    table.add_row("3", "▶️   Tiếp tục sách đang dở")
    table.add_row("4", "🎧  Tạo audiobook")
    table.add_row("5", "🔍  QA tự động")
    table.add_row("6", "💾  Git commit")
    table.add_row("7", "📊  Thống kê chi tiết")
    table.add_row("0", "🚪  Thoát")
    console.print(Panel(table, title="[bold]MENU[/bold]", border_style="cyan"))

def show_book_status():
    console.print()
    console.print(Rule("[bold]📚 TRẠNG THÁI SÁCH[/bold]", style="cyan"))

    statuses = get_books_status()
    if not statuses:
        console.print("  [dim]Chưa có sách nào. Đặt file PDF/EPUB vào input/[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Slug", style="white", max_width=35)
    table.add_column("Bản dịch", justify="center", width=10)
    table.add_column("EPUB", justify="center", width=6)
    table.add_column("Progress", justify="center", width=12)
    table.add_column("Audio", justify="center", width=12)

    for s in statuses:
        # Trạng thái bản dịch
        if s["has_vi_md"]:
            vi_status = "[green]✓[/green]"
        elif s["progress_count"] > 0:
            vi_status = f"[yellow]{s['progress_count']}/{s['total_chunks']}[/yellow]"
        else:
            vi_status = "[red]✗[/red]"

        # EPUB
        epub_status = "[green]✓[/green]" if s["has_epub"] else "[dim]—[/dim]"

        # Progress
        if s["total_chunks"] > 0:
            pct = s["progress_count"] / s["total_chunks"] * 100
            bar_len = 10
            filled = int(pct / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            progress_str = f"{bar} {pct:.0f}%"
        else:
            progress_str = "[dim]—[/dim]"

        # Audio
        if s["audio_total"] > 0:
            audio_str = f"{s['audio_done']}/{s['audio_total']} ch"
        elif s["mp3_count"] > 0:
            audio_str = f"[green]{s['mp3_count']}[/green] mp3"
        else:
            audio_str = "[dim]—[/dim]"

        table.add_row(s["slug"], vi_status, epub_status, progress_str, audio_str)

    console.print(table)

def show_detail_stats():
    console.print()
    console.print(Rule("[bold]📊 THỐNG KÊ CHI TIẾT[/bold]", style="cyan"))

    statuses = get_books_status()
    for s in statuses:
        if not s["has_vi_md"] and s["progress_count"] == 0:
            continue

        panel_content = []
        panel_content.append(f"  📁 Slug: [bold]{s['slug']}[/bold]")

        if s["has_vi_md"]:
            panel_content.append(f"  📝 Bản dịch: [green]✓[/green] (vi.md)")
        if s["has_epub"]:
            panel_content.append(f"  📕 EPUB: [green]✓[/green]")
        if s["total_chunks"] > 0:
            panel_content.append(f"  🧩 Chunks: {s['progress_count']}/{s['total_chunks']}")
        if s["total_chapters"] > 0:
            panel_content.append(f"  📑 Chapters: {s['total_chapters']}")
        if s["mp3_count"] > 0:
            panel_content.append(f"  🎧 Audio: {s['mp3_count']} files")
        if s["audio_done"] > 0:
            panel_content.append(f"  🎵 Audiobook: {s['audio_done']}/{s['audio_total']} chapters")

        console.print(Panel("\n".join(panel_content), title=f"[bold]{s['slug']}[/bold]", border_style="blue"))

def run_audiobook():
    console.print()
    console.print(Rule("[bold]🎧 TẠO AUDIOBOOK[/bold]", style="cyan"))

    # Tìm sách có vi.md
    books_dir = PROJECT_ROOT / "output" / "books"
    if not books_dir.exists():
        console.print("  [red]Không tìm thấy output/books/[/red]")
        return

    available = []
    for d in sorted(books_dir.iterdir()):
        if d.is_dir() and (d / "final" / "vi.md").exists():
            available.append(d.name)

    if not available:
        console.print("  [dim]Chưa có sách nào có bản dịch[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("STT", width=4)
    table.add_column("Sách", style="white")

    for i, slug in enumerate(available, 1):
        table.add_row(str(i), slug)

    console.print(table)

    choice = Prompt.ask("\nChọn sách", default="1")
    try:
        idx = int(choice) - 1
        slug = available[idx]
    except (ValueError, IndexError):
        console.print("  [red]Lựa chọn không hợp lệ[/red]")
        return

    voice = Prompt.ask("Voice ( Enter = active)", default="")
    temp = Prompt.ask("Temperature ( Enter = 0.3)", default="0.3")
    top_k = Prompt.ask("Top-k ( Enter = 10)", default="10")

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "audiobook" / "audiobook_long.py"),
        "--slug", slug,
        "--temperature", temp,
        "--top-k", top_k,
        "--force",
    ]
    if voice:
        cmd.extend(["--voice", voice])

    console.print(f"\n  [cyan]Chạy: {' '.join(cmd[-6:])}[/cyan]\n")

    if Confirm.ask("  Bắt đầu?", default=True):
        with console.status("[bold green]Đang tạo audio...[/bold green]"):
            subprocess.run(cmd, cwd=str(PROJECT_ROOT))

def run_git_commit():
    console.print()
    console.print(Rule("[bold]💾 GIT COMMIT[/bold]", style="cyan"))

    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    if not result.stdout.strip():
        console.print("  [dim]Không có thay đổi nào[/dim]")
        return

    console.print(f"\n  [bold]Thay đổi:[/bold]\n{result.stdout}")

    if Confirm.ask("  Commit tất cả?", default=True):
        subprocess.run(["git", "add", "-A"], cwd=str(PROJECT_ROOT))
        msg = Prompt.ask("  Commit message", default="🔄 update: cập nhật bản dịch")
        subprocess.run(["git", "commit", "-m", msg], cwd=str(PROJECT_ROOT))
        console.print("  [green]✓ Đã commit[/green]")

        if Confirm.ask("  Push lên GitHub?", default=False):
            subprocess.run(["git", "push", "origin", "main"], cwd=str(PROJECT_ROOT))
            console.print("  [green]✓ Đã push[/green]")

# ─── Main ────────────────────────────────────────────────────────────────

def main():
    clear()
    show_banner()

    while True:
        show_main_menu()
        choice = Prompt.ask("\nChọn", default="0")

        if choice == "1":
            show_book_status()
        elif choice == "2":
            console.print("\n  [cyan]Đặt file PDF/EPUB vào input/ rồi gõ /dich[/cyan]")
        elif choice == "3":
            console.print("\n  [cyan]Đặt file PDF/EPUB vào input/ rồi gõ /dich[/cyan]")
        elif choice == "4":
            run_audiobook()
        elif choice == "5":
            console.print("\n  [cyan]Gõ /dich để chạy QA tự động[/cyan]")
        elif choice == "6":
            run_git_commit()
        elif choice == "7":
            show_detail_stats()
        elif choice == "0":
            console.print("\n  [dim]Tạm biệt! 👋[/dim]\n")
            break
        else:
            console.print("  [red]Lựa chọn không hợp lệ[/red]")

        console.print()

if __name__ == "__main__":
    main()
