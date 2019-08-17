# alsoslc
Site generator for https://alsoslc.com

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

* `GPS GPSLongitude` will be used for the geolocation
* `GPS GPSLatitude` will be used for the geolocation
* `EXIF DateTimeOriginal` will be used for populating the date taken
* `Image ImageDescription` will be used for the description / caption

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

These have their own license separate from this repo's and are included here only for convenience.