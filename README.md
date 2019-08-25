# alsoslc
Site generator for https://alsoslc.com

This script takes a directory of geotagged images, and creates the pages that make up alsoslc.com:
* Index page with some static text and \~10 randomly selected images. (Set this number in [`NUM_HOME_IMAGES`](https://github.com/mvexel/alsoslc/blob/master/publish.py#L26))
* Map page showing an interactive map with all image locations, using clustering to reduce clutter
* List page with clickable thumbnails for all images in 4 columns
* Individual photo pages with a mini map.

Images in the source folder that do not have geotags are skipped.

The photo 'titles' are generated using reverse geocoding with the [Nominatim](https://nominatim.openstreetmap.org/) geocoder to get street, neighborhood and city.

If the photo has an IPTC `Headline` tag, its content will be used as the title and reverse geocoding skipped. If the photo has an IPTC `Description` tag, its content will be used to generate a longer description text visible on the individual photo page.

We use the [Jinja](https://palletsprojects.com/p/jinja/) template engine for generating the pages.

## Initial Setup

```
$ python3 -m venv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

## Environment Variables

```
export ALSOSLC_SOURCE=/path/to/images/
export ALSOSLC_SITE=/path/to/local/site
export ALSOSLC_REMOTE=user@host:/path/to/site
```

`ALSOSLC_SOURCE` is the source directory of geotagged images. All images must have these EXIF fields for them to be included:

* EXIF `GPSLongitude` will be used for the geolocation
* EXIF `GPSLatitude` will be used for the geolocation
* EXIF `DateTimeOriginal` will be used for populating the date taken
* IPTC `Headline` will be used for the title
* IPTC `Description` will be used for the caption

`ALSOSLC_SITE` is where the local copy of the site will be saved. You can use the empty `site/` directory in this directory or any directory you can write to for `ALSOSLC_SITE`.

`ALSOSLC_REMOTE` is the remote path where the live site lives.

## Deploy

```
./deploy.sh
```

The initial run will be slow as the images are resized and each HTML page is generated. Subsequent runs will be incremental and much faster.

## A note on included assets

The assets included are

* [Leaflet](https://github.com/Leaflet/Leaflet) 1.5.1
* [Bootstrap](https://github.com/twbs/bootstrap) 4.0
* [Lazy Load](https://github.com/tuupola/lazyload) 2.0.0-rc.2

These have their own license separate from this repo's and are included here only for convenience.