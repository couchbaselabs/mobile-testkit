import base64
import random
import uuid
import os

from PIL import Image

from keywords.constants import DATA_DIR
from keywords.utils import log_info


def generate_png_100_100():
    att = generate_png(100, 100)
    return att


def generate_png(width, height):
    """ Generates a noise rgb images for attachment testing. """

    img = Image.new("RGBA", (width, height), 255)
    random_rgb_grid = map(lambda x: (
        int(random.random() * 256),
        int(random.random() * 256),
        int(random.random() * 256)
    ), [0] * width * height)

    img.putdata(random_rgb_grid)

    image_temp_name = "{}.png".format(str(uuid.uuid4()))
    image_temp_path = "{}/{}".format(DATA_DIR, image_temp_name)

    # Save temporary image
    log_info("Saving temporary generated image: {}".format(image_temp_path))
    img.save(image_temp_path)

    # Load and store image data
    att = load_from_data_dir(image_temp_name)
    log_info("Creating Attachment: {}".format(image_temp_name))

    # Remove temporary image
    log_info("Removing temporary generated image: {}".format(image_temp_path))
    os.remove(image_temp_path)

    # Return attachment with generated name and loaded image data
    return att


def load_from_data_dir(name):

    file_path = "{}/{}".format(DATA_DIR, name)
    log_info("Loading attachment from file: {}".format(file_path))
    with open(file_path) as f:
        data = base64.standard_b64encode(f.read())
    return Attachment(name, data)


class Attachment:

    def __init__(self, name, data):
        self.name = name
        self.data = data
