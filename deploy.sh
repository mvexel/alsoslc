#!/bin/bash

echo $ALSOSLC_SOURCEPATH
"${ALSOSLC_SOURCEPATH?ALSOSLC_SOURCEPATH not set}"
"${ALSOSLC_SITEPATH?ALSOSLC_SITEPATH not set}"
# generate site
source venv/bin/activate
./publish.py $ALSOSLC_SOURCEPATH $ALSOSLC_SITEPATH
rsync -avz $ALSOSLC_SOURCEPATH www-data@alsoslc.com:/var/www/html/alsoslc.com/public_html
