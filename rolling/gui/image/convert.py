# coding: utf-8
from PIL import Image

from rolling.gui.image.colortrans import rgb2short

"""
THIS CODE HAVE BEEN COPIED FROM https://github.com/hit9/img2txt/blob/gh-pages/LICENSE THEN HAVE
BEEN MODIFIED FOR ROLLING CODE ADAPTATION.

Copyright (c) 2013 - 2016, hit9

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of img2txt nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


def get_pixel(pixels, x, y):
    return " ", pixels[x, y]


def generate_ANSI_from_pixels(pixels, width, height):
    string = []
    for h in range(height):
        string.append([])
        for w in range(width):
            draw_char, rgba = get_pixel(pixels, w, h)

            # RGB to hex
            hexrgb = "#%02x%02x%02x" % rgba[:3]
            # Hex to xterm-256
            short = rgb2short(hexrgb)
            string[-1].append(short[0])

    return string


def load_and_resize_image(imgname, antialias, max_width, max_height, aspectRatio):
    if aspectRatio is None:
        aspectRatio = 1.0

    img = Image.open(imgname)

    # force image to RGBA - deals with palettized images (e.g. gif) etc.
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    native_width, native_height = img.size

    new_width = native_width
    new_height = native_height

    # First apply aspect ratio change (if any) - just need to adjust one axis
    # so we'll do the height.
    if aspectRatio != 1.0:
        new_height = int(float(aspectRatio) * new_height)

    rate = 1.0
    if new_width > max_width and new_height > max_height:
        if max_width < max_height:
            rate = float(max_width) / new_width
        else:
            rate = float(max_height) / new_height
    elif new_width > max_width:
        rate = float(max_width) / new_width
    elif new_height > max_height:
        rate = float(max_height) / new_height

    new_width = int(new_width * rate)
    new_height = int(new_height * rate)

    # # Now isotropically resize up or down (preserving aspect ratio) such that
    # # longer side of image is maxLen
    # width_rate = float(max_width) / max(new_width, new_height)
    # height_rate = float(max_height) / max(new_width, new_height)
    # new_width = int(width_rate * new_width)
    # new_height = int(height_rate * new_height)

    if native_width != new_width or native_height != new_height:
        img = img.resize((new_width, new_height), Image.ANTIALIAS if antialias else Image.NEAREST)

    return img


def convert_img_to_urwid(image_path, max_width, max_height):
    image = load_and_resize_image(
        image_path, antialias=True, max_width=max_width, max_height=max_height, aspectRatio=0.5
    )
    pixel = image.load()
    width, height = image.size
    return generate_ANSI_from_pixels(pixel, width, height)
