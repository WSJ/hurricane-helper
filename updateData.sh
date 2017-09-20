#!/bin/bash
rm -r shp/*

source virt-hurricanemap/bin/activate
python makeCurrentGeoJSON.py
deactivate

#don't iterate when there are no files
shopt -s nullglob
for filename in ./geojson/*.json; do
      #upload/rsync your files using a command here
      echo "$filename"
done
