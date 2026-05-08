"""Optional runtime hooks for the HyperAgents plugin."""
from pathlib import Path


def install():
    root = Path('/a0/usr/plugins/a0_hyperagents/storage')
    (root / 'nodes' / 'gen_initial').mkdir(parents=True, exist_ok=True)
    return {'ok': True, 'storage_root': str(root)}
