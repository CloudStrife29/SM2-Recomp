import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counted_mips_relocations import parse, parse_stream, relocate


def container(images, streams):
    offset = stream_offset = 0
    records = []
    for image, stream in zip(images, streams):
        records.append((offset, len(image), stream_offset))
        offset += len(image)
        stream_offset += len(stream)
    return (struct.pack('<I', len(images)) +
            b''.join(struct.pack('<III', *record) for record in records) +
            b''.join(images) + b''.join(streams))


class CountedRelocationsTest(unittest.TestCase):
    def test_all_kinds_preserve_instruction_fields_and_offset_zero(self):
        image = struct.pack('<4I', 12, 0x3c080000, 0x25090040, 0x0ffffffe)
        stream = struct.pack('<6I', 0, 5, 0x7000, 10, 15, 0xffffffff)
        original = container([image], [stream])
        member, = parse(original)
        relocated = relocate(member, 0x80101234)
        self.assertEqual(struct.unpack('<4I', relocated),
                         (0x80101240, 0x3c088011, 0x25091274, 0x0c04048b))
        self.assertEqual(member.image, image)
        self.assertEqual(original, container([image], [stream]))

    def test_separate_member_images_and_streams(self):
        source = container([struct.pack('<I', 0), struct.pack('<I', 8)],
                           [struct.pack('<I', 0xffffffff), struct.pack('<2I', 0, 0xffffffff)])
        first, second = parse(source)
        self.assertEqual(first.image_offset, 28)
        self.assertEqual(second.image_offset, 32)
        self.assertEqual(relocate(first, 0x80020000), bytes(4))
        self.assertEqual(relocate(second, 0x80120000), struct.pack('<I', 0x80120008))

    def test_out_of_bounds_and_repeated_writes_are_rejected(self):
        for words in ((4, 0xffffffff), (0, 0, 0xffffffff)):
            with self.subTest(words=words), self.assertRaises(ValueError):
                parse(container([bytes(4)], [struct.pack('<%dI' % len(words), *words)]))

    def test_truncated_stream_and_extra_bytes_are_rejected(self):
        for stream in (struct.pack('<I', 1), struct.pack('<I', 0),
                       struct.pack('<2I', 0xffffffff, 0)):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                parse(container([bytes(4)], [stream]))

    def test_invalid_counts_and_overlapping_images_are_rejected(self):
        source = container([bytes(4), bytes(4)], [struct.pack('<I', 0xffffffff)] * 2)
        for offset, value in ((0, 0), (0, 4097), (16, 0)):
            bad = bytearray(source)
            struct.pack_into('<I', bad, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                parse(bytes(bad))

    def test_placement_must_fit_ram_and_be_aligned(self):
        member, = parse(container([bytes(8)], [struct.pack('<I', 0xffffffff)]))
        for base in (0x80000001, 0x7fffffff, 0x807ffffc):
            with self.subTest(base=base), self.assertRaises(ValueError):
                relocate(member, base)

    def test_separate_stream_relocates_like_a_container_member(self):
        image = struct.pack('<4I', 12, 0x3c080000, 0x25090040, 0x0ffffffe)
        stream = struct.pack('<6I', 0, 5, 0x7000, 10, 15, 0xffffffff)
        member = parse_stream(image, stream, image_offset=0x800, stream_offset=0x1000)
        counted, = parse(container([image], [stream]))
        self.assertEqual(member.relocations, counted.relocations)
        self.assertEqual((member.image_offset, member.stream_offset, member.stream_end),
                         (0x800, 0x1000, 0x1000 + len(stream)))
        for base in (0x80101234, 0x8010fffc, 0x801fffe0):
            with self.subTest(base=base):
                self.assertEqual(relocate(member, base), relocate(counted, base))

    def test_separate_stream_must_be_complete_and_exact(self):
        image = bytes(8)
        for stream in (struct.pack('<2I', 0xffffffff, 0),       # bytes after the terminator
                       struct.pack('<I', 0),                    # no terminator
                       struct.pack('<I', 1),                    # HI16 without its addend
                       struct.pack('<2I', 8, 0xffffffff),       # target outside the image
                       struct.pack('<3I', 0, 0, 0xffffffff),    # repeated target
                       struct.pack('<I', 0xffffffff)[:3]):      # not whole words
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                parse_stream(image, stream)
        for bad_image in (b'', bytes(6)):
            with self.subTest(image=bad_image), self.assertRaises(ValueError):
                parse_stream(bad_image, struct.pack('<I', 0xffffffff))


if __name__ == '__main__':
    unittest.main()
