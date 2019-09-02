#!/usr/bin/env python3
"""Publish AlsoSLC"""

import sys
import os
from datetime import datetime
from distutils.dir_util import copy_tree
from random import random
import imghdr
from PIL import Image, IptcImagePlugin
from PIL.ExifTags import TAGS, GPSTAGS
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
import requests

ASSETS_DIR = "assets"
IMAGES_DIR = "images"
PAGES = ["index", "map", "list"]
NUM_HOME_IMAGES = 10 # Number of images to display on the home page

IMAGE_WIDTHS = [
    1024,
    240,
]  # full size, [thumbnail size, ...]
IPTC_KEYS = {
    "title": (2, 5),
    "jobtitle": (2, 85),
    "headline": (2, 105),
    "description": (2, 120),
    "copyright": (2, 116),
}

# pylint:disable=C0103


def reverse_geocode(image):
    """Reverse geocode an image using Nominatim"""
    request_url = "https://nominatim.openstreetmap.org/reverse?format=json&lon={lon}&lat={lat}".format(
        lon=image.lon,
        lat=image.lat)
    nominatim_response = requests.get(request_url).json()
    address = nominatim_response.get("address")
    parts = []
    road = address.get("road")
    neighbourhood = address.get("neighbourhood")
    city = address.get("city")
    if road:
        parts.append(road)
    if neighbourhood:
        parts.append(neighbourhood)
    if city:
        parts.append(city)
    return ", ".join(parts)


def get_decimal_from_dms(dms, ref):
    """get decimal degrees from d,m,s and ref"""

    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    if ref in ["S", "W"]:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 5)


def get_coordinates(geotags):
    """Get the lat lon as dms from the geotags"""
    lat = get_decimal_from_dms(
        geotags["GPSLatitude"], geotags["GPSLatitudeRef"]
    )
    lon = get_decimal_from_dms(
        geotags["GPSLongitude"], geotags["GPSLongitudeRef"]
    )
    return (lon, lat)


def label_exifs(exif):
    """Helper to get human readable labels for exif dict"""
    result = {}
    for (key, val) in exif.items():
        result[TAGS.get(key)] = val
    return result


def get_geotagging(exif):
    """Get GPS tags from exifs"""
    if not exif:
        raise ValueError("No EXIF metadata found")

    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == "GPSInfo":
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging


class AlsoSLCSite(object):
    """The site"""

    source_path = None
    site_path = None
    image_widths = []
    images = []

    def render_html(self, page_name):
        """Generate the index page html"""
        jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        home_template = jinja_env.get_template(
            "{}.html".format(page_name)
        )
        return home_template.render(site=self)

    def save(self):
        """Save everything"""

        # create image directory if not exist
        os.makedirs(
            os.path.join(self.site_path, IMAGES_DIR),
            exist_ok=True,
        )

        # gather all images
        total_imagecount = 0
        image_list = os.listdir(self.source_path)
        for filename in image_list:
            total_imagecount += 1
            the_image = AlsoSLCImage.from_file(
                os.path.join(self.source_path, filename)
            )
            if the_image:
                if random() < NUM_HOME_IMAGES / len(image_list):
                    the_image.display_on_home = True
                the_image.save(self)
                self.images.append(the_image)

        # write root pages
        for page_name in PAGES:
            with open(
                os.path.join(
                    self.site_path,
                    "{}.html".format(page_name),
                ),
                "w",
            ) as file_handle:
                file_handle.write(
                    self.render_html(page_name)
                )

        # copy other assets
        copy_tree(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                ASSETS_DIR,
            ),
            os.path.join(self.site_path, ASSETS_DIR),
        )

    def __str__(self):
        return "AlsoSLC site at {}".format(self.site_path)


