import struct
import re
from pathlib import Path


def generate_mo(po_path, mo_path):
    with open(po_path, "r", encoding="utf-8") as f:
        content = f.read()

    pairs = re.findall(r'msgid "(.*?)"\s+msgstr "(.*?)"', content, re.DOTALL)
    messages = {k: v for k, v in pairs}

    keys = sorted(messages.keys())
    offsets = []
    ids = b""
    strs = b""
    for k in keys:
        k_enc = k.encode("utf-8") + b"\x00"
        v_enc = messages[k].encode("utf-8") + b"\x00"
        offsets.append((len(ids), len(k_enc) - 1, len(strs), len(v_enc) - 1))
        ids += k_enc
        strs += v_enc

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)

    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets.append((l1, o1 + keystart))
        voffsets.append((l2, o2 + valuestart))

    header = struct.pack(
        "Iiiiiii", 0x950412DE, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0
    )
    tables = b"".join(
        struct.pack("ii", length, o) for length, o in koffsets
    ) + b"".join(struct.pack("ii", length, o) for length, o in voffsets)

    with open(mo_path, "wb") as f:
        f.write(header + tables + ids + strs)
    print(f"Successfully compiled {mo_path}")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    po_file = base / "locale" / "uk" / "LC_MESSAGES" / "django.po"
    mo_file = base / "locale" / "uk" / "LC_MESSAGES" / "django.mo"
    generate_mo(po_file, mo_file)
