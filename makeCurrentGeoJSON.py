#!/usr/bin/env python
# encoding: utf-8

"""
makeCurrentGeoJSON.py

1. Read RSS feed
2. Download each shapefile
3. Convert to GeoJSON
4. Save to file

"""

import requests
import feedparser
import os
import glob
import shutil
import zipfile
import shapefile
import geojson
import datetime
import dateparser

RSS_URLS = ["http://www.nhc.noaa.gov/gis-at.xml","http://www.nhc.noaa.gov/gis-ep.xml"]
ITEMS_WANTED = {"Preliminary Best Track [shp]":"historical","Forecast [shp]":"forecast"}
COMPONENTS = {"historical":["pts"],"forecast":["pgn","pts"]}
STORM_NAMES = open("storm_names.txt").read().splitlines()

def checkDataQuality(rss_feature_list):
    observed_source_types = set([x.properties["source"] for x in rss_feature_list if "source" in x.properties])
    observed_shape_types = set([x.geometry.type for x in rss_feature_list])
    observed_storm_names = set([x.properties["storm"] for x in rss_feature_list if not x.properties["remnant_flag"]])
    polygon_count = len([True for x in rss_feature_list if x.geometry.type == "Polygon" and not x.properties["remnant_flag"]])
    if len(rss_feature_list) == 0:
        print "no features to check"
        return True
    else:
        if not set(["historical", "forecast"]) == observed_source_types:
            print "only observed",observed_source_types
            return False
        if not set(["Point","LineString","Polygon"]) == observed_shape_types:
            print "only observed",observed_shape_types
            return False
        if not len(observed_storm_names) == polygon_count:
            print "observed",len(observed_storm_names),"storms but",len([True for x in rss_feature_list if x.geometry.type == "Polygon"]),"polygons"
            return False
        print "storms parsed ok"
        return True

