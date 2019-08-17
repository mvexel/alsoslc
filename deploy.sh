#!/bin/bash

# directories need to have trailing slashes!

"${ALSOSLC_SOURCEPATH?ALSOSLC_SOURCEPATH not set}"
"${ALSOSLC_SITEPATH?ALSOSLC_SITEPATH not set}"
"${ALSOSLC_REMOTEPATH?ALSOSLC_REMOTEPATH not set}"

# generate site
source venv/bin/activate
./publish.py $ALSOSLC_SOURCEPATH $ALSOSLC_SITEPATH
rsync -avz $ALSOSLC_SITEPATH $ALSOSLC_REMOTEPATH
