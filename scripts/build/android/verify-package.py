"""Check privacy-sensitive settings in a built Android APK."""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_aapt() -> str:
    command = shutil.which('aapt')
    if command:
        return command
    roots = (Path('build/android/.buildozer/android/platform/android-sdk/build-tools'),
             Path.home() / '.buildozer/android/platform/android-sdk/build-tools')
    for root in roots:
        for candidate in sorted(root.glob('*/aapt'), reverse=True):
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError('Android aapt was not found after the APK build')


def verify(apk: Path) -> None:
    aapt = find_aapt()
    badging = subprocess.check_output([aapt, 'dump', 'badging', str(apk)], text=True)
    permissions = set(re.findall(r"^uses-permission: name='([^']+)'", badging, re.MULTILINE))
    if permissions:
        raise RuntimeError(f'Unexpected Android permissions: {sorted(permissions)}')
    manifest = subprocess.check_output([aapt, 'dump', 'xmltree', str(apk), 'AndroidManifest.xml'], text=True)
    if not re.search(r'android:allowBackup\([^\n]+\)=\(type 0x12\)0x0(?:\s|$)', manifest):
        raise RuntimeError('Android application backups must be disabled')
    print(f'APK manifest verified: no application permissions; allowBackup=false ({apk})')


if __name__ == '__main__':
    verify(Path(sys.argv[1]).resolve())
