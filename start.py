import struct
import unittest


def column_create(dicty):
    column_count = len(dicty)

    buf = []

    flags = struct.pack('B', 4)
    buf.append(flags)

    buf.append(struct.pack('H', column_count))

    return b''.join(buf)


def hexs(byte_string):
    return ''.join(("%02X" % ord(x) for x in byte_string))


class ColumnCreateTests(unittest.TestCase):
    def assert_hex(self, dicty, hexstring):
        assert hexs(column_create(dicty)) == hexstring

    def test_1212(self):
        self.assert_hex({"1212": 1212}, b"040100040000000000313231327809")


if __name__ == '__main__':
    unittest.main()
