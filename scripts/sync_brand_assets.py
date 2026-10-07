"""Regenerate public wordmark/icon from the shared terminal lettering."""

import argparse
import hashlib
import re
from pathlib import Path

from openwfn.branding import icon_svg, wordmark_svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assets = {'openwfn-brand.svg': wordmark_svg(), 'openwfn-icon-v2.svg': icon_svg()}
    manifest_path = root / 'docs/assets/data/asset-provenance.yml'
    manifest = manifest_path.read_text(encoding='utf-8')
    stale = []
    for name, source in assets.items():
        path = root / 'docs/assets/images' / name
        digest = hashlib.sha256(source.encode()).hexdigest()
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != source:
                stale.append(name)
            if not re.search(r'^  ' + re.escape(name) + r':\n(?:(?!^  \S).)*?sha256: ' + digest,
                             manifest, re.S | re.M):
                stale.append(name + ' provenance')
        else:
            path.write_text(source, encoding='utf-8')
            manifest = re.sub(r'(^  ' + re.escape(name) + r':\n(?:(?!^  \S).)*?sha256: )[a-f0-9]+',
                              lambda match: match[1] + digest, manifest, flags=re.S | re.M)
    if not args.check:
        manifest_path.write_text(manifest, encoding='utf-8')
    if stale:
        parser.exit(1, 'Stale brand assets: ' + ', '.join(stale) + '\n')


if __name__ == '__main__':
    main()
