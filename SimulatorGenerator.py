#!/usr/bin/env python

# built-ins
import sys
import os
import ConfigParser
from xml.dom import minidom
import json
import random
import mimetypes
import time
import datetime
import subprocess
import re
import traceback
import pickle

# site packages
import requests
import twitter 

# local
sys.path.insert(0, "./lib")
import titlecase

# global constants
CONFIG_PATH = "config/config.ini"
CREDENTIALS_PATH = "config/credentials.ini"
TWITTERGC_PATH = "config/twitter_global_config.json"
TWITTER_STATUS_LIMIT = 140

# globals
config = ConfigParser.ConfigParser()
creds = ConfigParser.ConfigParser()
twitterApi = None
twitterGlobalConfig = None

def setup():
    global creds
    global config
    global twitterApi
    global twitterGlobalConfig

    random.seed()

    config.read(CONFIG_PATH)
    creds.read(CREDENTIALS_PATH)

    consumer_key = creds.get("twitter", "consumer_key")
    consumer_secret = creds.get("twitter", "consumer_secret")
    access_token = creds.get("twitter", "access_token")
    access_token_secret = creds.get("twitter", "access_token_secret")
    twitterApi = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret)

    oneDayAgo = time.time() - 60*60*24
    if (not os.path.exists(TWITTERGC_PATH) or os.path.getmtime(TWITTERGC_PATH) < oneDayAgo):
        print("Getting configuration data from Twitter.")
        twitterGlobalConfig = twitterApi.GetHelpConfiguration()
        with open(TWITTERGC_PATH, "w") as tgcFile:
            json.dump(twitterGlobalConfig, tgcFile)
    else:
        with open(TWITTERGC_PATH, "r") as tgcFile:
            twitterGlobalConfig = json.load(tgcFile)
    

def getRandomJobTitle():
    # TODO: store off the category, don't repeat job titles, rotate categories
    #   http://api.careerbuilder.com/CategoryCodes.aspx
    # TODO: Alternately, forget CareerBuilder and have this use BLS job titles.

    cb_apiKey = creds.get("careerbuilder", "apikey")
    js_params = {
        "DeveloperKey" : cb_apiKey,
        "HostSite" : "US",
        "OrderBy" : "Date",
    }
    cb_URL = "http://api.careerbuilder.com/v1/jobsearch?"

    if (config.get("services", "careerbuilder_live") == 1):
        response = requests.get(cb_URL, params=js_params)
        dom = minidom.parseString(response.content)
    else:
        with open("offline-samples/sample_jobsearch.xml") as jobFile:
            dom = minidom.parse(jobFile)

    jobs = []
    for node in dom.getElementsByTagName("JobTitle"):
        jobs.append(node.firstChild.nodeValue)

    # NOTE: in the year 10,000 AD, this will need to be updated
    maxLength = TWITTER_STATUS_LIMIT - (len(" Simulator ") + 4 + twitterGlobalConfig["characters_reserved_per_media"])
    job = ""
    count = 0
    while (len(job) == 0 or len(job) > maxLength):
        if (count >= 25):
            # buncha really long job titles up in here
            job = job[:maxLength-1] # (not great, but there are worse things)
            break
        job = random.choice(jobs)
        count += 1
    job = job.replace("'", "\\'").replace('"', '\\"')

    print("%i iteration(s) found random job title: %s" % (count, job))
    return job

