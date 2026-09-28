"""Notebook presentation and reproducible local evidence files."""
from hashlib import sha256
from html import escape
from importlib.metadata import version
import json
from pathlib import Path
import sys


def table(rows, columns=None):
    """Escape all text, including imported conversations and generated model content."""
    if not rows:
        return "<p>No rows.</p>"
    columns = columns or list(rows[0])
    header = "".join(f"<th style='text-align:left;padding:6px'>{escape(str(c))}</th>" for c in columns)
    body = []
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            text = "—" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)
            values.append(f"<td style='padding:6px;vertical-align:top'>{escape(text)}</td>")
        body.append("<tr>" + "".join(values) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def metric_bars(rows):
    blocks = []
    for row in rows:
        value = row["hit_at_1"]
        blocks.append(
            f"<div style='margin:12px 0'>{escape(row['arm'])}: <b>{value:.0%}</b>"
            f"<div style='background:#e5e7eb;height:14px;width:360px'>"
            f"<div style='background:#2563eb;height:14px;width:{100 * value:.2f}%'></div></div></div>"
        )
    return "<h4>Held-out correction-family hit@1</h4>" + "".join(blocks)


def save_report(directory: Path, report, records):
    directory.mkdir(parents=True, exist_ok=True)
    corpus = "\n".join(r.model_dump_json() for r in records) + "\n"
    (directory / "captured.jsonl").write_text(corpus)
    manifest = {
        "python": sys.version,
        "versions": {name: version(name) for name in ("numpy", "deepagents", "langchain-openai", "openai")},
        "corpus_sha256": sha256(corpus.encode()).hexdigest(),
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
    }
    (directory / "evaluation.json").write_text(json.dumps(report, indent=2))
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return directory
