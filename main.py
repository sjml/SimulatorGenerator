import os
import ConfigParser
import urllib
from xml.dom import minidom
import json
import random

creds = ConfigParser.ConfigParser()
creds.read("credentials.ini")

cb_apiKey = creds.get("careerbuilder", "apikey")
params = {
	"DeveloperKey" : cb_apiKey,
	"HostSite" : "US",
	"OrderBy" : "Date",
}
cb_URL = "http://api.careerbuilder.com/v1/jobsearch?"
for key, value in params.iteritems():
	cb_URL += "%s=%s&" % (key, value)
cb_URL = cb_URL[:-1]

def getJobTitle():
	# TODO: store off the category, don't repeat job titles, rotate categories
	#   http://api.careerbuilder.com/CategoryCodes.aspx

	# dom = minidom.parse(urllib.urlopen(cb_URL))
	dom = minidom.parse(open("sample_jobsearch.xml"))
	jobs = []
	for node in dom.getElementsByTagName("JobTitle"):
		jobs.append(node.firstChild.nodeValue)
	return random.choice(jobs)

def getImageFor(searchTerm):
	is_URL = "https://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=%s" % (searchTerm)
	imageResults = json.load(urllib.urlopen(is_URL))
	# imageResults = json.load(open("sample_imagesearch.json"))
	largest = 0
	imgURL = ""
	for image in imageResults['responseData']['results']:
		pixelCount = int(image['width']) * int(image['height'])
		if (pixelCount > largest):
			imgURL = image['url']
			largest = pixelCount
	
	# TODO: deal with the image not being there

	localImgFile = "tmp/base_image"
	baseFile = open(localImgFile, 'wb')
	response = urllib.urlopen(imgURL)
	baseFile.write(response.read())
	baseFile.close()
	outputFile = "output.png"

	options = [
		("-size", "%w%h"),
		("-font", "'./helvetica-ultra-compressed.ttf'"),
		("-pointsize", "100"),
		("-fill", "white"),
		("-stroke", "gray",),
		("-gravity", "SouthEast"),
		("-interline-spacing", "15"),
		("-annotate", "0x10+20+20 '%s\nSimulator 2014'" % (searchTerm)),
	]
	exeLine = "convert %s %s %s" % (localImgFile, ''.join('%s %s ' % o for o in options), outputFile)
	print(exeLine)
	os.system(exeLine)
	os.system("rm %s" % (localImgFile))

job = getJobTitle()

image = getImageFor(job)