def getImageFor(searchTerm):
    is_params = {
        "v" : "1.0", 
        "q" : searchTerm, 
        "imgType" : "photo",
        "imgsz" : "small|medium|large|xlarge|xxlarge|huge"
    }
    headers = {"Referer" : "https://twitter.com/SimGenerator"}
    is_URL = "https://ajax.googleapis.com/ajax/services/search/images"

    if (config.get("services", "googleimage_live") == 1):
        imageResults = requests.get(is_URL, params=is_params).json()
    else:
        with open("offline-samples/sample_imagesearch.json") as isFile:
            imageResults = json.load(isFile)

    if (imageResults == None or 'responseData' not in imageResults or imageResults['responseData'] == None):
        sys.stderr.write("No response data in image search for %s. JSON:\n%s\n" % (searchTerm, imageResults))
        return

    imageData = []
    for image in imageResults['responseData']['results']:
        imageData.append(
            {
                "url" : image['url'], 
                "h" : int(image['height']), 
                "w" : int(image['width']), 
                "size" : int(image['width']) * int(image['height'])
            }
        )
    imageData.sort(reverse=True, key=lambda img: img['size'])

    mimetypes.init()
    for img in imageData:
        try:
            r = requests.head(img['url'])
            if not r.ok:
                # can't download for whatever reason
                continue
        except:
            # requests library puked
            continue

        try:
            extension = mimetypes.guess_extension(r.headers['Content-Type'])
        except KeyError, e:
            sys.stderr.write("Couldn't find content-type header: %s" % str(r.headers))
            extension = ""
        if (extension == ".jpe") : extension = ".jpg"

        localFileName = "tmp/base_image-%s%s" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f"), extension)
        imgResponse = requests.get(img['url'])
        with open(localFileName, 'wb') as baseFile:
            baseFile.write(imgResponse.content)

        # check our work
        cmdLine = ['identify', '-format', '%wx%h', localFileName]
        dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
        dimensions = dimensionString.split("x")
        if (int(dimensions[0]) == img['w'] and int(dimensions[1]) == img['h']):
            return localFileName

def cap(value, maxVal):
    if (value < maxVal):
        return value
    else:
        return maxVal

def wpl(totalwords, current=None):
    if (current == None):
        current = []

    if (totalwords == 0):
        return current
    if (totalwords == 1):
        current.append(1)
        return current
    if (totalwords % 3 == 0):
        return current + [3]*(totalwords/3)
    current.append(2)
    return wpl(totalwords-2, current)

def createBoxArt(jobTitle, localImgFile, year):
    grav = random.choice(("NorthWest", "NorthEast", "SouthWest", "SouthEast"))
    if grav[-4:] == "West":
        align = "West"
    else:
        align = "East"

    wordlist = jobTitle.split()
    wordsPerLine = wpl(len(wordlist))
    jobTitle = ""
    indent = " "
    for wordCount in wordsPerLine:
        while wordCount > 0:
            jobTitle += wordlist.pop(0) + " "
            wordCount -= 1
        jobTitle += "\n"
        if (align == "West"):
            jobTitle += indent
            indent += " "

    # newlines to deal with the font overruning its rendering bounds; 
    #   we trim the canvas in imagemagick anyway
    jobTitle = "\n%sSimulator %i\n" % (jobTitle, year)

    cmdLine = ['identify', '-format', '%wx%h', localImgFile]
    try:
        dimensionString = subprocess.Popen(cmdLine, stdout=subprocess.PIPE).communicate()[0]
    except TypeError, e:
        sys.stderr.write("Couldn't get dimensions for %s\n" % localImgFile)
        return
    dimensions = map(int, dimensionString.split("x"))

    if (dimensions[0] > dimensions[1]):
        widthMultiplier = 0.65
    else:
        widthMultiplier = 0.95

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    outputFile = "tmp/output-%s.png" % timestamp
    offset = "+%i+%i" % (cap(dimensions[0] * .05, 20), cap(dimensions[1] * .05, 20))
    command = [
        "convert",

        # generate large text that we'll scale down to fit the target image later
        "-background", "none", 
        "-fill", "white",
        "-stroke", "gray",
        "-strokewidth", "3",
        "-kerning", "-5",
        "-font", "./data/helvetica-ultra-compressed.ttf",
        "-pointsize", "300",
        "-gravity", align,
        "-interline-spacing", "75",
        ("label:%s" % jobTitle).encode("utf8"),
        "-shear", "10x0", # since this font doesn't have true oblique / italics
        "-trim", # remove the extra space added by the newline wrapping

        # bring its size down so it can be overlaid into the base image
        "-resize", "%ix%i" % (dimensions[0] * widthMultiplier, dimensions[1] * .95),

        localImgFile, "+swap", # take everything we just created and make it
                               #  the thing that we're overlaying. localImgFile
                               #  becomes the target
        "-gravity", grav,
        "-geometry", offset,
        "-composite",
        "-resize", "%ix%i>" % (twitterGlobalConfig["photo_sizes"]["large"]["w"], twitterGlobalConfig["photo_sizes"]["large"]["h"]), 
        outputFile
    ]

    print("ImageMagick command: %s", " ".join(command))
    subprocess.call(command)
    os.rename(localImgFile, "archive/%s" % os.path.basename(localImgFile))
    return outputFile

