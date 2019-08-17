#!/usr/bin/env python3
"""Publish AlsoSLC"""

import sys
import os
from datetime import datetime
from shutil import rmtree, copytree
import imghdr
import exifread
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape

IMAGES_DIR = None
SITE_ROOT = None
FORCE_RESYNC = False
LAST_RUN = None
ASSETS_DIR = 'assets'
IMAGES_DIR = 'images'
PAGES = ['index', 'map']
IMAGE_WIDTHS = [1024, 240]  # full size, [thumbnail size, ...]

# pylint:disable=C0103

def dms_to_decimal(dms_ratios):
    """Convert given DMS to decimal degrees"""
    in_degs = dms_ratios[0]
    in_mins = dms_ratios[1]
    in_secs = dms_ratios[2]
    return in_degs.num / in_degs.den + (
        in_mins.num / in_mins.den * 60 + in_secs.num / in_secs.den) / 3600

def read_exif(image_handle):
    """Reads relevant exif tags from an image provided as PIL.Image object"""
    lat = 0.0
    lon = 0.0
    date_taken = None
    description = ""

    with open(image_handle.filename, 'rb') as file_handle:
        exifs = exifread.process_file(file_handle, details=True)

    # Check for availability of geotag
    if 'GPS GPSLongitude' not in exifs:
        print("no GPS in image {}".format(image_handle.filename))
        return None
    # Extract decimal coordinates
    lon_dms = exifs.get('GPS GPSLongitude').values
    lat_dms = exifs.get('GPS GPSLatitude').values
    lon_orientation = exifs.get('GPS GPSLongitudeRef').values
    lat_orientation = exifs.get('GPS GPSLatitudeRef').values

    # convert to decimal coords
    lon = dms_to_decimal(lon_dms)
    lat = dms_to_decimal(lat_dms)
    if lon_orientation == 'W':
        lon = -lon
    if lat_orientation == 'S':
        lat = -lat

    # Gather EXIF date, description
    # self.date_taken = exifs.get('EXIF DateTimeOriginal').values
    # 2019:08:04 12:28:53
    date_taken = datetime.strptime(
        exifs.get('EXIF DateTimeOriginal').values,
        '%Y:%m:%d %H:%M:%S')
    desc_exif = exifs.get('Image ImageDescription')
    if desc_exif:
        description = desc_exif.values
    else:
        description = "None given"
    return {"lat": lat, "lon": lon, "date_taken": date_taken, "description": description}

class AlsoSLCSite():  #pylint:disable=R0903
    """The site"""

    source_path = None
    site_path = None
    image_widths = []
    images = []

    def render_html(self, page_name):
        """Generate the index page html"""
        jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml']))
        home_template = jinja_env.get_template('{}.html'.format(page_name))
        return home_template.render(site=self)


    def save(self):
        """Save everything"""

        # create image directory if not exist
        os.makedirs(os.path.join(
            self.site_path,
            IMAGES_DIR), exist_ok=True)

        # gather all images
        for filename in os.listdir(self.source_path):
            the_image = AlsoSLCImage.from_file(
                os.path.join(
                    self.source_path,
                    filename))
            if the_image:
                self.images.append(the_image)
            else:
                print("skipping {}".format(filename))

        # create thumbnails and save them, and the full size image
        for image in self.images:
            image.save(
                self.site_path,
                self.image_widths)

        # write root pages
        for page_name in PAGES:
            with open(os.path.join(
                    self.site_path,
                    '{}.html'.format(page_name)), 'w') as file_handle:
                file_handle.write(self.render_html(page_name))

        # copy other assets
        rmtree(os.path.join(self.site_path, ASSETS_DIR))
        copytree(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), ASSETS_DIR),
            os.path.join(self.site_path, ASSETS_DIR))

    # def smallest_thumbnail_width_for(self, image):
    #     """A helper method for Jinja rendering."""
    #     name, ext = os.path.splitext(
    #         os.path.basename(
    #             image.image_handle.filename))
    #     smallest_width = min(self.image_widths)
    #     return "{name}_{width}{ext}".format(
    #         name=name,
    #         width=smallest_width,
    #         ext=ext)


    def __str__(self):
        return "AlsoSLC site at {}".format(
            self.site_path)


class AlsoSLCImage():
    """An image"""

    _date_taken = None
    description = None
    lon = None
    lat = None
    image_handle = None
    html = None

    def __init__(self, handle, exifs):
        self.image_handle = handle
        self.lon = exifs.get("lon")
        self.lat = exifs.get("lat")
        self.date_taken = exifs.get("date_taken")
        self.description = exifs.get("description")


    @classmethod
    def from_file(cls, image_path):
        """Create an image object from an image file path"""
        if os.path.isfile(image_path) and imghdr.what(image_path) in ['jpeg', 'png']:
            image_handle = Image.open(image_path)
            exifs = read_exif(image_handle)
            if exifs:
                return cls(image_handle, exifs)
        return None


    def save(self, site_path, widths):
        """Create and save the HTML + images"""

        print("saving {}".format(self.name))

        html_filename = os.path.join(
            site_path,
            "{name}.html".format(name=self.name))

        if not os.path.isfile(html_filename):

            # Render HTML
            jinja_env = Environment(
                loader=FileSystemLoader('templates'),
                autoescape=select_autoescape(['html', 'xml']))
            home_template = jinja_env.get_template('single.html')
            self.html = home_template.render(
                image=self,
                relpath=os.path.join(
                    IMAGES_DIR,
                    os.path.basename(self.image_handle.filename)))

            # Save HTML
            with open(
                    html_filename,
                    'w') as file_handle:
                file_handle.write(self.html)

        # Create and save thumbnails
        orig_width = self.image_handle.size[0]
        for width in widths:
            if width < orig_width:
                thumb_path = os.path.join(
                    site_path,
                    IMAGES_DIR,
                    "{}_{}.jpg".format(
                        self.name,
                        width))
                if not os.path.isfile(thumb_path):
                    im_copy = self.image_handle.copy()
                    im_copy.thumbnail((width, width), Image.ANTIALIAS)
                    im_copy.save(thumb_path, "JPEG")

        #Save the original size
        # orig_name = os.path.join(
        #     site_path,
        #     IMAGES_DIR,
        #     os.path.basename(self.image_handle.filename))

        # if not os.path.isfile(orig_name):
        #     self.image_handle.save(orig_name, "JPEG")

    def __str__(self):
        return "AlsoSLC Image {name} at ({lon},{lat})".format(
            name=self.name,
            lon=self.lon,
            lat=self.lat)

    @property
    def date_taken(self):
        """The date an image was taken as a human readable string"""
        return self._date_taken.strftime("%Y-%m-%d")

    @date_taken.setter
    def date_taken(self, val):
        self._date_taken = val

    @property
    def name(self):
        """the bare name of the image"""
        return os.path.splitext(os.path.basename(self.image_handle.filename))[0]


def crap(message):
    """Croak with a message"""
    print(message)
    sys.exit(-1)


if __name__ == '__main__':
    ARGS = sys.argv
    if len(ARGS) < 2:
        crap('Usage: publish.py SOURCE_ROOT SITE_ROOT')
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
