"""Offline 052 measurement with input-fingerprinted, resumable file-IPC shards."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from . import checkpoints, measurement_v2, measurement_v3, route_v2
from scripts.playtest import save_telemetry

ROOT = checkpoints.ROOT


def main() -> int:
    folder, args = Path(sys.argv[1]).resolve(), sys.argv[2:]

    def value(flag, default):
        return args[args.index(flag)+1] if flag in args else default

    scenario = Path(value('--scenario', checkpoints.DEFAULT_SCENARIO))
    save = Path(value('--save', save_telemetry.DEFAULT_SAVE))
    signature = measurement_v2.input_fingerprints(scenario, save)
    signature['strategy_052b'] = hashlib.sha256((ROOT/'eval/balance/strategy_052b.json').read_bytes()).hexdigest()
    if '--passive-table' in args:
        signature['frozen_passive_table'] = hashlib.sha256(Path(value('--passive-table', None)).read_bytes()).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder/'input-fingerprints.json'
    if manifest.exists():
        if json.loads(manifest.read_text(encoding='utf-8')) != signature:
            raise ValueError('Cached input fingerprints differ; use a new candidate cache')
    else:
        manifest.write_text(json.dumps(signature, indent=2)+'\n', encoding='utf-8')

    def cached(jobs, workers):
        def execute(job):
            encoded = json.dumps([str(v) if isinstance(v, Path) else v for v in job], sort_keys=True)
            key = hashlib.sha256(encoded.encode()).hexdigest()
            options = job[5] if len(job) > 5 and isinstance(job[5], dict) else {}
            for name in ('checkpoint_path', 'probe_inputs_path'):
                if options.get(name):
                    key = hashlib.sha256((key+hashlib.sha256(Path(options[name]).read_bytes()).hexdigest()).encode()).hexdigest()
            source, output = folder/(key+'-in.json'), folder/(key+'-out.json')
            if output.exists():
                return json.loads(output.read_text(encoding='utf-8')), True
            source.write_text(encoded, encoding='utf-8')
            pending = output.with_suffix('.partial')
            subprocess.run([sys.executable, '-X', 'utf8', '-m', 'scripts.balance.route_v2',
                            '--worker-job', str(source), '--worker-output', str(pending)],
                           cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            pending.replace(output)
            return json.loads(output.read_text(encoding='utf-8')), False
        with ThreadPoolExecutor(max_workers=workers) as pool:
            batches = list(pool.map(execute, jobs))
        print(f'cache: {sum(hit for _, hit in batches)}/{len(jobs)} shards reused', flush=True)
        return [row for records, _ in batches for row in records]

    with patch.object(route_v2, 'run_jobs', cached):
        return measurement_v3.main(args)


if __name__ == '__main__':
    raise SystemExit(main())