def tweet(job, year, artFile, respondingTo=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    title = "%s Simulator %i" % (job, year)

    userName = None
    requestId = None
    if (respondingTo != None):
        userName = respondingTo[0]
        requestId = respondingTo[1]

    if (artFile != None and os.path.exists(artFile)):
        if (userName != None):
            title = "@%s %s" % (userName, title)
        if (config.get("services", "twitter_live") == 1):
            twitterApi.PostMedia(title, artFile, in_reply_to_status_id=requestId)
        else:
            print("Would have posted '%s' to twitter with image: %s" % (title, artFile))

        os.rename(artFile, "archive/image-%s.png" % timestamp)
        with open("archive/text-%s.txt" % timestamp, "w") as archFile:
            archFile.write(title.encode('utf8'))
    else:
        # don't tweet; something's wrong. 
        print("FAILURE: %s" % title.encode("utf8"))
        with open("archive/failed-%s.txt" % timestamp, "w") as archFile:
            archFile.write(title.encode('utf8'))

def checkTwitterLimits():
    rateLimitData = twitterApi.GetRateLimitStatus()

    rateLimitCallsLeft = rateLimitData['resources']['application']['/application/rate_limit_status']['remaining']
    rateLimitReset = rateLimitData['resources']['application']['/application/rate_limit_status']['reset']
    mentionsCallsLeft = rateLimitData['resources']['statuses']['/statuses/mentions_timeline']['remaining']
    mentionsReset = rateLimitData['resources']['statuses']['/statuses/mentions_timeline']['reset']

    print mentionsCallsLeft, "mentions calls left."


def manualJobTweet(job, year=None):
    job = titlecase.titlecase(job)
    image = getImageFor(job)
    if (year == None):
        year = random.randomint(2007, datetime.date.today().year)
    art = createBoxArt(job, image, year)
    tweet(job, year, art)

def randomJobTweet():
    job = getRandomJobTitle()
    image = getImageFor(job)
    year = random.randint(2007, datetime.date.today().year)
    art = createBoxArt(job, image, year)
    tweet(job, year, art)

def respondToRequests():
    if (config.get("settings", "taking_requests") == 0):
        print("Not taking requests.")
        return

    lastReply = 0
    lastReplyFile = "last_replied_to.txt"
    if (os.path.exists(lastReplyFile)):
        with open(lastReplyFile, "r") as lpf:
            lastReply = int(lpf.read())

    with open("data/badwords.json", "r") as badwordsFile:
        badwordsData = json.load(badwordsFile)
    badwords = badwordsData['badwords']

    requestRegex = re.compile('make one about ([^,\.\n@]*)', re.IGNORECASE)

    if (config.get("services", "twitter_live") == 1):
        mentions = twitterApi.GetMentions(since_id=lastReply)
    else:
        with open("offline-samples/twitter-mentions.pickle", "rb") as mentionArchive:
            mentions = pickle.load(mentionArchive)

    mentions.reverse() # look at the newest one last and hold our place there
    for status in mentions:
        result = requestRegex.search(status.text)
        if (result):
            job = result.groups()[0]
            # because regex is annoying
            if (job.lower().startswith("a ")):
                job = job[2:]
            elif (job.lower().startswith("an ")):
                job = job[3:]
            job = titlecase.titlecase(job)

            year = random.randint(2007, datetime.date.today().year)

            earlyOut = False
            # check for derogatory speech
            for word in job.split():
                if word in badwords:
                    earlyOut = True
                    break
            # see if we'll even be able to post back at them
            if len("@%s %s Simulator %i" % 
                    (status.user.screen_name, 
                     job, 
                     year)
                    ) + twitterGlobalConfig["characters_reserved_per_media"] > TWITTER_STATUS_LIMIT:
                earlyOut = True

            if earlyOut:
                # TODO: consider tweeting back "no" at them? 
                continue

            try:
                image = getImageFor(job)
                art = createBoxArt(job, image, year)
                tweet( job, year, art, (status.user.screen_name, str(status.id)) )
            except Exception, e:
                sys.stderr.write("Couldn't respond to request: %s\n" % status.text.encode("utf8"))
                traceback.print_exc(file=sys.stderr)
            finally:
                lastReply = status.id

    with open(lastReplyFile, "w") as f:
        f.write(str(lastReply))


if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath( __file__ ))
    os.chdir(base)
    
    setup()

    if (len(sys.argv) > 1 and sys.argv[1] == "check"):
        respondToRequests()
    else:
        randomJobTweet()

