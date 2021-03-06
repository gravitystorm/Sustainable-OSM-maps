# -*- coding: utf-8 -*-
#! /usr/bin/python

"""
  extract_pois.py
  Copyright 2010 Tom Chance <tom@acrewoods.net>

  This script downloads data from OpenStreetMap related to
  sustainable lifestyles and turns it into KML feeds.

  This program is free software; you may redistribute it and/or
  modify it under the terms of the GNU General Public License as
  published by the Free Software Foundation; either version 3 of
  the License, or (at your option) any later version.

  This program is distributed in the hope that it will be useful, 
  but WITHOUT ANY WARRANTY; without even the implied warranty of 
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
  GNU General Public License for more details.

  http://www.gnu.org/licenses/gpl-3.0.html
"""
 
import libxslt
import libxml2
import re
import urllib
import os
import csv
import sys
import flickr

libxml2.lineNumbersDefault(1)
libxml2.substituteEntitiesDefault(1)

def escape(html):
    """
      Returns the given HTML with ampersands, quotes and carets encoded,
      and encoded into unicode for weird characters.
    """
    html_enc = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
    return unicode(html_enc, 'utf-8')

def processRawData(xapi_uri, xsl_uri, features):
  """
    Downloads the data from XAPI and turns it into a Python object.
  """
  # Download data to temporary file and read the XML/XSL into memory
  if ('-v' in sys.argv):
    print "Downloading %s" % (xapi_uri)
  urllib.urlretrieve(xapi_uri,'temp.xml')
  osmdoc = libxml2.parseFile('temp.xml')
  styledoc = libxml2.parseFile(xsl_uri)
  style = libxslt.parseStylesheetDoc(styledoc)

  # Translate XML to CSV (easier to then read into py object)
  if ('-v' in sys.argv):
    print "Processing data..."
  for key,value in features.iteritems():
    result = style.applyStylesheet(osmdoc,\
      { "key":"'%s'"%key, "value":"'%s'"%value })
    style.saveResultToFilename('temp.csv', result, 0)

  # Encode HTML elements
  f = open('temp.csv', 'r')
  safe_content = escape(f.read())
  f = open('temp.csv', 'w')
  f.write(safe_content.encode('utf-8'))
  
  # Read CSV file into dict
  csv_file = open('temp.csv', 'rb')
  temp_data = csv_file.read()
  temp_data_unicoded = unicode(temp_data, 'utf-8')
  pdata = csv.DictReader(csv_file, delimiter='	')
  for row in pdata:
    print row
  exit(42)
  return pdata

def generateKMLStyle(name,icon):
  """
    Return a valid KML style definition
  """
  return """<Style id="%s">\n\t<IconStyle>\n\t\t<Icon>\n\t\t\t<href>%s</href>\n\t\t</Icon>\n\t\t<hotSpot x="0.5" y="0" xunits="fraction" yunits="fraction"/>\n\t</IconStyle>\n</Style>\n""" % (name,icon)

def generateKMLHeader(styles,document_name):
  """
    Return a valud KML header definition
  """
  kml_styles = ''
  for name,icon in styles.iteritems():
    kml_styles = ''.join([kml_styles, generateKMLStyle(name,icon)])
  return """<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n\t<name>%s</name>\n%s\n\n""" % (document_name, kml_styles)

def generateKMLPlacemark(row,style):
  """
    Return a valud KML placemark definition adding in
    data from the universal tags (description, website, etc.)
  """
  name = row['name']
  lon = row['lon']
  lat = row['lat']
  if (row['description']):
    description = row['description']
  else:
    description = "<p>No further details known</p>"
  if (row['flickr']):
    pdata = flickr._doget('flickr.photos.getSizes', photo_id=row['flickr'])
    for psize in pdata.rsp.sizes.size:
      if (psize.label == 'Small'):
        description = "".join([description, """<p><img src="%s"></p>""" % (psize.source)])
  if (row['operator']):
    description = "".join([description, """<p><strong>Operator:</strong> %s</p>""" % (row['operator'])])
  if (row['website'] or row['wikipedia']):
    description = "".join([description, "<p><strong>More information:</strong> "])
    if (row['website']):
      description = "".join([description, """<a href="%s">Website</a> """ % (row['website'])])
    if (row['wikipedia']):
      row['wikipedia'] = re.sub(r'en:', '', row['wikipedia'])
      row['wikipedia'] = re.sub(r'http://en.wikipedia.org/wiki/', '', row['wikipedia'])
      description = "".join([description, """<a href="http://en.wikipedia.org/wiki/%s">Wikipedia article</a>""" % (row['wikipedia'])])
    description = "".join([description, "</p>"])
  return """<Placemark>\n\t<name>%s</name>\n\t<description><![CDATA[%s]]></description>\n\t<styleUrl>#%s</styleUrl>\n\t<Point>\n\t\t<coordinates>%s,%s</coordinates>\n\t</Point>\n</Placemark>\n""" % (name,description,style,lon,lat)

