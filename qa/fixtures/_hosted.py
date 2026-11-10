"""
The images kitchen_sink hosts, committed so its hosted branch loads in a real inbox (v0.9.0).

They are served from this public repository's ``main`` branch, so a mail client fetches
them as it would any hosted image; ``cdn.example.com`` elsewhere still stands for an
image that never loads. The bytes come from constants, and a test holds the committed
files to them::

    python -m qa.fixtures._hosted        # rewrite qa/fixtures/hosted/ from the constants
"""

from __future__ import annotations

from pathlib import Path

from ._png import gradient_png, matrix_png

#: Where the files are served from: the repository's main branch, as raw files.
BASE_URL = "https://raw.githubusercontent.com/RorySullivan1/inkfold/main/qa/fixtures/hosted/"

#: The folder they are committed in.
FOLDER = Path(__file__).resolve().parent / "hosted"

#: An H in a five-by-five grid, for the footer's mark.
_MARK = ("10001", "10001", "11111", "10001", "10001")

#: Each file's name and bytes. The band blends kitchen_sink's own masthead colours, so the
#: image is visible against the fallback fill; the logo is twice its 128px display width.
IMAGES: dict[str, bytes] = {
    "header-bg.png": gradient_png(680, 220, (58, 43, 63), (124, 84, 96)),
    "hermes-logo.png": gradient_png(256, 64, (253, 246, 227), (196, 138, 90)),
    "hermes-mark.png": matrix_png(
        _MARK, scale=16, border=0, dark=(92, 87, 78), light=(242, 241, 238)
    ),
}


def url(name: str) -> str:
    """The URL a hosted fixture image is fetched from."""
    if name not in IMAGES:
        raise KeyError(f"no hosted fixture image {name!r}; there are {sorted(IMAGES)}")
    return BASE_URL + name


def write() -> list[Path]:
    """Write every image into :data:`FOLDER`."""
    FOLDER.mkdir(exist_ok=True)
    paths = []
    for name, data in IMAGES.items():
        path = FOLDER / name
        path.write_bytes(data)
        paths.append(path)
    return paths


if __name__ == "__main__":
    for written in write():
        print(written)
