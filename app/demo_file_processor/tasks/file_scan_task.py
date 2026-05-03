import pathlib
from typing import List, Dict, Any
from framework.core.task import AbstractTask


class FileScanTask(AbstractTask):
    """Scans a directory for text files and counts words/lines in each.

    Works well with WithTimeout() for large directories.
    """

    PATTERNS = ["*.py", "*.txt", "*.md", "*.json", "*.yaml", "*.yml"]

    def __init__(self, directory: str) -> None:
        self.directory = directory

    def run(self, ctx) -> Dict[str, Any]:
        root = pathlib.Path(self.directory)
        ctx.report_message(f"Scanning {root} …")

        all_files: List[pathlib.Path] = []
        for pat in self.PATTERNS:
            all_files.extend(root.rglob(pat))

        total = len(all_files)
        ctx.report_message(f"Found {total} file(s). Processing…")
        ctx.log(f"FileScanTask: {total} files in {root}")

        results: List[Dict] = []
        for i, fp in enumerate(all_files):
            if ctx.is_cancelled():
                ctx.report_message("Scan cancelled.")
                return {"results": results, "total": total, "cancelled": True}
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
                results.append({
                    "name": fp.name,
                    "rel_path": str(fp.relative_to(root)),
                    "lines": len(text.splitlines()),
                    "words": len(text.split()),
                    "size_kb": round(fp.stat().st_size / 1024, 1),
                })
            except Exception as exc:
                ctx.log(f"Skipped {fp.name}: {exc}")
                results.append({
                    "name": fp.name,
                    "rel_path": str(fp.relative_to(root)),
                    "lines": 0, "words": 0, "size_kb": 0,
                    "error": str(exc),
                })

            pct = int((i + 1) / max(total, 1) * 100)
            ctx.report_progress(pct)
            ctx.report_message(f"({i + 1}/{total}) {fp.name}")

        return {"results": results, "total": total, "cancelled": False}
