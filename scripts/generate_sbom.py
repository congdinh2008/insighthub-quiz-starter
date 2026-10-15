"""Generate a deterministic CycloneDX inventory from locked project inputs."""

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "release" / "SBOM.cdx.json"


def component(name, version, kind, *, scope="required"):
    return {
        "type": kind,
        "name": name,
        "version": version,
        "scope": scope,
        "bom-ref": f"{kind}:{name}@{version}",
    }


def main():
    components = []
    seen = set()
    for line in (ROOT / "api" / "requirements.txt").read_text().splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ ;\\]+)", line)
        if match:
            key = ("library", match.group(1).casefold(), match.group(2))
            if key not in seen:
                seen.add(key)
                components.append(component(match.group(1), match.group(2), "library"))
    lock = json.loads((ROOT / "web" / "package-lock.json").read_text())
    for path, metadata in lock["packages"].items():
        if not path.startswith("node_modules/") or "version" not in metadata:
            continue
        name = path.removeprefix("node_modules/")
        scope = "optional" if metadata.get("optional") else "required"
        key = ("library", name.casefold(), metadata["version"])
        if key not in seen:
            seen.add(key)
            components.append(component(name, metadata["version"], "library", scope=scope))
    for compose_file in (ROOT / "docker-compose.yml", ROOT / "infra" / "reranker" / "docker-compose.yml"):
        for raw in compose_file.read_text().splitlines():
            match = re.match(r"\s*image:\s*([^\s#]+)", raw)
            if not match:
                continue
            image = match.group(1)
            name, version = image, "configured-at-runtime"
            if "@sha256:" in image:
                name, version = image.split("@sha256:", 1)
                version = "sha256:" + version
            elif ":" in image and not image.startswith("${"):
                name, version = image.rsplit(":", 1)
            key = ("container", name.casefold(), version)
            if key not in seen:
                seen.add(key)
                components.append(component(name, version, "container"))
    components.sort(key=lambda item: item["bom-ref"])
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "mochi-ai/insighthub-starter/1.0.0")),
        "version": 1,
        "metadata": {
            "timestamp": "2026-09-19T00:00:00Z",
            "component": {"type": "application", "name": "InsightHub Starter", "version": json.loads((ROOT / "starter.manifest.json").read_text())["version"]},
        },
        "components": components,
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
