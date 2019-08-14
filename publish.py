#!/usr/bin/env python3

import sys
import os
from pathlib import Path
import exifread
from datetime import datetime
from PIL import Image, ExifTags
from jinja2 import Environment, FileSystemLoader, select_autoescape

IMAGES_PATH = None
SITE_PATH = None
FORCE_RESYNC = False
LAST_RUN = None

def dms_to_decimal(dms_ratios):
    """Convert given DMS to decimal degrees"""
    in_degs = dms_ratios[0]
    in_mins = dms_ratios[1]
    in_secs = dms_ratios[2]
    return in_degs.num / in_degs.den + (
        in_mins.num / in_mins.den * 60 + in_secs.num / in_secs.den) / 3600


class AlsoSLCImageSet():
    """A set of Images"""

    images = []
    html = None
    basename = None
    dest_path = None


    def add_image(self, my_image):
        """Add an image to the set"""
        self.images.append(my_image)


    def save_all(self):
        """Create and save the page with all the images"""
        jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml']))
        home_template = jinja_env.get_template('index.html')
        self.html = home_template.render(imgset=self)

        # save the HTML
        with open(os.path.join(
                        self.dest_path,
                        self.basename + '.html'), 'w') as file_handle:
            file_handle.write(self.html)


class AlsoSLCImage():
    """An image"""

    source_path = None
    dest_path = None
    _date_taken = None
    caption = None
    lon = None
    lat = None
    thumbs = {}
    image_handle = None
    html = None
    image_filename = None
    image_dir_name = None


    def __new__(cls, source_path, dest_path, image_dir_name):
        if source_path and dest_path and image_dir_name:
            instance = super(AlsoSLCImage, cls).__new__(cls)
            instance.source_path = source_path
            instance.dest_path = dest_path
            instance.image_dir_name = image_dir_name
            instance.image_filename = os.path.basename(source_path)
            instance.image_handle = Image.open(source_path)
            if instance._read_exif():  # pylint:disable=protected-access
                return instance
            return None
        return None


    def create_thumbs(self, widths):
        """Create thumbnails for this image of given sizes"""
        orig_width = self.image_handle.size[0]
        for width in widths:
            if width < orig_width:
                im_copy = self.image_handle.copy()
                im_copy.thumbnail((width, width), Image.ANTIALIAS)
                thumb_filename = "{basename}_{width}.jpg".format(
                    basename=os.path.basename(self.image_filename),
                    width=width)
                self.thumbs[width] = {
                    'filename': thumb_filename,
                    'handle': im_copy}

    def _read_exif(self):
        with open(self.source_path, 'rb') as file_handle:
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


    def save_all(self):
        """Create and save the HTML + images"""
        jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=select_autoescape(['html', 'xml']))
        home_template = jinja_env.get_template('single.html')
        self.html = home_template.render(img=self)

        # save the HTML
        with open(
                os.path.join(
                    self.dest_path,
                    os.path.basename(self.image_filename) + '.html'),
                'w') as file_handle:
            file_handle.write(self.html)

        # save the images
        for thumb_width in self.thumbs:
            thumb = self.thumbs[thumb_width]
            thumb_path = os.path.join(
                self.dest_path,
                self.image_dir_name,
                thumb['filename'])
            thumb['handle'].save(thumb_path, "JPEG")
        self.image_handle.save(os.path.join(
            self.dest_path,
            self.image_dir_name,
            os.path.basename(self.image_filename) + ".jpg"), "JPEG")


    def __str__(self):
        return "Also SLC Image at ({lon},{lat}".format(
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
    def full_path(self, size=None):
        """The full path to the thumbnail of given size.
        If size not given return path to full image"""
        if size:
            my_filename = img.thumbs[max(self.thumbs, key=int)]['filename']
        else:
            my_filename = self.image_filename
        return os.path.join(
            self.image_dir_name, my_filename)


def crap(message):
    """Croak with a message"""
    print(message)
    sys.exit(-1)


if __name__ == '__main__':
    ARGS = sys.argv
    if len(ARGS) < 3:
        crap('Usage: publish.py IMG_PATH SITE_PATH [FORCE_RESYNC]')

    IMAGES_PATH = ARGS[1]
    SITE_PATH = ARGS[2]
    if len(ARGS) == 4:
        print('Force a re-sync')
        FORCE_RESYNC = True

    # get last run
    if os.path.exists('.lastrun'):
        LAST_RUN = datetime.fromtimestamp(os.path.getmtime('.lastrun'))
    else:
        Path('.lastrun').touch()
        LAST_RUN = datetime.now()
    print('last run: ', LAST_RUN)

    if not (os.path.isdir(IMAGES_PATH) and os.path.isdir(SITE_PATH)):
        crap('Paths must both exist')

    # create images subdirectory
    os.makedirs(os.path.join(SITE_PATH, 'images'), exist_ok=True)

    print('loading images from', IMAGES_PATH)
    print('saving to', SITE_PATH)

    for filename in os.listdir(IMAGES_PATH):

        img = AlsoSLCImage(os.path.join(IMAGES_PATH, filename), SITE_PATH, 'images')
        # set the relative path for saving images

        if img:
            print(img)
            # Create small sizes
            img.create_thumbs([1024, 640, 320])
            # Save everything
            img.save_all()
        else:
            print("skipping {}".format(filename))
