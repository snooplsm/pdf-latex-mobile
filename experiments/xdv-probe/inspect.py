#!/usr/bin/env python3
"""Inventory XDV operations; fail on unsupported opcodes, never render them silently."""
import collections
import json
from pathlib import Path
import sys


def inspect(path):
    data = Path(path).read_bytes()
    i = 0
    counts = collections.Counter()
    fonts, specials = set(), set()
    def take(n):
        nonlocal i
        if i + n > len(data):
            raise ValueError(f'truncated XDV at {i}')
        out = data[i:i+n]
        i += n
        return out
    def uint(n):
        return int.from_bytes(take(n), 'big')
    while i < len(data):
        op = uint(1)
        counts[op] += 1
        if op <= 127 or op in (138, 140, 141, 142, 147, 152, 161, 166) or 171 <= op <= 234:
            continue
        if 128 <= op <= 131: take(op - 127)
        elif op in (132, 137): take(8)
        elif 133 <= op <= 136: take(op - 132)
        elif op == 139: take(44)
        elif 143 <= op <= 146: take(op - 142)
        elif 148 <= op <= 151: take(op - 147)
        elif 153 <= op <= 156: take(op - 152)
        elif 157 <= op <= 160: take(op - 156)
        elif 162 <= op <= 165: take(op - 161)
        elif 167 <= op <= 170: take(op - 166)
        elif 235 <= op <= 238: take(op - 234)
        elif 239 <= op <= 242: specials.add(take(uint(op - 238)).decode('utf-8', errors='replace'))
        elif 243 <= op <= 246:
            take(op - 242 + 12)
            a, b = uint(1), uint(1)
            fonts.add(take(a+b).decode('utf-8', errors='replace'))
        elif op == 247:
            version = uint(1)
            if version != 7: raise ValueError(f'unsupported XDV version {version}')
            take(12)
            take(uint(1))
        elif op == 248: take(28)
        elif op == 249:
            take(5)
            if any(b != 223 for b in data[i:]): raise ValueError('invalid trailer')
            i = len(data)
        elif op == 252:
            take(8)
            flags = uint(2)
            fonts.add(take(uint(1)).decode('utf-8', errors='replace'))
            take(4)
            for flag in (0x200, 0x1000, 0x2000, 0x4000):
                if flags & flag: take(4)
        elif op in (253, 254):
            if op == 254: take(uint(2) * 2)
            take(4)
            take(uint(2) * 10)
        else: raise ValueError(f'unsupported opcode {op} at {i-1}')
    return {'file': str(path), 'pages': counts[139], 'fonts': sorted(fonts), 'specials': sorted(specials), 'opcodes': dict(sorted(counts.items()))}

if __name__ == '__main__':
    print(json.dumps([inspect(path) for path in sys.argv[1:]], indent=2))
