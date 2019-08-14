#!/usr/bin/env python3
"""Publish AlsoSLC"""

import sys
import os
from pathlib import Path
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

# pylint:disable=C0103

def dms_to_decimal(dms_ratios):
    """Convert given DMS to decimal degrees"""
    in_degs = dms_ratios[0]
    in_mins = dms_ratios[1]
    in_secs = dms_ratios[2]
    return in_degs.num / in_degs.den + (
        in_mins.num / in_mins.den * 60 + in_secs.num / in_secs.den) / 3600


class AlsoSLCSite():  #pylint:disable=R0903
    """The site"""

    source_path = None
    root_path = None
    assets_subdir = None
    images_subdir = None
    thumb_sizes = []
    images = []

    def index_html(self):
        """Generate the index page html"""
        jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml']))
        home_template = jinja_env.get_template('index.html')
        return home_template.render(site=self)


    def save(self):
        """Save everything"""

        # clean out site root
        rmtree(self.root_path)

        # create image directory if not exist
        os.makedirs(os.path.join(
            self.root_path,
            self.images_subdir), exist_ok=True)

        # gather all images
        for filename in os.listdir(
                os.path.join(
                    self.source_path,
                    self.images_subdir)):

            print("opening image at {}".format(
                os.path.join(
                    self.source_path,
                    self.images_subdir,
                    filename)))
            the_image = AlsoSLCImage.from_file(
                os.path.join(
                    self.source_path,
                    self.images_subdir,
                    filename))
            if the_image:
                self.images.append(the_image)
                print("added {}, now {}".format(the_image, len(self.images)))
            else:
                print("skipping {}".format(filename))

        # create thumbnails and save them, and the full size image
        for image in self.images:
            image.create_thumbs(self.thumb_sizes)
            image.save(self.root_path, os.path.join(self.root_path, self.images_subdir))

        # write index page
        with open(os.path.join(
                self.root_path,
                'index.html'), 'w') as file_handle:
            file_handle.write(self.index_html())

        # copy other assets
        copytree(
            os.path.join(self.source_path, self.assets_subdir),
            os.path.join(self.root_path, 'assets'))

    def __str__(self):
        return "AlsoSLC site at {} with assets at {} and images at {}".format(
            self.root_path,
            self.assets_subdir,
            self.images_subdir)


class AlsoSLCImage():
    """An image"""

    _date_taken = None
    caption = None
    lon = None
    lat = None
    thumbs = {}
    image_handle = None
    html = None

    def __init__(self, handle):
        self.image_handle = handle
        self._read_exif()

    @classmethod
    def from_file(cls, image_path):
        """Create an image object from an image file path"""
        if os.path.isfile(image_path) and imghdr.what(image_path) in ['jpeg', 'png']:
            image_handle = Image.open(image_path)
            print("handle of image: ", image_handle)
            return cls(image_handle)
        return None

    def create_thumbs(self, widths):
        """Create thumbnails for this image of given sizes"""
        orig_width = self.image_handle.size[0]
        for width in widths:
            if width < orig_width:
                im_copy = self.image_handle.copy()
                im_copy.thumbnail((width, width), Image.ANTIALIAS)
                thumb_filename = "{basename}_{width}.jpg".format(
                    basename=os.path.basename(self.image_handle.filename),
                    width=width)
                self.thumbs[width] = {
                    'filename': thumb_filename,
                    'handle': im_copy}

    def _read_exif(self):
        with open(self.image_handle.filename, 'rb') as file_handle:
            exifs = exifread.process_file(file_handle, details=True)

        # Check for availability of geotag
        if 'GPS GPSLongitude' not in exifs and 'GPS GPSLatitude' not in exifs:
            return False

        # Extract decimal coordinates
        lon_dms = exifs.get('GPS GPSLongitude').values
        lat_dms = exifs.get('GPS GPSLatitude').values
        lon_orientation = exifs.get('GPS GPSLongitudeRef').values
        lat_orientation = exifs.get('GPS GPSLatitudeRef').values
        self.lon = dms_to_decimal(lon_dms)
        self.lat = dms_to_decimal(lat_dms)
        if lon_orientation == 'W':
            self.lon = -self.lon
        if lat_orientation == 'S':
            self.lat = -self.lat

        # Gather EXIF date, caption
        # self.date_taken = exifs.get('EXIF DateTimeOriginal').values
        # 2019:08:04 12:28:53
        self.date_taken = datetime.strptime(
            exifs.get('EXIF DateTimeOriginal').values,
            '%Y:%m:%d %H:%M:%S')
        desc_exif = exifs.get('Image ImageDescription')
        if desc_exif is not None:
            self.caption = desc_exif.values
        else:
            self.caption = "N/A"
        return True

    def save(self, site_path, image_subdir):
        """Create and save the HTML + images"""
        jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml']))
        home_template = jinja_env.get_template('single.html')
        self.html = home_template.render(
            image=self,
            relpath=os.path.join(image_subdir, self.image_handle.filename))

        # save the HTML
        with open(
                os.path.join(
                    site_path,
                    os.path.splitext(os.path.basename(self.image_handle.filename))[0] + '.html'),
                'w') as file_handle:
            file_handle.write(self.html)

        # save the images
        for thumb_width in self.thumbs:
            thumb = self.thumbs[thumb_width]
            thumb_path = os.path.join(
                site_path,
                image_subdir,
                thumb['filename'])
            thumb['handle'].save(thumb_path, "JPEG")
        self.image_handle.save(os.path.join(
            site_path,
            image_subdir,
            os.path.basename(self.image_handle.filename)), "JPEG")

    def __str__(self):
        return "AlsoSLC Image at ({lon},{lat})".format(
            lon=self.lon,
            lat=self.lat)

    @property
    def date_taken(self):
        """The date an image was taken as a human readable string"""
        return self._date_taken.strftime("%Y-%m-%d")

    @date_taken.setter
    def date_taken(self, val):
        self._date_taken = val


def crap(message):
    """Croak with a message"""
    print(message)
    sys.exit(-1)


if __name__ == '__main__':
    ARGS = sys.argv
    if len(ARGS) < 4:
        crap('Usage: publish.py SOURCE_ROOT SITE_ROOT IMAGES_DIR ASSETS_DIR [FORCE_RESYNC]')
    SOURCE_ROOT = ARGS[1]
    SITE_ROOT = ARGS[2]
    IMAGES_DIR = ARGS[3]
    ASSETS_DIR = ARGS[4]
    if len(ARGS) == 5:
        print('Force a re-sync')
        FORCE_RESYNC = True

    # get last run
    if os.path.exists('.lastrun'):
        LAST_RUN = datetime.fromtimestamp(os.path.getmtime('.lastrun'))
    else:
        Path('.lastrun').touch()
        LAST_RUN = datetime.now()
    print('last run: ', LAST_RUN)

    if not os.path.isdir(SITE_ROOT):
        crap('Site root does not exist')

    site = AlsoSLCSite()
    site.source_path = os.path.abspath(SOURCE_ROOT)
    site.root_path = os.path.abspath(SITE_ROOT)
    site.assets_subdir = ASSETS_DIR
    site.images_subdir = IMAGES_DIR
    site.thumb_sizes = [1024, 640, 320]
    print(site)
    site.save()
