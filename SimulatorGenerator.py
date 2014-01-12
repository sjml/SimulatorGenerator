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
import sqlite3

# site-packages
import requests

# global constants
BASE_PATH = os.path.dirname(os.path.abspath( __file__ ))
CONFIG_PATH = "config/config.ini"
CREDENTIALS_PATH = "config/credentials.ini"
TWITTERGC_PATH = "config/twitter_global_config.json"
PERSIST_PATH = "data/persistence.sqlite3"
TWITTER_RESOURCES = "statuses,help,application,friendships,account"

# local
sys.path.insert(0, os.path.join(BASE_PATH, "lib"))
import twitter 
import titlecase


# globals
config = ConfigParser.ConfigParser()
creds = ConfigParser.ConfigParser()
twitterApi = None
twitterGlobalConfig = None
persistenceConnection = None
persistence = None

def setup():
    global creds
    global config
    global twitterApi
    global twitterGlobalConfig
    global persistenceConnection
    global persistence

    random.seed()

    config.read(CONFIG_PATH)
    creds.read(CREDENTIALS_PATH)

    creatingDB = not os.path.exists(PERSIST_PATH)
    persistenceConnection = sqlite3.connect(PERSIST_PATH)
    persistence = persistenceConnection.cursor()
    if (creatingDB):
        persistence.execute("CREATE TABLE rateLimits (resource text unique, reset int, max int, remaining int)")
        persistence.execute("CREATE TABLE intPrefs (name text unique, value int)")
        persistence.execute("CREATE TABLE queuedRequests (tweet int unique, job text, user text)")
        persistence.execute("CREATE TABLE failedRequests (tweet int unique, job text, user text)")
        persistenceConnection.commit()

    if (config.getint("services", "twitter_live") == 1):
        consumer_key = creds.get("twitter", "consumer_key")
        consumer_secret = creds.get("twitter", "consumer_secret")
        access_token = creds.get("twitter", "access_token")
        access_token_secret = creds.get("twitter", "access_token_secret")
        twitterApi = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret)

        # global config data
        oneDayAgo = time.time() - 60*60*24
        if (not os.path.exists(TWITTERGC_PATH) or os.path.getmtime(TWITTERGC_PATH) < oneDayAgo):
            print("Getting configuration data from Twitter.")
            # not checking twitter rate limits here since it will only get called once per day
            twitterGlobalConfig = twitterApi.GetHelpConfiguration()
            with open(TWITTERGC_PATH, "w") as tgcFile:
                json.dump(twitterGlobalConfig, tgcFile)
        else:
            with open(TWITTERGC_PATH, "r") as tgcFile:
                twitterGlobalConfig = json.load(tgcFile)

        # install the rate limits
        if creatingDB:
            getTwitterRateLimits()
    else:
        # cached values will do in a pinch
        with open(TWITTERGC_PATH, "r") as tgcFile:
            twitterGlobalConfig = json.load(tgcFile)


def getTwitterRateLimits():
    persistence.execute("SELECT resource FROM rateLimits")
    existingResources = map(lambda x: x[0], persistence.fetchall())

    # not checking twitter rate limits here since it will only gets called when
    #  one of the limits is ready to reset
    limits = twitterApi.GetRateLimitStatus(TWITTER_RESOURCES)
    for resourceGroup, resources in limits["resources"].items():
        for resource, rateValues in resources.items():
            if resource not in existingResources:
                persistence.execute(
                    "INSERT INTO rateLimits VALUES (?, ?, ?, ?)",
                    [
                        resource,
                        int(rateValues["reset"]),
                        int(rateValues["limit"]),
                        int(rateValues["remaining"]),
                    ]
                )
            else:
                persistence.execute(
                    "UPDATE rateLimits SET reset=?, max=?, remaining=? WHERE resource=?", 
                    [
                        int(rateValues["reset"]),
                        int(rateValues["limit"]),
                        int(rateValues["remaining"]),
                        resource,
                    ]
                )
    persistenceConnection.commit()

    defaults = [
        ("tweetHourlyReset",     int(time.time()) + 60*60),
        ("tweetDailyReset",      int(time.time()) + 60*60*24),
        ("tweetHourlyRemaining", config.getint("services", "twitter_hourly_limit")),
        ("tweetDailyRemaining",  config.getint("services", "twitter_daily_limit")),
    ]
    for default in defaults:
        if getIntPref(default[0]) == -1:
            setIntPref(default[0], default[1])


def getIntPref(name):
    persistence.execute("SELECT value FROM intPrefs WHERE name=?", [name])
    pref = persistence.fetchone()
    if (pref == None):
        return -1
    return pref[0]


def setIntPref(name, value):
    if getIntPref(name) == -1:
        persistence.execute("INSERT INTO intPrefs VALUES (?, ?)", [name, value])
    else:
        persistence.execute("UPDATE intPrefs SET value=? WHERE name=?", [value, name])
    persistenceConnection.commit()


