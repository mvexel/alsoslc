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

class AlsoSLCImage(object):

    path = None
    title = None
    date_taken = None
    description = None
    lon = None
    lat = None
    thumbs = {}
    image_handle = None
    html = None
    basename = None

    def __new__(cls, path):
        if path:
            instance = super(AlsoSLCImage, cls).__new__(cls)
            instance.path = path
            instance.basename = os.path.splitext(os.path.basename(path))[0]
            instance.image_handle = Image.open(path)
            if instance._read_exif():
                return instance

    def create_thumbs(self, widths):
        orig_width = self.image_handle.size[0]
        for width in widths:
            if width < orig_width:
                im_copy = self.image_handle.copy()
                im_copy.thumbnail((width, width), Image.ANTIALIAS)
                # dest_path = os.path.join(SITE_PATH, 'images', fh.name.split('.')[0] + '_' + str(width) + '.jpg')
                # print('saving copy as ' + dest_path)
                thumb_filename = "{basename}_{width}.jpg".format(
                    basename=self.basename,
                    width=width)
                self.thumbs[width] = {
                    'filename': thumb_filename,
                    'handle': im_copy}

    def _dms_to_decimal(self, dms_ratios):
        d = dms_ratios[0]
        m = dms_ratios[1]
        s = dms_ratios[2]
        return d.num / d.den + (m.num / m.den * 60 + s.num / s.den) / 3600


    def _read_exif(self):
        with open(self.path, 'rb') as fh:
            exifs = exifread.process_file(fh, details=False)
    
        # Check for availability of geotag
        if 'GPS GPSLongitude' not in exifs and 'GPS GPSLatitude' not in exifs:
            return False
        
        # Extract decimal coordinates
        lon_dms = exifs.get('GPS GPSLongitude').values
        lat_dms = exifs.get('GPS GPSLatitude').values
        lon_orientation = exifs.get('GPS GPSLongitudeRef').values
        lat_orientation = exifs.get('GPS GPSLatitudeRef').values
        self.lon = self._dms_to_decimal(lon_dms)
        self.lat = self._dms_to_decimal(lat_dms)
        if lon_orientation == 'W': self.lon = -self.lon
        if lat_orientation == 'S': self.lat = -self.lat

        # Gather EXIF date, title, description
        self.date_taken = exifs.get('Image DateTime')
        return True

    def save_all(self, out_basepath, out_imagepath):
        # create the HTML
        home_template = jinja_env.get_template('single.html')
        self.html = home_template.render(
            lon=self.lon,
            lat=self.lat,
            image_path=os.path.join(
                out_imagepath,
                self.thumbs[max(self.thumbs, key=int)]['filename']))

        # save the HTML
        with open(os.path.join(
            out_basepath,
            self.basename + '.html'), 'w') as fh:
            fh.write(self.html)
        
        # save the images
        for thumb_width in self.thumbs.keys():
            thumb = self.thumbs[thumb_width]
            thumb_path = os.path.join(
                SITE_PATH,
                out_imagepath,
                thumb['filename'])
            thumb['handle'].save(thumb_path, "JPEG")
        self.image_handle.save(os.path.join(
            SITE_PATH,
            out_imagepath,
            self.basename + ".jpg"), "JPEG")


    def __str__(self):
        return "Also SLC Image at ({lon},{lat}".format(
            lon=self.lon,
            lat=self.lat)


jinja_env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml']))


def crap(message):
    print(message);
    sys.exit(-1)


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 3:
        crap('Usage: publish.py IMG_PATH SITE_PATH [FORCE_RESYNC]')
    
    IMAGES_PATH = args[1]
    SITE_PATH = args[2]
    if len(args) == 4:
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

        img = AlsoSLCImage(os.path.join(IMAGES_PATH, filename))

        if img:
            print(img)        
            # Create small sizes
            img.create_thumbs([1024, 640, 320])
            # Save everything
            img.save_all(SITE_PATH, 'images')
        else:
            print("skipping {}".format(filename))
