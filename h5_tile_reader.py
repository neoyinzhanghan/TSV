import io
import os
import ray
import time
import h5py
import base64

import openslide
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from PIL import Image


def image_to_jpeg_string(image):
    # Create an in-memory bytes buffer
    buffer = io.BytesIO()
    try:
        # Save the image in JPEG format to the buffer
        image.save(buffer, format="JPEG")
        jpeg_string = buffer.getvalue()  # Get the byte data
    finally:
        buffer.close()  # Explicitly close the buffer to free memory

    return jpeg_string


def jpeg_string_to_image(jpeg_string):
    # Create an in-memory bytes buffer from the byte string
    buffer = io.BytesIO(jpeg_string)

    # Open the image from the buffer and keep the buffer open
    image = Image.open(buffer)

    # Load the image data into memory so that it doesn't depend on the buffer anymore
    image.load()

    return image


def encode_image_to_base64(jpeg_string):
    return base64.b64encode(jpeg_string)


def decode_image_from_base64(encoded_string):
    return base64.b64decode(encoded_string)


class h5_tile_reader:
    """A reader for the dzsave_h5 output. Due to large h5 file size and that the file is intended to be read on a network drive.
    The open-as-read operation presents a significant bottleneck if has to be done every time a tile is read.
    This class is meant to keep the file open during the lifetime of the object.], so the bottleneck only occurs once per slide.

    === Class Attributes ===
    -- h5_path: str
    -- f: h5py.File
    """

    def __init__(self, h5_path: str):
        self.h5_path = h5_path
        self.f = h5py.File(h5_path, "r")

    def open(self):
        if self.f is None:
            self.f = h5py.File(self.h5_path, "r")
        else:
            print("File is already open")

    def close(self):
        if self.f is not None:
            self.f.close()
            self.f = None
        else:
            print("File is already closed")

    def __del__(self):
        self.close()

    def retrieve_tile_h5(self, level, row, col):

        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            try:
                jpeg_string = self.f[str(level)][row, col]
                jpeg_string = decode_image_from_base64(jpeg_string)
                image = jpeg_string_to_image(jpeg_string)

                return image

            except Exception as e:
                print(
                    f"Error: {e} occurred while retrieving tile at level: {level}, row: {row}, col: {col} from {self.h5_path}"
                )
                raise e

    def get_slide_dimensions(self):
        """Return the width (horizontal dimension) and height (vertical dimension) of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["level_0_width"][0], self.f["level_0_height"][0]

    def get_patch_size(self):
        """Return the patch size of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["patch_size"][0]

    def get_num_levels(self):
        """Return the number of levels of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["num_levels"][0]

    def get_overlap(self):
        """Return the overlap of the slide."""
        if self.f is None:
            raise ValueError("File is not open. Call open() method first")
        else:
            return self.f["overlap"][0]


if __name__ == "__main__":
    h5_path = "/dmpisilon_tools/HemeLabel/media/slides/6825083.h5"

    h5_reader = h5_tile_reader(h5_path)

    h5_reader.open()
    width, height = h5_reader.get_slide_dimensions()
    tile_size = h5_reader.get_patch_size()

    num_to_retrieve = 1000

    start_time = time.time()

    with h5py.File(h5_path, "r") as f:
        for i in tqdm(range(num_to_retrieve), desc="Retrieving tiles from h5"):
            # find a random level from 0, 1, ... 18
            random_level = np.random.randint(0, 19)
            downsample_factor = 2 ** (18 - random_level)

            # find a random x and y coordinate
            random_x = np.random.randint(
                0, max((width / downsample_factor) // tile_size, 1)
            )
            random_y = np.random.randint(
                0, max((height / downsample_factor) // tile_size, 1)
            )

            tile = h5_reader.retrieve_tile_h5(random_level, random_x, random_y)
    retrieval_time_h5 = time.time() - start_time

    print(
        f"Retrieval time for h5 for {num_to_retrieve} random tiles:", retrieval_time_h5
    )
    print(f"File size of the h5 file: {os.path.getsize(h5_path) / 1e6} MB")
    print(f"Tile size: {tile.size}")
    print(f"Width: {width}, Height: {height}")
    print(f"Number of levels: {h5_reader.get_num_levels()}")
    print(f"Overlap: {h5_reader.get_overlap()}")

    f.close()
