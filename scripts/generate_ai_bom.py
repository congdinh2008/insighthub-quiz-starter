#!/usr/bin/env python3
"""Generate an AI Bill of Materials (Kit K11, Requirements LR-24).

Reads configuration defaults and the learner's .env variable *names/values for
non-secret keys only* (provider and model choices; keys matching KEY|TOKEN|SECRET|
PASSWORD are never read), prompt versions declared in code, and evaluation corpus
hashes. Writes docs/ai/ai-bom.json. Review and complete the `manual` section.
"""
import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|COOKIE|DATABASE|SMTP", re.I)
USERINFO = re.compile(r"(?<=://)[^/@\s]+@")
MODEL_SETTINGS = re.compile(r"(provider|model|embedding_dim|embedding_revision|base_url|rag_mode|rag_profile)$", re.I)


def config_defaults(path=ROOT / "api/app/core/config.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if SECRET.search(name) or not MODEL_SETTINGS.search(name):
                continue
            value = node.value
            if isinstance(value, ast.Call):
                value = next((k.value for k in value.keywords if k.arg == "default"), None)
            if isinstance(value, ast.Constant):
                values[name] = USERINFO.sub("", value.value) if isinstance(value.value, str) else value.value
    return values


def env_overrides(path):
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if SECRET.search(name) or not MODEL_SETTINGS.search(name):
            continue
        values[name.lower()] = USERINFO.sub("", value.strip().strip('"').strip("'"))
    return values


def prompt_versions():
    found = []
    for path in sorted((ROOT / "api" / "app").rglob("*.py")):
        for match in re.finditer(r"^(\w*PROMPT_VERSION\w*)\s*=\s*['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"), re.M):
            found.append({"name": match.group(1), "version": match.group(2), "file": path.relative_to(ROOT).as_posix()})
    return found


def corpus_hashes():
    folder = ROOT / "evaluation" / "corpus"
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def build(env_file):
    settings = config_defaults()
    settings.update(env_overrides(env_file))
    suites = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "evaluation" / "harness" / "suites").glob("*.json"))
    return {
        "bom_format": "InsightHub AI-BOM",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"config_defaults": "api/app/core/config.py", "env_file": env_file.name if env_file.is_file() else None,
                   "secrets_read": False},
        "models_and_providers": settings,
        "prompts": prompt_versions(),
        "evaluation": {"corpus_sha256": corpus_hashes(), "suites": suites},
        "development_tools": {"primary": "Claude (Claude.ai, Claude Code)", "optional": "ChatGPT/Codex"},
        "manual": {
            "output_schemas": "TODO: schema_version của Summary, Quiz, Chat và vị trí định nghĩa",
            "data_flows_abroad": "TODO: provider nào nhận dữ liệu gì (đối chiếu threat model)",
            "known_limitations": "TODO",
            "reviewed_by": "",
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "ai" / "ai-bom.json"))
    args = parser.parse_args(argv)
    bom = build(Path(args.env_file))
    output = Path(args.output)
    manual = None
    if output.is_file():
        manual = json.loads(output.read_text(encoding="utf-8")).get("manual")
    if manual:
        bom["manual"] = manual
    output.write_text(json.dumps(bom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}; {len(bom['prompts'])} prompt versions; secrets_read=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