def checkTwitterPostLimit():
    currentTime = int(time.time())

    hourlyReset = getIntPref("tweetHourlyReset")
    if currentTime - hourlyReset > 0:
        setIntPref("tweetHourlyReset", currentTime + 60*60)
        setIntPref("tweetHourlyRemaining", config.getint("services", "twitter_hourly_limit"))
        hourly = config.getint("services", "twitter_hourly_limit")
    
    dailyReset = getIntPref("tweetDailyReset")
    if currentTime - dailyReset > 0:
        setIntPref("tweetDailyReset", currentTime + 60*60*24)
        setIntPref("tweetDailyRemaining", config.getint("services", "twitter_daily_limit"))
    
    hourly = getIntPref("tweetHourlyRemaining")
    daily = getIntPref("tweetDailyRemaining")

    if hourly > 0 and daily > 0:
        return True
    else:
        return False


def useTweet():
    for resource in ["tweetDailyRemaining", "tweetHourlyRemaining"]:
        setIntPref(resource, getIntPref(resource) - 1)


def checkTwitterResource(resourceKey, proposedUsage=1):
    persistence.execute("SELECT * FROM rateLimits WHERE resource=?", [resourceKey])
    resourceData = persistence.fetchone()
    if (resourceData == None):
        sys.stderr.write("Invalid Twitter resource: %s\n" % (resourceKey))
        return False

    if int(time.time()) - resourceData[1] > 0:
        getTwitterRateLimits()
        persistence.execute("SELECT * FROM rateLimits WHERE resource=?", [resourceKey])
        resourceData = persistence.fetchone()

    if (resourceData[3] - proposedUsage > 0):
        return True
    else:
        return False


def useTwitterResource(resourceKey, usage=1):
    persistence.execute("SELECT * FROM rateLimits WHERE resource=?", [resourceKey])
    resourceData = persistence.fetchone()
    if (resourceData == None):
        sys.stderr.write("Invalid Twitter resource: %s\n" % (resourceKey))
        return

    newVal = resourceData[3] - usage

    persistence.execute("UPDATE rateLimits SET reset=?, max=?, remaining=? WHERE resource=?",
        [
            resourceData[1],
            resourceData[2],
            newVal,
            resourceKey,
        ]
    )
    persistenceConnection.commit()

    return newVal


def shutdown():
    if (persistence != None):
        persistence.close()


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

    if (config.getint("services", "careerbuilder_live") == 1):
        response = requests.get(cb_URL, params=js_params)
        dom = minidom.parseString(response.content)
    else:
        with open("offline-samples/careerbuilder-jobsearch.xml") as jobFile:
            dom = minidom.parse(jobFile)

    jobs = []
    for node in dom.getElementsByTagName("JobTitle"):
        jobs.append(node.firstChild.nodeValue)

    # NOTE: in the year 10,000 AD, this will need to be updated
    maxLength = twitter.CHARACTER_LIMIT - (len(" Simulator ") + 4 + twitterGlobalConfig["characters_reserved_per_media"])
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
        "imgsz" : "small|medium|large|xlarge|xxlarge|huge",
        "rsz": 8,
        "safe" : config.get("services", "google_safesearch")
    }
    is_headers = {"Referer" : "https://twitter.com/SimGenerator"}
    is_URL = "https://ajax.googleapis.com/ajax/services/search/images"

    if (config.getint("services", "googleimage_live") == 1):
        imageResults = requests.get(is_URL, params=is_params, headers=is_headers).json()
    else:
        with open("offline-samples/googleimage-lpnsearch.json") as isFile:
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

    if (config.getint("settings", "log_imagemagick") == 1):
        print("ImageMagick command: %s" % " ".join(command))
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

        posting = True
        if   config.getint("services", "twitter_live") == 0:
            print("Twitter support is disabled; not posting.")
            posting = False
        elif config.getint("services", "actively_tweet") == 0:
            print("Tweeting is turned off; not posting.")
            posting = False
        elif not checkTwitterPostLimit():
            print("Over rate limit; not posting.")
            posting = False

        if posting:
            useTweet()
            print("Tweeting '%s' to Twitter with image: %s" % (title, artFile))
            twitterApi.PostMedia(title, artFile, in_reply_to_status_id=requestId)
        else:
            print("Would have posted '%s' to Twitter with image: %s" % (title, artFile))

        os.rename(artFile, "archive/output-%s.png" % timestamp)
        with open("archive/text-%s.txt" % timestamp, "w") as archFile:
            archFile.write(title.encode('utf8'))
    else:
        # don't tweet; something's wrong. 
        print("FAILURE: %s" % title.encode("utf8"))
        with open("archive/failed-%s.txt" % timestamp, "w") as archFile:
            archFile.write(title.encode('utf8'))



def manualJobTweet(job, year=None):
    job = titlecase.titlecase(job)
    image = getImageFor(job)
    if (year == None):
        year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
    art = createBoxArt(job, image, year)
    tweet(job, year, art)


