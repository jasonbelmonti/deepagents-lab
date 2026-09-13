"""Sequential matched live runs, with replayable manifests and incremental saves."""
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from deepagents_lab.benchmarks import incident_metrics

from .config import ARMS, Config, arm_order
from .fixture import make_graph
from .oracle import expected_answer
from .prompts import prompt_for
from .report import render_report, summarize
from .trial import model_settings, run_trial


def manifest(config, *, scripted=False):
    sources = [*Path(__file__).parent.glob("*.py"), Path(incident_metrics.__file__)]
    notebook = Path(__file__).parents[4] / "notebooks/experiments/graph-ptc-value.py"
    if notebook.exists():
        sources.append(notebook)
    blocks = []
    for case in config.cases:
        for seed in config.seeds:
            data = make_graph(seed, case.width)
            payload = asdict(data)
            blocks.append(dict(case=case.name, seed=seed, fixture=payload,
                               fixture_sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                               expected=expected_answer(data, case),
                               prompts={arm: prompt_for(case, data.root, arm, config) for arm in ARMS}))
    return dict(schema_version=2, created_at=datetime.now(timezone.utc).isoformat(), config=asdict(config),
                comparisons={"primary": ["ordinary", "ptc"], "secondary": ["compute", "ptc"]},
                evidence_kind="scripted" if scripted else "live", model_settings=model_settings(config),
                versions={name: version(name) for name in ("deepagents", "langchain-core", "langchain-openai", "langchain-quickjs", "quickjs-rs")},
                source_sha256={source.name: hashlib.sha256(source.read_bytes()).hexdigest() for source in sources},
                blocks=blocks, planned_runs=config.planned_runs, trials=[])


async def run_benchmark(config: Config, output_dir: Path, *, model_factory=None, progress=print):
    """A model_factory is for offline harness verification, never live evidence."""
    report = manifest(config, scripted=model_factory is not None)
    destination = output_dir / str(uuid4())
    destination.mkdir(parents=True, exist_ok=False)
    report["report_path"] = str((destination / "report.json").resolve())

    def save():
        report["summary"] = summarize(report["trials"])
        temporary = destination / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(destination / "report.json")
        (destination / "report.md").write_text(render_report(report))

    save()
    for case_index, case in enumerate(config.cases):
        for seed_index, seed in enumerate(config.seeds):
            # Position rotates within each scenario even with a small seed set.
            for position, arm in enumerate(arm_order(seed_index + 2 * case_index), 1):
                report["pending_trial"] = dict(case=case.name, seed=seed, arm=arm, position=position)
                save()
                progress(f"{case.name}, seed {seed}, {arm} ({len(report['trials']) + 1}/{config.planned_runs})")
                model = model_factory(config, case, seed, arm) if model_factory else None
                if model_factory is not None and model is None:
                    raise ValueError("Offline model_factory must return a model; refusing a provider fallback.")
                row = await run_trial(config, case, seed, arm, model=model)
                row["position"] = position
                report["trials"].append(row)
                report.pop("pending_trial")
                last_two = report["trials"][-2:]
                if row.get("interrupted"):
                    report["stop_reason"] = "Cancelled; observed accounting retained."
                elif len(last_two) == 2 and all(r.get("error_status") in (400, 401, 403, 404, 429) for r in last_two):
                    report["stop_reason"] = "Repeated provider request/access failures; check configuration before rerunning."
                save()
                if report.get("stop_reason"):
                    return report
    return report