class AlsoSLCImage(object):
    """An image"""

    description = None
    headline = None
    lon = None
    lat = None
    html = None
    skip = False
    display_on_home = False
    name = None
    image_path = None

    def __init__(self, image_path):
        self.image_path = image_path
        self.name = os.path.splitext(
            os.path.basename(image_path))[0]
        if os.path.exists(
                os.path.join(
                    site.site_path,
                    "{name}.html".format(name=self.name),
                )):
            print("{name} exists, skipping reverse geocode and image generation".format(
                name=self.name))
            self.skip = True
        self.read_exif()

    @classmethod
    def from_file(cls, image_path):
        """Create an image object from an image file path"""
        if os.path.isfile(image_path) and imghdr.what(
                image_path
        ) in ["jpeg", "png"]:
            return cls(image_path)
        return None

    def save(self, my_site):
        """Create and save the HTML + images"""

        if self.skip:
            return

        print("saving {}".format(self.name))

        html_filename = os.path.join(
            site.site_path,
            "{name}.html".format(name=self.name),
        )

        # Render HTML
        jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        home_template = jinja_env.get_template(
            "single.html"
        )
        self.html = home_template.render(
            image=self, site=my_site
        )

        # Save HTML
        with open(html_filename, "w") as file_handle:
            file_handle.write(self.html)

        # Create and save thumbnails
        image_handle = Image.open(self.image_path)
        orig_width = image_handle.size[0]
        for width in site.image_widths:
            if width < orig_width:
                thumb_path = os.path.join(
                    site.site_path,
                    IMAGES_DIR,
                    "{}_{}.jpg".format(self.name, width),
                )
                if not os.path.isfile(thumb_path):
                    im_copy = image_handle.copy()
                    im_copy.thumbnail(
                        (width, width), Image.ANTIALIAS
                    )
                    im_copy.save(thumb_path, "JPEG")
        image_handle = None

    def read_exif(self):
        """Reads relevant exif tags from an image provided as PIL.Image object"""
        image_handle = Image.open(self.image_path)
        exif = image_handle.info["parsed_exif"]
        iptc = IptcImagePlugin.getiptcinfo(image_handle)
        labeled_exifs = label_exifs(exif)
        image_handle = None

        # longitude, latitude
        geotags = get_geotagging(exif)
        self.lon, self.lat = get_coordinates(geotags)

        # date taken
        self._date_taken = datetime.strptime(
            labeled_exifs.get("DateTimeOriginal"),
            "%Y:%m:%d %H:%M:%S",
        )

        # headline
        if not self.skip:
            headline = iptc.get(IPTC_KEYS["headline"])
            if headline is not None:
                self.headline = headline.decode("UTF-8")
            else:
                self.headline = reverse_geocode(self)

            # description
            description = iptc.get(IPTC_KEYS["description"])
            if description is not None:
                self.description = description.decode("UTF-8")
            else:
                self.description = "No description...yet"


    def __str__(self):
        return "AlsoSLC Image {name} at ({lon},{lat})".format(
            name=self.name, lon=self.lon, lat=self.lat
        )

    @property
    def date_taken(self):
        """The date an image was taken as a human readable string"""
        return self._date_taken.strftime("%Y-%m-%d")

    @date_taken.setter
    def set_date_taken(self, val):
        self._date_taken = val

    @property
    def age_in_days(self):
        """The age of the image in days"""
        return (datetime.now() - self._date_taken).days


def crap(message):
    """Croak with a message"""
    print(message)
    sys.exit(-1)


if __name__ == "__main__":
    ARGS = sys.argv
    if len(ARGS) < 2:
        crap("Usage: publish.py SOURCE_ROOT SITE_ROOT")
    SOURCE_ROOT = ARGS[1]
    SITE_ROOT = ARGS[2]

    if not os.path.isdir(SITE_ROOT):
        print("creating {}".format(SITE_ROOT))
        os.makedirs(SITE_ROOT)

    site = AlsoSLCSite()
    site.source_path = os.path.abspath(SOURCE_ROOT)
    site.site_path = os.path.abspath(SITE_ROOT)
    site.image_widths = IMAGE_WIDTHS
    print(site)
    site.save()
