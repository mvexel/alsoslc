#!/bin/bash

# directories need to have trailing slashes!

echo "${ALSOSLC_SOURCEPATH?ALSOSLC_SOURCEPATH not set}"
echo "${ALSOSLC_SITEPATH?ALSOSLC_SITEPATH not set}"
echo "${ALSOSLC_REMOTEPATH?ALSOSLC_REMOTEPATH not set}"

# generate site
source venv/bin/activate
./publish.py $ALSOSLC_SOURCEPATH $ALSOSLC_SITEPATH
rsync -avz $ALSOSLC_SITEPATH $ALSOSLC_REMOTEPATH
