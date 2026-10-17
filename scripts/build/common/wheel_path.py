"""Print the sole wheel from the current build and reject stale or ambiguous output."""

from pathlib import Path

from project_version import project_version


def wheel_path(root: Path) -> Path:
    wheels = sorted((root / 'dist' / 'wheels').glob('cooking_planner-*.whl'))
    version = project_version(root)
    expected = f'cooking_planner-{version}-'
    if len(wheels) != 1 or not wheels[0].name.startswith(expected):
        raise ValueError(f'Expected one Cooking Planner {version} wheel, found: '
                         f'{[wheel.name for wheel in wheels]}')
    return wheels[0]


if __name__ == '__main__':
    print(wheel_path(Path(__file__).resolve().parents[3]))