def download(url):
    print "downloading",url
    filename = url.split("/")[-1]
    filepath = "shp/"+filename
    #always re-download best track
    if not os.path.exists(filepath) or "best_track" in filename:
        response = requests.get(url, stream=True)
        with open(filepath, "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
    return filepath

def unzip(filepath):
    print "unzipping",filepath
    zh = zipfile.ZipFile(filepath, "r")
    unzippedpath = os.path.splitext(filepath)[0]
    zh.extractall(unzippedpath)
    zh.close()
    return unzippedpath

def parseRSS(url):
    rss_response = requests.get(url)
    rss_object = feedparser.parse(rss_response.text)
    rss_feature_list  = []
    for rss_item in rss_object.entries:
        if any(item_wanted in rss_item.title for item_wanted in ITEMS_WANTED.keys()) and any(storm_wanted.upper() in rss_item.title.upper() for storm_wanted in STORM_NAMES):
            for storm in STORM_NAMES:
                if storm in rss_item.title:
                    for item in ITEMS_WANTED.keys():
                        if item in rss_item.title:
                            if "Remnants" in rss_item.title:
                                remnant_flag = True
                            else:
                                remnant_flag = False
                            shp_feature_list = parseSHP(rss_item.link,ITEMS_WANTED[item],storm,remnant_flag)
                            rss_feature_list.extend(shp_feature_list)
    if checkDataQuality(rss_feature_list):
        return rss_feature_list
    else:
        print "failed to parse storms for",url
        raise SystemExit

def strToInt(s):
    return int(s.split(".")[0])

def convertKnotsToMiles(knots):
    return round((float(knots)*1.15078)/5)*5

def hurricaneNumber(wind):
    #wind in knots
    if wind <= 63:
        return None
    if 64 <= wind <= 82:
        return 1
    if 83 <= wind <= 95:
        return 2
    if 96 <= wind <= 112:
        return 3
    if 113 <= wind <= 136:
        return 4
    if wind >= 137:
        return 5

def parseProperties(p,shp_type,component,storm,remnant_flag,shape_index):
    #set up an empty dictionary to return
    o = {}
    #add storm name
    o["storm"] = storm
    o["remnant_flag"] = remnant_flag
    #if polygon, add forecast period and category
    if component == "pgn":
        o["fcstpd"] = p["FCSTPRD"]
        o["cat"] = p["STORMTYPE"]
    #add properties to points
    if component == "pts":
        #say if it"s historical or forecast
        o["source"] = shp_type
        #for forecast
        if shp_type == "forecast":
            #%Y-%m-%d %I:%M %p %a
            #convert to GMT and then drop the timezone reference
            #first forecast time is the same as the advisory issue date
            if shape_index == 0:
                time_fragment = p["ADVDATE"].split(" ")[0]
                if time_fragment.isdigit() and (3 <= len(time_fragment) <= 4):
                    time_fragment_formatted = time_fragment[:-2] + ":" + time_fragment[-2:]
                    if time_fragment_formatted == p["DATELBL"].split(" ")[0]:
                        o["datetime"] = dateparser.parse(time_fragment_formatted + " " + p["ADVDATE"].split(" ",1)[1],settings={"TO_TIMEZONE": "UTC"}).replace(tzinfo=None).isoformat()
                    else:
                        print "advisory hour/label hour mismatch"
                        raise ValueError
                else:
                    print "problem extracting hours from",p["ADVDATE"]
                    raise ValueError
            else:
                o["datetime"] =           dateparser.parse(p["FLDATELBL"],settings={"TO_TIMEZONE": "UTC"}).replace(tzinfo=None).isoformat()
            #pressure in millibars or none
            if p["MSLP"] == "9999.0":
                o["pressure"] = None
            else:
                o["pressure"] = strToInt(p["MSLP"])
            #maximum sustained wind speed
            o["wind"] = strToInt(p["MAXWIND"])
            if shape_index == 0:
                o["current"] = True
            else:
                o["current"] = False
        #for historical
        if shp_type == "historical":
            o["current"] = False
            #this is GMT already
            o["datetime"] = datetime.datetime(strToInt(p["YEAR"]),strToInt(p["MONTH"]),strToInt(p["DAY"]),int(p["HHMM"][0:2])).isoformat()
            #pressure in millibars
            o["pressure"] = strToInt(p["MSLP"])
            #maximum sustained wind speed a.k.a. intensity
            #http://www.nhc.noaa.gov/outreach/presentations/NHC2017_IntensityChallenges.pdf
            o["wind"] = strToInt(p["INTENSITY"])
        #storm category for hurricanes and major hurricanes
        if p["STORMTYPE"] in ["HU","MH"]:
            hurricane_number = hurricaneNumber(o["wind"])
            if hurricaneNumber:
                o["cat"] = "H"+str(hurricane_number)
        else:
            o["cat"] = p["STORMTYPE"]
        #convert wind speed from knots to mph
        o["wind"] = convertKnotsToMiles(o["wind"])
    return o

def parseSHP(url,shp_type,storm,remnant_flag):
    print "parsing",url,"as",shp_type
    shppath = unzip(download(url))
    print "opening",shppath
    shp_feature_list = []
    for component in COMPONENTS[shp_type]:
        for filename in glob.glob(shppath+"/*.shp"):
            if "_"+component in filename:
                component_shp_feature_list = []
                sf = shapefile.Reader(filename)
                shape_records = sf.shapeRecords()
                shape_fields = [f[0] for f in sf.fields][1:]
                for shape_index,shape_record in enumerate(shape_records):
                    properties = dict(zip(shape_fields,shape_record.record))
                    properties = parseProperties(properties,shp_type,component,storm,remnant_flag,shape_index)
                    feature =  geojson.Feature(geometry=shape_record.shape.__geo_interface__,properties=properties)
                    component_shp_feature_list.append(feature)
                if component == "pts":
                    #make linestrings from points
                    linestrings_list = []
                    for i in range(len(component_shp_feature_list)-1):
                        ls = geojson.LineString(
                        [component_shp_feature_list[i].geometry.coordinates,
                        component_shp_feature_list[i+1].geometry.coordinates]
                        )
                        lsf = geojson.Feature(geometry=ls,properties=component_shp_feature_list[i].properties)
                        linestrings_list.append(lsf)
                    component_shp_feature_list = linestrings_list + component_shp_feature_list
                shp_feature_list += component_shp_feature_list
    return shp_feature_list

if __name__ == "__main__":
    url_feature_list = []

    for url in RSS_URLS:
        print "checking",url
        rss_feature_list = parseRSS(url)
        url_feature_list.extend(rss_feature_list)

    feature_collection = geojson.FeatureCollection(url_feature_list)
    with open("geojson/currentGeoJSON.json", "wb") as geojson_file_handle:
        print "saving geojson/currentGeoJSON.json"
        geojson.dump(feature_collection, geojson_file_handle, sort_keys=True)

    storm_set = set([s.properties["storm"] for s in url_feature_list])

    for storm_name in storm_set:
        with open("geojson/"+storm_name+".json","wb") as geojson_file_handle:
            s_feature_collection = geojson.FeatureCollection([s for s in url_feature_list if s.properties["storm"] == storm_name])
            print "saving","geojson/"+storm_name+".json"
            geojson.dump(s_feature_collection,geojson_file_handle, sort_keys=True)
