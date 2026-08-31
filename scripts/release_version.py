from __future__ import annotations

import os
import re
from pathlib import Path


VERSION_PATTERN = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def resolve_version(pyproject_path: Path, ref_type: str, ref_name: str) -> str:
    pyproject = pyproject_path.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(pyproject)
    if match is None:
        raise ValueError(f"{pyproject_path} does not expose a package version")

    version = match.group(1)
    if ref_type == "tag" and ref_name != f"v{version}":
        raise ValueError(f"tag {ref_name} does not match v{version}")
    return version


def main() -> None:
    try:
        version = resolve_version(
            Path("pyproject.toml"),
            os.environ.get("GITHUB_REF_TYPE", ""),
            os.environ.get("GITHUB_REF_NAME", ""),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write(f"version={version}\n")
    else:
        print(version)


if __name__ == "__main__":
    main()
