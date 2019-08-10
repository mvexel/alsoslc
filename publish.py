#!/usr/bin/env python3

import sys
import os
import exifread
from PIL import Image, ExifTags

OUT_PATH = ''

def crap(message):
	print(message);
	sys.exit(-1)

def dms_to_decimal(dms_ratios):
	d = dms_ratios[0]
	m = dms_ratios[1]
	s = dms_ratios[2]
	return d.num / d.den + (m.num / m.den * 60 + s.num / s.den) / 3600

def create_thumbs(image_fh, widths):
	im = Image.open(fh)
	orig_width = im.size[0]
	for width in widths:
		if width < orig_width:
			im_copy = im.copy()
			im_copy.thumbnail((width, width), Image.ANTIALIAS)
			dest_path = os.path.join(OUT_PATH, fh.name.split('.')[0] + '_' + str(width) + '.jpg')
			print('saving copy as ' + dest_path)
			im_copy.save(dest_path, 'JPEG')

def create_photopage(image_fh, lon, lat):
	# print('Creating photo page for ' + image_fh.name)
	pass

if __name__ == '__main__':
	args = sys.argv
	if len(args) != 3:
		crap('Usage: publish.py IMG_PATH SITE_PATH')
	
	inpath = args[1]
	OUT_PATH = args[2]

	if not (os.path.isdir(inpath) and os.path.isdir(OUT_PATH)):
		crap('Paths must both exist')

	print('saving to ' + OUT_PATH)

	for filename in os.listdir(inpath):
		# Get EXIF tags
		fh = open(os.path.join(inpath, filename), 'rb')
		exifs = exifread.process_file(fh, details=False)
	
		# Check for availability of geotag
		if 'GPS GPSLongitude' not in exifs and 'GPS GPSLatitude' not in exifs:
			print('Image ' + fh.name + 'is not geotagged')
			continue
		
		# Extract decimal coordinates
		lon_dms = exifs.get('GPS GPSLongitude').values
		lat_dms = exifs.get('GPS GPSLatitude').values
		lon_orientation = exifs.get('GPS GPSLongitudeRef').values
		lat_orientation = exifs.get('GPS GPSLatitudeRef').values
		lon = dms_to_decimal(lon_dms)
		lat = dms_to_decimal(lat_dms)
		if lon_orientation == 'W': lon = -lon
		if lat_orientation == 'S': lat = -lat

		# Gather EXIF date, title, description
		image_date = exifs.get('Image DateTime')

		# Create small sizes
		create_thumbs(fh, [2000, 800])

		# Create photo page
		create_photopage(fh, lon, lat)

		# Close file handle for image
		fh.close()
