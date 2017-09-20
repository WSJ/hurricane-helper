# Hurricane Helper
Hurricane Helper is the data processor for [The Wall Street Journal's Hurricane Tracker](http://www.wsj.com/graphics/hurricane-map/). This script is an opinionated parser of [National Hurricane Center](http://www.nhc.noaa.gov/) storm data, written in Python.  For every named storm tracked by the center in the [Atlantic](http://www.nhc.noaa.gov/gis-at.xml) and [Eastern Pacific](http://www.nhc.noaa.gov/gis-ep.xml) oceans, Hurricane Helper creates a GeoJSON FeatureCollection and saves it as a .json file in `geojson/` with the name of the storm. The FeatureCollection contains:

1. A polygon feature of the forecast cone with the following properties:
  * **storm** The storm name in title case
  * **cat** The storm intensity
  * **fcstpd** The forecast period in hours (always "120", 5 days)

2. Linestring features representing the historical and forecast track segments, each with the following properties, attributable to the first point of the linestring:
  * **storm** The storm name in title case
  * **cat** The storm intensity
  * **datetime** ISO 8601 datetime in UTC/GMT,
  * **wind** wind speed in miles per hour,
  * **pressure** pressure in millibars (or `null` if `source` is `forecast`),
  * **source** "historical" or "forecast"
  * **current** boolean true for the first forecast point, listed as "current center location" by the NHC

3. Point features, in oldest-to-newest order, each with the same properties as the linestring segments.

All storms are also added to one big FeatureCollection and saved to `geojson/currentGeoJSON.json`.

Since the goal of this project is to show _all_ current hurricanes, if you wish to display a single storm, you can filter on the **storm** name property.

### Storm categories
For polygons, we use the category provided by the NHC:
* **HU** Hurricane
* **MH** Major hurricane ([Saffir-Simpson scale](http://www.nhc.noaa.gov/aboutsshws.php) category 3 and above)

For points and linestrings, we replace HU or MH with H1-H5 depending on the [Saffir-Simpson scale](http://www.nhc.noaa.gov/aboutsshws.php).

For less intense wind speed measurements, we've recently observed the following categories:
* **TS** [Tropical storm](http://www.nhc.noaa.gov/aboutgloss.shtml#TROPSTRM)
* **STS** [Subtropical storm](http://www.nhc.noaa.gov/aboutgloss.shtml#SUBSTRM)
* **STD** [Subtropical depression](http://www.nhc.noaa.gov/aboutgloss.shtml#SUBDEP)
* **DB** [Tropical disturbance](http://www.nhc.noaa.gov/aboutgloss.shtml#TROPDIST)
* **LO** [Remnant low](http://www.nhc.noaa.gov/aboutgloss.shtml#REM)

Other categories may be reported.

### Problems solved
* Forecasts are produced in "local" time, while historical positions are recorded in UTC/GMT. This standardizes all times to UTC/GMT.
* Small, unimportant tropical disturbances are included in the official RSS feed. This outputs only named storms.
* Sometimes the forecast cones are not in the shapefiles. This suppresses the output until all features are present for each storm.
* Wind speeds are reported in knots. This converts to miles per hour using the correct precision.
* Hurricane numbers aren't specified. This puts each hurricane on the 1-5 scale.
* Nonexistent values are given as `-9999.0`. This changes those to `None` (Python)/`null` (JavaScript).
* Storms disappear after they are no longer tracked. This saves the last data for each storm to a file for that storm.

### Mysteries
The last historical point and the first forecast point have the same `datetime` but different locations. This may be because the first forecast point contains some uncertainty.

## Development
`sh setup.sh` to create a Python virtual environment and install requirements

## Production
`sh updateData.sh` provides a shell script template for processing the files with a cron job.

## License
[ISC](/LICENSE)
