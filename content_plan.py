"""Prepare a fictional document inventory and a checked local staging copy."""

from pathlib import Path, PurePosixPath
from datetime import date
import argparse
import hashlib
import json
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
CATEGORIES = {"People Support", "Systems", "Guidance"}
DOCUMENT_TYPES = {"Work instruction", "Reference", "FAQ"}


def safe_path(root, relative):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Use a non-empty relative path with forward slashes")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(part in ("..", ".") for part in parts.parts):
        raise ValueError("Path must stay inside its root")
    target = (root / relative).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError("Path escapes its root")
    return target


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_plan(source_root, records, as_of):
    """Inventory files and hold items requiring an owner, review or duplicate decision."""
    cutoff = date.fromisoformat(as_of)
    entries = []
    identifiers = set()
    targets = set()
    for record in records:
        identifier = record["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("Document IDs must be non-empty and unique")
        identifiers.add(identifier)
        if record["category"] not in CATEGORIES or record["document_type"] not in DOCUMENT_TYPES:
            raise ValueError("Unknown taxonomy value")
        source = safe_path(source_root, record["source"])
        if not source.is_file():
            raise ValueError("Source document is missing")
        target = record["target"]
        safe_path(source_root, target)
        if target.casefold() in targets:
            raise ValueError("Target paths must be unique, including case")
        targets.add(target.casefold())
        due = date.fromisoformat(record["review_due"])
        owner = record.get("owner", "").strip()
        flags = []
        if not owner:
            flags.append("MISSING_OWNER")
        if due < cutoff:
            flags.append("REVIEW_OVERDUE")
        entries.append({
            "id": identifier, "title": record["title"], "source": record["source"],
            "target": target, "category": record["category"],
            "document_type": record["document_type"], "owner": owner,
            "review_due": due.isoformat(), "sha256": digest(source),
            "bytes": source.stat().st_size, "flags": flags,
        })
    hashes = {}
    for entry in entries:
        hashes.setdefault(entry["sha256"], []).append(entry["id"])
    for entry in entries:
        if len(hashes[entry["sha256"]]) > 1:
            entry["flags"].append("DUPLICATE_CONTENT")
        entry["ready_for_staging"] = not entry["flags"]
    return {
        "synthetic": True, "as_of": cutoff.isoformat(), "cloud_calls": 0,
        "documents": entries, "total": len(entries),
        "ready": sum(entry["ready_for_staging"] for entry in entries),
        "held": sum(not entry["ready_for_staging"] for entry in entries),
    }


def stage_plan(source_root, plan, destination):
    """Publish eligible files to a new local directory after all hashes pass."""
    source_root = Path(source_root).resolve()
    destination = Path(destination).resolve()
    if destination.is_relative_to(source_root) or source_root.is_relative_to(destination):
        raise ValueError("Source and staging directories must be separate")
    ready = [entry for entry in plan["documents"] if entry["ready_for_staging"]]
    for entry in ready:
        source = safe_path(source_root, entry["source"])
        if not source.is_file() or digest(source) != entry["sha256"]:
            raise ValueError("Source changed after the inventory was prepared")
        safe_path(destination, entry["target"])
    expected = {entry["target"]: entry["sha256"] for entry in ready}
    if destination.exists():
        actual = {path.relative_to(destination).as_posix(): digest(path)
                  for path in destination.rglob("*") if path.is_file()}
        if actual != expected:
            raise ValueError("Existing staging directory differs; choose a new directory")
        return {"staged": len(ready), "held": plan["held"], "unchanged": True}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="content-stage-", dir=destination.parent))
    try:
        for entry in ready:
            target = safe_path(temporary, entry["target"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_path(source_root, entry["source"]), target)
            if digest(target) != entry["sha256"]:
                raise ValueError("Staged file did not pass its hash check")
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {"staged": len(ready), "held": plan["held"], "unchanged": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default="2026-11-16")
    parser.add_argument("--stage", type=Path, help="Optional local staging directory")
    options = parser.parse_args()
    source = ROOT / "examples/content"
    records = json.loads((ROOT / "examples/catalogue.json").read_text(encoding="utf-8"))
    plan = prepare_plan(source, records, options.as_of)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "content-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    summary = {key: plan[key] for key in ("synthetic", "as_of", "total", "ready", "held", "cloud_calls")}
    if options.stage:
        summary["staging"] = stage_plan(source, plan, options.stage)
    (reports / "content-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
