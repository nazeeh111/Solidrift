"""Build the free recorded-evidence site. Never runs or simulates Blender."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit('Use a new output directory.')
    report = json.loads((args.case/'report.json').read_text())
    if report.get('status') != 'repaired':
        raise SystemExit('The public demo requires an accepted native repair.')
    # A public report needs source identity, not host-specific parent paths.
    for source in report.get('sources', []):
        source.pop('path', None)
        source.pop('absolute_path', None)
    report['demo'] = True
    args.out.mkdir(parents=True)
    for name in ('index.html','style.css','app.js'):
        shutil.copyfile(ROOT/'solidrift/web'/name, args.out/name)
    shutil.copyfile(ROOT/'site/tour.html', args.out/'tour.html')
    shutil.copyfile(ROOT/'site/favicon.svg', args.out/'favicon.svg')
    media = args.out/'media'; media.mkdir()
    for name in ('solidrift-tour.mp4', 'solidrift-tour.jpg'):
        shutil.copyfile(ROOT/'docs/media'/name, media/name)
    demo = args.out/'demo';demo.mkdir()
    data = (json.dumps(report, indent=2, allow_nan=False)+'\n').encode()
    (demo/'report.json').write_bytes(data)
    with zipfile.ZipFile(demo/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('report.json', data)
        for subdir in ('meshes','originals'):
            for path in sorted((args.case/subdir).glob('*')):
                if path.is_file():archive.write(path, str(path.relative_to(args.case)))
        for name in ('patch.json',):
            if (args.case/name).is_file():archive.write(args.case/name,name)
        for name in ('LICENSE','NOTICE'):
            archive.write(ROOT/name,name)
        # Inline viewer carries exactly the sanitized public report and assets.
        from solidrift.cli import view
        import types
        viewer=demo/'report.html'
        view(types.SimpleNamespace(report=demo/'report.json',out=viewer))
        archive.write(viewer,'report.html')
        manifest={}
        for info in archive.infolist():
            manifest[info.filename]={'bytes':info.file_size,'sha256':hashlib.sha256(archive.read(info.filename)).hexdigest()}
        archive.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    (args.out/'.nojekyll').touch()
    print(json.dumps({'out':str(args.out),'report_sha256':hashlib.sha256(data).hexdigest(),
                      'bundle_sha256':hashlib.sha256((demo/'evidence.zip').read_bytes()).hexdigest()}))

if __name__ == '__main__':main()
