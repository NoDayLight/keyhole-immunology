"""Safe filesystem resolution for package-owned, wheel-installed resources."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

_RESOURCE_ROOT = Path(__file__).resolve().parent / "resources"


def _parts(relative: str) -> tuple[str, ...]:
    value = PurePosixPath(relative)
    if (
        not relative
        or value.is_absolute()
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise ValueError(f"unsafe resource path: {relative!r}")
    return value.parts


def safe_child(root: Path, relative: str) -> Path:
    """Resolve a non-traversing relative path beneath *root*."""

    resolved_root = root.expanduser().resolve()
    candidate = resolved_root.joinpath(*_parts(relative)).resolve()
    if resolved_root not in candidate.parents:
        raise ValueError(f"resource path escapes its root: {relative!r}")
    return candidate


def packaged_file(relative: str) -> Path:
    """Return one existing regular file from the installed resource tree."""

    path = safe_child(_RESOURCE_ROOT, relative)
    if not path.is_file():
        raise FileNotFoundError(f"required packaged resource is missing: {relative}")
    return path


def packaged_directory(relative: str) -> Path:
    """Return one existing directory from the installed resource tree."""

    path = safe_child(_RESOURCE_ROOT, relative)
    if not path.is_dir():
        raise FileNotFoundError(f"required packaged resource directory is missing: {relative}")
    return path
