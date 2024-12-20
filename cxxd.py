#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from collections import deque
from copy import deepcopy
from signal import signal, SIGPIPE, SIG_DFL


def colorize(s, vt100_index):
    return "\033[38;5;%dm%s\033[0m" % (vt100_index, s)


class XXDParser(object, metaclass=ABCMeta):
    null_color = 59
    address_separator = ": "
    hex_separator = "  "
    pixel_char = "\u25FC"
    regex_bin = "([01]{8})"
    regex_hex = "([A-Fa-f0-9]{2})"

    def __init__(self, binary):
        self.base = 2 if binary else 16
        self.regex = XXDParser.regex_bin if binary else XXDParser.regex_hex

    @abstractmethod
    def color_picker(self, byte):
        """Return the color index that this byte maps to."""
        raise NotImplementedError

    @abstractmethod
    def show_palette(self):
        """Return the expected color mapping."""
        raise NotImplementedError

    def parse(self, hex_data, pixelate):
        byte_data = (b for b in re.split(self.regex, hex_data))

        def map_color(byte):
            if not byte.strip():
                return byte
            to_show = XXDParser.pixel_char if pixelate else byte
            return colorize(to_show, self.color_picker(int(byte, self.base)))

        colored_data = (map_color(b) for b in byte_data)
        return "".join(colored_data)


class GradientPalette(XXDParser):
    base_palette = deque(
        [
            131,
            167,
            203,
            209,
            173,
            137,
            179,
            221,
            227,
            191,
            149,
            120,
            78,
            79,
            116,
            117,
            74,
            75,
            68,
            105,
            62,
            98,
            97,
            134,
            176,
            207,
            164,
            163,
            126,
            132,
            168,
        ]
    )

    def __init__(self, binary, rotate_index):
        super(GradientPalette, self).__init__(binary)
        self.palette = GradientPalette.rotate(rotate_index)

    @staticmethod
    def rotate(num):
        rotated = deepcopy(GradientPalette.base_palette)
        rotated.rotate(-num)
        return rotated

    def color_picker(self, byte):
        if not byte:
            return XXDParser.null_color
        index = int(len(self.palette) * byte / 256.0)
        return self.palette[index]

    def show_palette(self):
        raise NotImplementedError("boo")


class AsciiPalette(XXDParser):
    def __init__(self, binary, rotate_index):
        super(GradientPalette, self).__init__(binary)
        self.palette = GradientPalette.rotate(rotate_index)

    def color_picker(self, byte):
        if byte >= 0x20 and byte < 0x7F:
            # byte is a printable character
            byte = chr(byte)
            if byte.isalpha():
                return  # chars
            if byte.isdigit():
                return  # num
            if byte == " ":
                return  # space
            if byte == "	":
                return  # tab
            return  # punctuation
        if byte == 0x0A:
            return  # newline
        if byte == 0x0D:
            return  # carriage return
        return XXDParser.null_color  # other

    def show_palette(self):
        raise NotImplementedError("boo")


def format_line(line, colorizer):
    if line == "*\n":
        return line
    address, hex_ascii = line.split(XXDParser.address_separator, 1)
    hex_data, ascii_data = hex_ascii.split(XXDParser.hex_separator, 1)
    hex_data = colorizer(hex_data)
    return (
        address
        + XXDParser.address_separator
        + hex_data
        + XXDParser.hex_separator
        + ascii_data[:-1]
    )


def main():
    signal(SIGPIPE, SIG_DFL)

    ap = argparse.ArgumentParser(
        description="colorized xxd",
        epilog="NOTE: Above are cxxd-specific optargs. All xxd optargs should also be supported.",
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=25, width=80
        ),
    )
    ap.add_argument(
        "-R",
        "--rotate",
        type=int,
        default=0,
        help="circularly rotate color gradient base index",
    )
    ap.add_argument(
        "-x",
        "--pixelate",
        action="store_true",
        default=False,
        help="replace hex values with colored blocks",
    )
    args, rem_args = ap.parse_known_args()

    parser = GradientPalette(False, args.rotate)
    colorizer = lambda line: parser.parse(line, args.pixelate)
    xxd = subprocess.Popen(
        ["xxd"] + rem_args, stdin=sys.stdin, stdout=subprocess.PIPE, close_fds=False
    )
    for line in xxd.stdout:
        print(format_line(line.decode(), colorizer))

    # When `xxd` returns an error code, propagate it up.
    exitcode = xxd.wait()
    if exitcode:
        exit(exitcode)


if __name__ == "__main__":
    main()