def doFood():
  """
    Create a KML feed for allotments and food markets
  """
  # Set-up styles and header
  styles = {"foodAllotment":"http://tomchance.dev.openstreetmap.org/pois/food_allotment.png",
		"foodMarket":"http://tomchance.dev.openstreetmap.org/pois/food_market.png"}
  output = generateKMLHeader(styles,"Sustainable food in London")

  # Get and process data for allotments
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[landuse=allotments][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_allotments.xsl'
  features = {"landuse":"allotments"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Allotments'
    output = ''.join([output, generateKMLPlacemark(row, 'foodAllotment')])
  
  ## Get and process data for food markets
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[amenity=marketplace][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_markets.xsl'
  features = {"amenity":"marketplace"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    # Skip markets that don't sell fish/meat/veg
    if (row['vegetables'] != 'yes' and row['meat'] != 'yes' and row['fish'] != 'yes'):
      continue
    if (row['name'] == ''):
      row['name'] = 'Food market'
    output = ''.join([output, generateKMLPlacemark(row, 'foodMarket')])

  output = ''.join([output, "</Document></kml>"])
  return output

def doWaste():
  """
    Create a KML feed for recycling bins, depots and landfill sites
  """
  # Set-up styles and header
  styles = {"wasteRecyclingBin":"http://tomchance.dev.openstreetmap.org/pois/waste_recycle.png",
	    "wasteRecyclingDepot":"http://tomchance.dev.openstreetmap.org/pois/waste_recycle.png",
	    "wasteLandfill":"http://tomchance.dev.openstreetmap.org/pois/waste_landfill.png"}
  output = generateKMLHeader(styles,"Waste facilities in London")
  recycling_regexp = re.compile(r'recycling:(\w+)')

  # Get and process data for recycling bins
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[amenity=recycling][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_recycling.xsl'
  features = {"amenity":"recycling"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Recycling bin(s)'
    recycling_list = []
    has_detail = 0
    for k,v in row.iteritems():
      if (v == 'yes'):
	result = recycling_regexp.search(k)
	if (result):
	  has_detail = 1
	  recycling_list.append(result.groups(0))
    if (has_detail):
      row['description'] = ''.join([row['description'], "<p><strong>Recycling facilities for:</strong> "])
      recycling_list.sort()
      for item in recycling_list:
        row['description'] = ''.join([row['description'], "%s, " % (item)])
      row['description'] = ''.join([row['description'], "</p>"])
    output = ''.join([output, generateKMLPlacemark(row, 'wasteRecyclingBin')])

  # Get and process data for waste depots 
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[amenity=waste_transfer_station][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_recycling.xsl'
  features = {"amenity":"waste_transfer_station"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Recycling centre'
    recycling_list = []
    has_detail = 0
    for k,v in row.iteritems():
      if (v == 'yes'):
	result = recycling_regexp.search(k)
	if (result):
	  has_detail = 1
	  recycling_list.append(result.groups(0))
    if (has_detail):
      row['description'] = ''.join([row['description'], "<p><strong>Recycling facilities for:</strong> "])
      recycling_list.sort()
      for item in recycling_list:
        row['description'] = ''.join([row['description'], "%s, " % (item)])
      row['description'] = ''.join([row['description'], "</p>"])
    output = ''.join([output, generateKMLPlacemark(row, 'wasteRecyclingDepot')])

  # Get and process data for landfills
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[landuse=landfill][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_landuse_generic.xsl'
  features = {"landuse":"landfill"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Landfill site'
    output = ''.join([output, generateKMLPlacemark(row, "wasteLandfill")])
  output = ''.join([output, "</Document></kml>"])
  return output

def doTransport():
  """
    Create a KML feed for car clubs, cycle hire and train/tube/tram stations
  """
  # Set-up styles and header
  styles = {"transportCarshare":"http://tomchance.dev.openstreetmap.org/pois/transport_carsharing.png",
	    "transportCyclehire":"http://tomchance.dev.openstreetmap.org/pois/transport_cyclehire.png",
	    "transportTrain":"http://tomchance.dev.openstreetmap.org/pois/transport_train.png",
	    "transportDLR":"http://tomchance.dev.openstreetmap.org/pois/transport_train.png",
	    "transportTube":"http://tomchance.dev.openstreetmap.org/pois/transport_tube.png",
	    "transportTram":"http://tomchance.dev.openstreetmap.org/pois/transport_tram.png"}
  output = generateKMLHeader(styles,"Sustainable transport facilities in London")

  # Get and process data for car shares
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[amenity=car_sharing][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_amenity_generic.xsl'
  features = {"amenity":"car_sharing"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Car club parking bay'
    output = ''.join([output, generateKMLPlacemark(row, "transportCarshare")])

  # Get and process data for cycle hire docking stations
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[amenity=bicycle_rental][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_amenity_generic.xsl'
  features = {"amenity":"bicycle_rental"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['name'] == ''):
      row['name'] = 'Cycle hire docking bay'
    if (row['network'] == 'Barclays Cycle Hire'):
      row['name'] = ''.join(['TfL Cycle Hire: ', row['name']])
    if (row['capacity']):
      row['description'] = ''.join([row['description'], "<p><strong>Capacity:</strong> %s</p>" % (row['capacity'])])
    output = ''.join([output, generateKMLPlacemark(row, "transportCyclehire")])

  # Get and process data for railway stations
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/node[railway=station][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_amenity_generic.xsl'
  features = {"railway":"station"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    if (row['network'] == 'London Underground'):
      iconstyle = 'transportTube'
    elif (row['network'] == 'DLR'):
      iconstyle = 'transportDLR'
    else:
      iconstyle = 'transportTrain'
    output = ''.join([output, generateKMLPlacemark(row, iconstyle)])

  # Get and process data for tram stops
  xapi_url = 'http://xapi.openstreetmap.org/api/0.6/node[railway=tram_stop][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_amenity_generic.xsl'
  features = {"railway":"tram_stop"}
  poi_data = processRawData(xapi_url, xsl_uri, features)
  for row in poi_data:
    if (row['lat'] == None):
      continue
    output = ''.join([output, generateKMLPlacemark(row, "transportTram")])

  output = ''.join([output, "</Document></kml>"])
  return output


def doPower(uk):
  """
    Create a KML feed for power generators
  """
  # Set-up styles and header
  styles = {"powerSolar":"http://tomchance.dev.openstreetmap.org/pois/power_solar.png",
		"powerWind":"http://tomchance.dev.openstreetmap.org/pois/power_wind.png",
		"powerBiomass":"http://tomchance.dev.openstreetmap.org/pois/power_biomass.png",
		"powerGas":"http://tomchance.dev.openstreetmap.org/pois/power_gas.png",
		"powerGeothermal":"http://tomchance.dev.openstreetmap.org/pois/power_geothermal.png",
		"powerHydro":"http://tomchance.dev.openstreetmap.org/pois/power_hydro.png",
		"powerSea":"http://tomchance.dev.openstreetmap.org/pois/power_sea.png",
		"powerWaste":"http://tomchance.dev.openstreetmap.org/pois/power_waste.png",
		"powerDefault":"http://tomchance.dev.openstreetmap.org/pois/power_default.png"}
  if (uk == 1):
    output = generateKMLHeader(styles, "Low carbon power generators in the UK")
  else:
    output = generateKMLHeader(styles, "Low carbon power generators in London")

  # Get and process data for these features
  if (uk == 1):
    xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[power=generator][bbox=-6.5,49.68,2.67,61.31]'
  else:
    xapi_url = 'http://xapi.openstreetmap.org/api/0.6/*[power=generator][bbox=-0.51,51.20,0.35,51.80]'
  xsl_uri = 'trans_generators.xsl'
  features = {"power":"generator"}
  poi_data = processRawData(xapi_url, xsl_uri, features)

  for row in poi_data:
    if (row['lat'] == None):
      continue
    # Skip definitely-un-green sources
    if (row['source'] == 'nuclear' or row['source'] == 'coal'):
      continue
    # Start out with default assumptions
    gen_style = "powerDefault"
    gen_type = "Unknown power generator"
    # Solar panels, geothermal, hydro, tidal, wave or wind turbines? (easy cases)
    if (row['source'] == 'solar'):
      gen_style = "powerSolar"
      if (row['hot_water'] != ''):
        gen_type = "Solar thermal heating panel(s)"
      elif (row['electricity'] != '' and row['method'] == 'thermal'):
	gen_type = "Solar thermal electricity generator"
      elif (row['electricity'] != ''):
        gen_type = "Solar photovoltaic panel(s)"
    elif (row['source'] == 'geothermal'):
      gen_style = 'powerGeothermal'
      if (row['hot_water'] != ''):
        gen_type = "Geothermal heat pump"
      elif (row['electricity'] != ''):
	gen_type = "Geothermal electricity generator"
    elif (row['source'] == 'wind'):
      gen_type = "Wind turbine(s)"
      gen_style = "powerWind"
    elif (row['source'] == 'hydro'):
      gen_type = 'Hydro generator'
      gen_style = 'powerHydro'
    elif (row['source'] == 'tidal'):
      gen_type = 'Tidal generator'
      gen_style = 'powerSea'
    elif (row['source'] == 'wave'):
      gen_type = 'Wave generator'
      gen_style = 'powerSea'
    elif (row['source'] == 'osmotic'):
      gen_type = 'Osmotic generator'
      gen_style = 'powerSea'
    # OK, must be some sort of boiler/CHP/digester/etc.... type of fuel?
    elif (row['source'] == 'biomass'):
      gen_type = "Biomass "
      gen_style = "powerBiomass"
    elif (row['source'] == 'biofuel'):
      gen_type = 'Biofuel '
      gen_style = "powerBiomass"
    elif (row['source'] == 'biogas'):
      gen_type = 'Biogas '
      gen_style = "powerBiomass"
    elif (row['source'] == 'gas'):
      gen_type = 'Gas '
      gen_style = 'powerGas'
    elif (row['source'] == 'oil'):
      gen_type = 'Oil '
      gen_style = "powerDefault"
    elif (row['source'] == 'waste'):
      gen_type = 'Waste-to-energy '
      gen_style = 'powerWaste'
    # Right, means of generation... is it an advanced energy-to-waste plant?
    if (row['method'] == 'anaerobic_digestion'):
      gen_type = ''.join([gen_type, "anaerobic digester"])
    elif (row['method'] == 'pyrolysis'):
      gen_type = ''.join([gen_type, "pyrolising digester"])
    if (row['source'] in ["biomass", "biofuel", "biogas", "gas", "oil", "waste"]):
      # Or maybe just a boiler / stove?
      if (row['electricity'] == '' and (row['hot_water'] != '' or row['hot_air'] != '')):
        if (gen_type == 'Gas '):
	  continue # no interest in gas boilers
        elif (row['hot_water'] != ''):
  	  gen_type = ''.join([gen_type, "boiler"])
        elif (row['hot_air'] != ''):
	  gen_type = ''.join([gen_type, "stove"])
       # Or maybe a CHP/CCHP?
      elif (row['electricity'] != '' and row['cold_water'] == '' and (row['hot_water'] != '' or row['steam'] != '')):
        gen_type = ''.join([gen_type, "combined heat and power plant"])
      elif (row['electricity'] != '' and row['cold_water'] != '' and (row['hot_water'] != '' or row['steam'] != '')):
        gen_type = ''.join([gen_type, "combined heat, cooling and power plant"])
    # For now, skip unknown and fossil generators
    if (gen_type == "Unknown power generator" or gen_type == "Gas " or gen_type == "Oil "):
      continue
    # Description stuff?
    description = "No further details known"
    if (row['description']):
      description = row['description']
    rating = re.compile('\d')
    if (rating.match(row['electricity'])):
      description = ''.join([description, """<p><strong>Electrical rating:</strong> %s</p>""" % (row['electricity'])])
    if (rating.match(row['hot_water'])):
      description = ''.join([description, """<p><strong>Hot water rating:</strong> %s</p>""" % (row['hot_water'])])
    if (rating.match(row['steam'])):
      description = ''.join([description, """<p><strong>Steam rating:</strong> %s</p>""" % (row['steam'])])
    row['description'] = description
    row['name'] = gen_type
    output = ''.join([output, generateKMLPlacemark(row, gen_style)])

  output = ''.join([output, "</Document></kml>"])
  return output
  
if __name__=="__main__":
  c = doPower(0)
  f = open('../public_html/kml/power.kml', 'w')
  f.write(c.encode('utf-8'))
  f.close()
  c = doFood()
  f = open('../public_html/kml/food.kml', 'w')
  f.write(c.encode('utf-8'))
  f.close()
  c = doWaste()
  f = open('../public_html/kml/waste.kml', 'w')
  f.write(c.encode('utf-8'))
  f.close()
  c = doTransport()
  f = open('../public_html/kml/transport.kml', 'w')
  f.write(c.encode('utf-8'))
  f.close()
  c = doPower(1)
  f = open('../public_html/kml/power_uk.kml', 'w')
  f.write(c.encode('utf-8'))
  f.close()
