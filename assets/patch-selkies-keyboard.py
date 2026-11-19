import hashlib
from pathlib import Path
import sys


ORIGINAL_SHA256 = "6d40a13fe9ca9751047c6b138bd0d89fb925003abfbce79ddfcab7ab7d7b6192"
PATCHED_SHA256 = "f5b46aeb7fb1872288f4fa1a8771b80e0861407d3e841d96b7820fba0458b095"
ORIGINAL = b"case F.XK_Super_L:e.macCmdAsCtrl&&(i=F.XK_Alt_L);break;case F.XK_Super_R:i=F.XK_Super_L;break;"
REPLACEMENT = b"case F.XK_Super_L:e.macCmdAsCtrl&&(i=F.XK_Control_L);break;case F.XK_Super_R:i=e.macCmdAsCtrl?F.XK_Control_L:F.XK_Super_L;break;"


def patch(root):
    path = root / "selkies-dashboard" / "selkies-core.js"
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256 or source.count(ORIGINAL) != 1:
        raise ValueError("Selkies client changed. Review the Command-key correction before rebuilding.")
    result = source.replace(ORIGINAL, REPLACEMENT)
    if hashlib.sha256(result).hexdigest() != PATCHED_SHA256:
        raise ValueError("The corrected Selkies client does not match the verified input fix.")
    path.write_bytes(result)


if __name__ == "__main__":
    patch(Path(sys.argv[1]) if len(sys.argv) == 2 else Path("/usr/share/selkies"))
