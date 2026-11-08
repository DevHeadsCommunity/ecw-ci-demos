#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
: "${ZEPHYR_BASE:?Initialize west and set ZEPHYR_BASE to the pinned Zephyr checkout}"
export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
expected_zephyr=413b789deb391d3a37d06b463288a5fe765ee57e
if [ "$(git -C "$ZEPHYR_BASE" rev-parse HEAD)" != "$expected_zephyr" ]; then
  echo "Expected upstream Zephyr v4.2.0 ($expected_zephyr)" >&2
  exit 1
fi
cd "$ZEPHYR_BASE"
west build -p always -b fpb_ra6e2 "$repo_dir/app" -d "$repo_dir/build/zephyr"
cp "$repo_dir/build/zephyr/zephyr/zephyr.hex" "$repo_dir/build/firmware.hex"
if [ "$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["demo"])' "$repo_dir/demo.json")" = twister ]; then
  python scripts/twister -T "$repo_dir/app" -p fpb_ra6e2 --build-only --outdir "$repo_dir/build/twister" --inline-logs
fi
cd "$repo_dir"
python - <<'PROVENANCE'
import hashlib,json,os,subprocess
from pathlib import Path
image=Path('build/firmware.hex')
payload={'platform':'fpb_ra6e2','zephyr_commit':subprocess.check_output(['git','-C',os.environ['ZEPHYR_BASE'],'rev-parse','HEAD'],text=True).strip(),
         'demo_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'bytes':image.stat().st_size,
         'sdk_requested':'0.17.2'}
Path('build/provenance.json').write_text(json.dumps(payload,indent=2)+'\n')
PROVENANCE
