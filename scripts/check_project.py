"""Check standalone release consistency without Docker or external credentials."""
import hashlib
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def local_file(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), f'Missing/nonportable file: {relative}'
    return path


def anchors(text):
    explicit = set(re.findall(r'<a id="([^"]+)"', text))
    headings = {re.sub(r'[^\w\- ]', '', x.lower()).replace(' ', '-')
                for x in re.findall(r'^#+ (.*)', text, re.M)}
    return explicit | headings


def check_reference(reference, srs):
    with zipfile.ZipFile(reference) as archive:
        assert archive.testzip() is None, 'Damaged API/schema reference'
        manifest = json.loads(archive.read('API_Schema_Reference/Manifest_Reference.json'))
        assert manifest['srs']['path'] == '../' + srs.name, 'Reference SRS path drift'
        assert manifest['srs']['sha256'] == hashlib.sha256(srs.read_bytes()).hexdigest(), 'Reference SRS hash drift'
        expected = {'API_Schema_Reference/Manifest_Reference.json'}
        for item in manifest['contract_files']:
            name = 'API_Schema_Reference/' + item['path']
            assert '..' not in Path(item['path']).parts and not Path(item['path']).is_absolute(), 'Unsafe reference path'
            assert hashlib.sha256(archive.read(name)).hexdigest() == item['sha256'], f'Reference hash drift: {name}'
            expected.add(name)
        assert set(archive.namelist()) == expected, 'Reference file list drift'


def main():
    manifest = json.loads((ROOT / 'starter.manifest.json').read_text())
    version = manifest['version']
    package = json.loads((ROOT / 'web/package.json').read_text())
    lock = json.loads((ROOT / 'web/package-lock.json').read_text())
    sbom = json.loads((ROOT / 'docs/release/SBOM.cdx.json').read_text())
    assert package['version'] == lock['version'] == lock['packages']['']['version'] == sbom['metadata']['component']['version'] == version, 'Version drift'
    assert (ROOT / 'api/app/main.py').read_text().count('"' + version + '"') == 2, 'API version drift'
    assert version in (ROOT / 'README.md').read_text(), 'README version drift'
    srs = local_file(manifest['requirements_baseline'])
    learner = local_file(manifest['learner_requirements'])
    reference = local_file(manifest['api_schema_reference'])
    parent = ROOT.parent / manifest['requirements_source']
    if parent.exists():
        expected = re.sub(r'\.\./02_Solution/Contract_R1_v[0-9.]+_\d{8}/README\.md', reference.name, parent.read_text())
        expected = re.sub(r'Manifest_ThamChieu_SRS_v[0-9.]+_\d{8}\.json', reference.name, expected).replace('[manifest tham chiếu]', '[manifest tham chiếu trong gói API/Schema]')
        assert srs.read_text() == expected, 'SRS snapshot differs from authoring source'
    check_reference(reference, srs)
    mapping = learner.read_text()
    requirements = set(re.findall(r'^#{4,5} (IH-[A-Z]+-\d{3}):', srs.read_text(), re.M))
    acceptance = set(re.findall(r'IH-[A-Z]+-\d{3}-AC\d{2}', srs.read_text()))
    mapped = set(re.findall(r'\| `?(IH-[A-Z]+-\d{3})`? \|', mapping))
    assert requirements == mapped and len(requirements) == 73, 'Incomplete requirement mapping'
    assert acceptance <= set(re.findall(r'IH-[A-Z]+-\d{3}-AC\d{2}', mapping)) and len(acceptance) == 165, 'Incomplete AC mapping'
    rows = re.findall(r'^\| (IH-[A-Z]+-\d{3}) \| (IH-[A-Z]+-\d{3}-AC\d{2}) \| (A|D[1-9]|N) \|', mapping, re.M)
    assert len(rows) == 165 and {row[1] for row in rows} == acceptance, 'Incomplete AC table'
    assert {scope: sum(row[2] == scope for row in rows) for scope in ['A', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'N']} == {'A': 134, 'D1': 9, 'D2': 3, 'D3': 2, 'D4': 1, 'D5': 1, 'D6': 1, 'D7': 0, 'D8': 1, 'D9': 1, 'N': 12}, 'Assignment scope drift'
    assert re.findall(r'<a id="lr-(\d+)">', mapping) == [f'{i:02}' for i in range(1, 30)], 'Learning task drift'
    broken = []
    markdown = list(ROOT.glob('*.md'))
    for directory in ['docs', 'evaluation', 'sample-docs', 'infra', 'api/migrations', 'specs', 'trace', '.github']:
        markdown.extend((ROOT / directory).rglob('*.md'))
    for path in markdown:
        if 'archive' in path.parts:
            continue
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            target = target.strip('<>')
            if urlsplit(target).scheme:
                continue
            relative, _, anchor = unquote(target).partition('#')
            resolved = (path.parent / relative).resolve() if relative else path
            if Path(relative).is_absolute() or not resolved.is_relative_to(ROOT) or not resolved.exists():
                broken.append(f'{path.relative_to(ROOT)}: {target}')
            elif anchor and resolved.suffix == '.md' and anchor not in anchors(resolved.read_text()):
                broken.append(f'{path.relative_to(ROOT)}: {target} (anchor)')
    assert not broken, 'Nonportable/broken links: ' + '; '.join(broken)
    print(f'PASS: {version}; 73 requirements / 165 AC; portable links; SRS sha256={hashlib.sha256(srs.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