def randomJobTweet():
    job = getRandomJobTitle()
    image = getImageFor(job)
    year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
    art = createBoxArt(job, image, year)
    tweet(job, year, art)


def respondToRequests():
    if (config.getint("settings", "taking_requests") == 0):
        print("Not taking requests.")
        return

    with open("data/badwords.json", "r") as badwordsFile:
        badwordsData = json.load(badwordsFile)
    badwords = badwordsData['badwords']
    with open("data/avoidphrases.json", "r") as avoidphrasesFile:
        avoidphrasesData = json.load(avoidphrasesFile)
    avoidphrases = avoidphrasesData['avoidphrases']

    requestRegex = re.compile('make one about ([^,\.\n@]*)', re.IGNORECASE)

    lastReply = getIntPref("lastReply")
    if (lastReply == -1):
        lastReply = 0
    if (config.getint("services", "twitter_live") == 1):
        if checkTwitterResource("/statuses/mentions_timeline"):
            mentions = twitterApi.GetMentions(count=100, since_id=lastReply)
            useTwitterResource("/statuses/mentions_timeline")
        else:
            print("Hit the mentions rate limit. Empty mentions.")
            mentions = []
    else:
        with open("offline-samples/twitter-mentions.pickle", "rb") as mentionArchive:
            mentions = pickle.load(mentionArchive)

    print("Processing %i mentions..." % (len(mentions)))
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

            earlyOut = False
            # don't accept links 
            #  (fine with it, but Twitter's aggressive URL parsing means it's
            #   unexpected behavior in many instances)
            if "http://" in job.lower():
                earlyOut = True
            # check for derogatory speech
            for word in job.lower().split():
                if word in badwords:
                    earlyOut = True
                    break
            # make sure nobody's trolling with shock sites or anything
            for phrase in avoidphrases:
                if phrase in job.lower():
                    earlyOut = True
                    break
            # see if we'll even be able to post back at them
            if len("@%s %s Simulator %i" % 
                    (status.user.screen_name, 
                     job, 
                     datetime.date.today().year)
                    ) + twitterGlobalConfig["characters_reserved_per_media"] > twitter.CHARACTER_LIMIT:
                earlyOut = True

            if earlyOut:
                # TODO: consider tweeting back "no" at them? 
                continue

            # put them in the queue
            try:
                persistence.execute("INSERT INTO queuedRequests VALUES (?, ?, ?)", [status.id, job, status.user.screen_name])
                persistenceConnection.commit()
            except sqlite3.IntegrityError:
                # already queued this tweet
                pass

        # even if we don't store it off, still mark the place here
        setIntPref("lastReply", status.id)


    # cycle through the queue
    print("Dequeueing %i request(s) from the backlog." % (config.getint("settings", "requests_per_run")))
    persistence.execute("SELECT * FROM queuedRequests LIMIT ?", [config.getint("settings", "requests_per_run")])
    artRequests = persistence.fetchall()
    for req in artRequests:
        tweetID = req[0]
        job = req[1]
        user = req[2]
        year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
        try:
            image = getImageFor(job)
            art = createBoxArt(job, image, year)
            tweet( job, year, art, (user, str(tweetID)) )
        except Exception, e:
            sys.stderr.write("Couldn't respond to request: '%s' from %s in %i\n" % 
                (
                    job.encode("utf8"),
                    user.encode("utf8"),
                    tweetID
                )
            )
            traceback.print_exc(file=sys.stderr)
            persistence.execute("INSERT INTO failedRequests VALUES (?, ?, ?)", 
                [
                    tweetID, job, user
                ]
            )
            persistenceConnection.commit()
        finally:
            persistence.execute("DELETE FROM queuedRequests WHERE tweet=?", [tweetID])
            persistenceConnection.commit()

    # update our count
    persistence.execute("SELECT COUNT(*) FROM queuedRequests")
    queueCount = persistence.fetchone()[0]
    setIntPref("queueCount", queueCount)
    print("Backlog is currently %i items." % (queueCount))


def updateQueue():
    # twitter documentation says this is rate-limited, doesn't appear
    #  to actually count against any resources. hmmmmm. 
    # resource should be "/account/update_profile", but that's not
    #  in the resource list at all. 
    locString = "Current queue: %i" % (getIntPref("queueCount"))
    if len(locString) > 30:
        locString = "Current queue: very, very long"
    twitterApi.UpdateProfile(location=locString)



if __name__ == '__main__':
    os.chdir(BASE_PATH)

    setup()

    if (config.getint("settings", "faking_requests") == 1 or (len(sys.argv) > 1 and sys.argv[1] == "check")):
        respondToRequests()
    elif (len(sys.argv) > 1 and sys.argv[1] == "updateQueue"):
        updateQueue()
    else:
        randomJobTweet()

    shutdown()
