import sys
from pathlib import Path


def main():
    root = Path('/a0/usr/plugins/a0_hyperagents/storage')
    for sub in ['nodes/gen_initial', 'sandboxes']:
        (root / sub).mkdir(parents=True, exist_ok=True)
    print(f'HyperAgents storage ready: {root}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
