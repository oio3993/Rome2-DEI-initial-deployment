"""Strict reader/writer for the uncompressed PFH4 mod packs used by this release."""
import struct
from project import require


def member_ok(name):
    require(isinstance(name, str) and name and '/' not in name and ':' not in name and
            all(part and part not in ('.', '..') for part in name.split('\\')),
            'Unsafe or invalid pack member name.')


def read_pack(raw):
    require(len(raw) >= 28, 'Truncated PFH4 header.')
    magic, kind, refs, refsize, count, indexsize, reserved = struct.unpack_from('<4s6I', raw)
    require((magic, kind, refs, refsize, reserved) == (b'PFH4', 3, 0, 0, 0), 'Unsupported PFH4 header.')
    end_index = 28 + indexsize
    require(end_index <= len(raw) and count <= indexsize // 6, 'Invalid PFH4 index bounds.')
    pos, items, names = 28, [], set()
    for _ in range(count):
        require(pos + 4 <= end_index, 'Truncated pack index size.')
        size = struct.unpack_from('<I', raw, pos)[0]
        pos += 4
        end = raw.find(b'\0', pos, end_index)
        require(end >= pos, 'Unterminated pack member name.')
        name = raw[pos:end].decode('utf-8')
        member_ok(name)
        require(name.lower() not in names, 'Duplicate pack member.')
        names.add(name.lower())
        items.append((name, size))
        pos = end + 1
    require(pos == end_index, 'Pack index length differs.')
    entries = {}
    for name, size in items:
        require(size <= len(raw) - pos, 'Truncated pack member data.')
        entries[name] = raw[pos:pos+size]
        pos += size
    require(pos == len(raw), 'Trailing pack data.')
    return entries


def make_pack(entries):
    names = set()
    for name, data in entries.items():
        member_ok(name)
        require(name.lower() not in names and isinstance(data, bytes), 'Invalid pack entry.')
        names.add(name.lower())
    index = b''.join(struct.pack('<I', len(data)) + name.encode('utf-8') + b'\0'
                     for name, data in entries.items())
    raw = struct.pack('<4s6I', b'PFH4', 3, 0, 0, len(entries), len(index), 0) + index + b''.join(entries.values())
    require(read_pack(raw) == entries, 'PFH4 write/readback mismatch.')
    return raw
