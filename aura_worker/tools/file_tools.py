"""File System & Document Processing Tools (Python)"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

ROOT_DOCS_DIR = Path(__file__).resolve().parent.parent / "environment" / "mock_files"


def list_files(directory: str = "") -> Dict[str, Any]:
    """List available files and documents in company storage directories."""
    try:
        clean_dir = directory.strip("/\\")
        target_dir = ROOT_DOCS_DIR / clean_dir if clean_dir else ROOT_DOCS_DIR

        if not target_dir.resolve().is_relative_to(ROOT_DOCS_DIR.resolve()):
            return {"success": False, "error": "Access denied: Path outside allowed storage"}

        if not target_dir.exists():
            return {"success": False, "error": f"Directory not found: '{directory}'"}

        entries: List[Dict[str, Any]] = []
        for item in target_dir.iterdir():
            rel_path = str(item.relative_to(ROOT_DOCS_DIR)).replace("\\", "/")
            if item.is_dir():
                entries.append({"name": item.name, "path": rel_path, "type": "directory"})
            else:
                stat = item.stat()
                mtime_iso = datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"
                entries.append({
                    "name": item.name,
                    "path": rel_path,
                    "type": "file",
                    "size_bytes": stat.st_size,
                    "modified_time": mtime_iso
                })

        entries.sort(key=lambda x: x.get("modified_time", ""), reverse=True)
        return {
            "success": True,
            "directory": directory or "/",
            "count": len(entries),
            "files": entries
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to list files: {str(e)}"}


def read_file(file_path: str) -> Dict[str, Any]:
    """Read the complete contents of a specific document or file by its relative path."""
    try:
        clean_path = file_path.strip("/\\")
        target_path = ROOT_DOCS_DIR / clean_path

        if not target_path.resolve().is_relative_to(ROOT_DOCS_DIR.resolve()):
            return {"success": False, "error": "Access denied: Path traversal not permitted"}

        if not target_path.exists():
            return {"success": False, "error": f"File not found: '{file_path}'"}

        content = target_path.read_text(encoding="utf-8")
        stat = target_path.stat()
        mtime_iso = datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"

        parsed_json = None
        if clean_path.endswith(".json"):
            try:
                parsed_json = json.loads(content)
            except Exception:
                pass

        return {
            "success": True,
            "file_path": clean_path,
            "size_bytes": stat.st_size,
            "last_modified": mtime_iso,
            "is_json": parsed_json is not None,
            "content": parsed_json if parsed_json is not None else content
        }
    except Exception as e:
        return {"success": False, "error": f"File read error for '{file_path}': {str(e)}"}


def search_documents(query: str) -> Dict[str, Any]:
    """Search across company files for specific keywords (e.g. 'Acme', 'INV-2024-889')."""
    try:
        matches = []
        lower_q = query.lower()

        for root, _, files in os.walk(ROOT_DOCS_DIR):
            for file_name in files:
                full_path = Path(root) / file_name
                rel_path = str(full_path.relative_to(ROOT_DOCS_DIR)).replace("\\", "/")

                filename_match = lower_q in file_name.lower()
                content_match = False
                snippet = ""

                try:
                    text = full_path.read_text(encoding="utf-8", errors="ignore")
                    idx = text.lower().find(lower_q)
                    if idx != -1:
                        content_match = True
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(query) + 40)
                        snippet = "..." + " ".join(text[start:end].split()) + "..."
                except Exception:
                    pass

                if filename_match or content_match:
                    matches.append({
                        "path": rel_path,
                        "filename": file_name,
                        "matched_in": "both" if filename_match and content_match else ("filename" if filename_match else "content"),
                        "snippet": snippet
                    })

        return {
            "success": True,
            "query": query,
            "match_count": len(matches),
            "matches": matches
        }
    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}
