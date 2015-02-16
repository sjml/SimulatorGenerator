#!/usr/bin/env python

# built-ins
import sys
import os
import ConfigParser
from xml.dom import minidom
import json
import random
import time
import datetime
import re
import traceback
import pickle
import sqlite3
import tempfile
import urllib

# site-packages
import requests
import prettytable
import inflection

# global constants
BASE_PATH = os.path.dirname(os.path.abspath( __file__ ))
CONFIG_PATH = os.path.join("config", "config.ini")
CREDENTIALS_PATH = os.path.join("config", "credentials.ini")
TWITTERGC_PATH = os.path.join("config", "twitter_global_config.json")
PERSIST_PATH = os.path.join("data", "persistence.sqlite3")
TWITTER_RESOURCES = "statuses,help,application,account,trends"
INNOCENCE_PATH = "http://bot-innocence.herokuapp.com/muted"

# local
sys.path.insert(0, os.path.join(BASE_PATH, "lib"))
import twitter 
import titlecase

# package
import SimulatorGeneratorImage


# globals
config = None
creds = None
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

    os.chdir(BASE_PATH)

    random.seed()

    for crucial in (CONFIG_PATH, CREDENTIALS_PATH):
        if not os.path.exists(crucial):
            sys.stderr.write("Couldn't load %s; exiting.\n" % (crucial))
    config = ConfigParser.ConfigParser()
    creds = ConfigParser.ConfigParser()
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

    if resourceData == None or int(time.time()) - resourceData[1] > 0:
        getTwitterRateLimits()
        persistence.execute("SELECT * FROM rateLimits WHERE resource=?", [resourceKey])
        resourceData = persistence.fetchone()
        if (resourceData == None):
            sys.stderr.write("Invalid Twitter resource: %s\n" % (resourceKey))
            return False

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


def getTrends():
    location = config.getint("services", "twitter_trends_woeid")
    trends = []
    if (checkTwitterResource("/trends/place")):
        trendsRaw = twitterApi.GetTrendsWoeid(location)
        useTwitterResource("/trends/place")
        for t in trendsRaw:
            trends.append(t.name)

    response = urllib.urlopen(INNOCENCE_PATH)
    if response.getcode() == 200:
        mutedTopics = json.loads(response.read())
        trends = filter(lambda x: x not in mutedTopics, trends)

    return trends


def shutdown():
    if (persistence != None):
        persistence.close()


def getRandomCBJobTitle():
    # TODO: store off the category, don't repeat job titles, rotate categories
    #   http://api.careerbuilder.com/CategoryCodes.aspx

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
        with open(os.path.join("offline-samples", "careerbuilder-jobsearch.xml")) as jobFile:
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


def getRandomBLSJobTitle():
    with open(os.path.join("data", "bls", "bls_normalized.txt")) as jobList:
        jobs = map(str.rstrip, jobList.readlines())

    job = ""
    # NOTE: in the year 10,000 AD, this will need to be updated
    maxLength = twitter.CHARACTER_LIMIT - (len(" Simulator ") + 4 + twitterGlobalConfig["characters_reserved_per_media"])
    while (len(job) == 0 or len(job) > maxLength):
        job = random.choice(jobs)
    job = job.replace("'", "\\'").replace('"', '\\"')
    return job


def tweet(job, year, artFile, respondingTo=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    title = "%s Simulator %i" % (job, year)

    userName = None
    requestId = None
    if (respondingTo != None):
        userName = respondingTo[0]
        requestId = respondingTo[1]

    if not os.path.exists("archive"):
        os.makedirs("archive")
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
            print("Tweeting '%s' to Twitter with image: %s" % (title.encode("utf8"), artFile))
            twitterApi.PostMedia(title, artFile, in_reply_to_status_id=requestId)
        else:
            print("Would have posted '%s' to Twitter with image: %s" % (title.encode("utf8"), artFile))

        os.rename(artFile, os.path.join("archive", "output-%s.png" % timestamp))
        with open(os.path.join("archive", "text-%s.txt" % timestamp), "w") as archFile:
            archFile.write(title.encode('utf8'))
    else:
        # don't tweet; something's wrong. 
        sys.stderr.write("FAILURE: %s\n" % title.encode("utf8"))
        with open(os.path.join("archive", "failed-%s.txt" % timestamp), "w") as archFile:
            archFile.write(title.encode('utf8'))



def manualJobTweet(job, year=None):
    image = SimulatorGeneratorImage.getImageFor(
        job, 
        safeSearchLevel=config.get("services", "google_safesearch"), 
        referer="http://twitter.com/SimGenerator"
    )

    if (year == None):
        year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
    artFile = "output-%s.png" % datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    artFile = os.path.join(tempfile.gettempdir(), artFile)
    SimulatorGeneratorImage.createBoxArt(
        job, 
        year, 
        image,
        artFile,
        maxSize=(
            str(twitterGlobalConfig["photo_sizes"]["large"]["w"] - 1),
            str(twitterGlobalConfig["photo_sizes"]["large"]["h"] - 1),
        ),
        deleteInputFile=True
    )
    tweet(titlecase.titlecase(job), year, artFile)


def randomJobTweet(source="BLS"):
    if source == "BLS":
        job = getRandomBLSJobTitle()
    elif source == "CB":
        job = getRandomCBJobTitle()

    image = SimulatorGeneratorImage.getImageFor(
        job,
        safeSearchLevel=config.get("services", "google_safesearch"), 
        referer="http://twitter.com/SimGenerator"
    )
    year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
    artFile = "output-%s.png" % datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    artFile = os.path.join(tempfile.gettempdir(), artFile)
    SimulatorGeneratorImage.createBoxArt(
        job, 
        year, 
        image,
        artFile,
        maxSize=(
            str(twitterGlobalConfig["photo_sizes"]["large"]["w"] - 1),
            str(twitterGlobalConfig["photo_sizes"]["large"]["h"] - 1),
        ),
        deleteInputFile=True
    )
    tweet(titlecase.titlecase(job), year, artFile)


def queueMentions():
    if (config.getint("settings", "taking_requests") == 0):
        print("Not taking requests.")
    else:
        filterPath = os.path.join("data", "filters")
        badWords = []
        for filterFile in os.listdir(filterPath):
            if filterFile[0] == ".":
                continue
            fp = os.path.join(filterPath, filterFile)
            with open(fp, "r") as f:
                loaded = json.load(f)
                badWords += loaded['badwords']
        print badWords

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
            with open(os.path.join("offline-samples", "twitter-mentions.pickle"), "rb") as mentionArchive:
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
                jobCheck = job.lower()
                # don't accept links 
                #  (fine with it, but Twitter's aggressive URL parsing means it's
                #   unexpected behavior in many instances)
                if "http://" in jobCheck:
                    earlyOut = True
                # check for derogatory speech, shock sites, etc.
                for phrase in badWords:
                    if phrase in jobCheck:
                        earlyOut = True
                        break
                # see if we'll even be able to post back at them
                if len("@%s %s Simulator %i" % 
                        (status.user.screen_name, 
                         job, 
                         datetime.date.today().year)
                        ) + twitterGlobalConfig["characters_reserved_per_media"] > twitter.CHARACTER_LIMIT:
                    earlyOut = True
                # don't let people crowd the queue
                persistence.execute("SELECT user FROM queuedRequests")
                existingUsers = map(lambda x: x[0], persistence.fetchall())
                if status.user.screen_name in existingUsers:
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


def fulfillQueue():
    # cycle through the queue
    if (config.getint("settings", "making_requests") == 0):
        print("Not automatically fulfilling requests.")
    else:
        print("Dequeueing %i request(s) from the backlog." % (config.getint("settings", "requests_per_run")))
        persistence.execute("SELECT * FROM queuedRequests LIMIT ?", [config.getint("settings", "requests_per_run")])
        artRequests = persistence.fetchall()
        for req in artRequests:
            takeSpecificRequest(data=req)


def printQueue():
    persistence.execute("SELECT * FROM queuedRequests")
    tab = prettytable.from_db_cursor(persistence)
    print(tab)


def deleteRequest(tweetID=None):
    if tweetID == None:
        sys.stderr.write("No tweet ID provided. :-/\n")
        return
    persistence.execute("DELETE FROM queuedRequests WHERE tweet=?", [tweetID])
    persistenceConnection.commit()
    printQueue()


def takeSpecificRequest(tweetID=None, data=None):
    if (tweetID != None and type(tweetID) == int):
        persistence.execute("SELECT * FROM queuedRequests WHERE tweet=?", [tweetID])
        req = persistence.fetchone()
        if req == None:
            print "Tweet not queued."
            return
    elif (data != None and type(data) == tuple and len(data) >= 3):
        req = data
    else:
        print type(data)
        sys.stderr.write("Need to pass either tweet ID or data to this function.\n")
        return

    tweetID = req[0]
    job = req[1]
    user = req[2]
    try:
        image = SimulatorGeneratorImage.getImageFor(
            job,
            safeSearchLevel=config.get("services", "google_safesearch"), 
            referer="http://twitter.com/SimGenerator"
        )
        year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
        artFile = "output-%s.png" % datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
        artFile = os.path.join(tempfile.gettempdir(), artFile)
        SimulatorGeneratorImage.createBoxArt(
            job, 
            year, 
            image,
            artFile,
            maxSize=(
                str(twitterGlobalConfig["photo_sizes"]["large"]["w"] - 1),
                str(twitterGlobalConfig["photo_sizes"]["large"]["h"] - 1),
            ),
            deleteInputFile=True
        )
        tweet( titlecase.titlecase(job), year, artFile, (user, str(tweetID)) )
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

    printQueue()



def updateQueue():
    # twitter documentation says this is rate-limited, doesn't appear
    #  to actually count against any resources. hmmmmm. 
    # resource should be "/account/update_profile", but that's not
    #  in the resource list at all. 
    persistence.execute("SELECT COUNT(*) FROM queuedRequests")
    queueCount = persistence.fetchone()[0]
    setIntPref("queueCount", queueCount)
    print("Backlog is currently %i items." % (queueCount))
    locString = "Request queue: %i" % queueCount
    if len(locString) > 30:
        locString = "Request queue: very, very long"
    if queueCount == 0:
        locString = "Request queue: EMPTY!"
    twitterApi.UpdateProfile(location=locString)


def randomTrendTweet():
    trends = getTrends()
    if len(trends) == 0:
        sys.stderr.write("Couldn't get any trending topics. :-/\n")
        return
    trend = random.choice(trends)
    if trend[0] == "#":
        text = trend[1:]
        text = inflection.titleize(text)
        text = titlecase.titlecase(text)
    else:
        text = trend
    image = SimulatorGeneratorImage.getImageFor(
        text,
        safeSearchLevel=config.get("services", "google_safesearch"), 
        referer="http://twitter.com/SimGenerator"
    )
    year = random.randint(config.getint("settings", "minyear"), datetime.date.today().year)
    artFile = "output-%s.png" % datetime.datetime.now().strftime("%Y-%m-%d-%H%M.%f")
    artFile = os.path.join(tempfile.gettempdir(), artFile)
    SimulatorGeneratorImage.createBoxArt(
        text, 
        year, 
        image,
        artFile,
        maxSize=(
            str(twitterGlobalConfig["photo_sizes"]["large"]["w"] - 1),
            str(twitterGlobalConfig["photo_sizes"]["large"]["h"] - 1),
        ),
        deleteInputFile=True
    )
    tweetString = text
    if trend[0] == "#":
        tweetString = trend + " " + tweetString

    tweet(tweetString, year, artFile)


if __name__ == '__main__':
    setup()

    if (config.getint("settings", "faking_requests") == 1 or (len(sys.argv) > 1 and sys.argv[1] == "check")):
        queueMentions()
    elif (len(sys.argv) > 1 and sys.argv[1] == "fulfill"):
        fulfillQueue()
    elif (len(sys.argv) > 1 and sys.argv[1] == "updateQueue"):
        updateQueue()
    elif (len(sys.argv) > 2 and sys.argv[1] == "take"):
        takeSpecificRequest(tweetID=int(sys.argv[2]))
    elif (len(sys.argv) > 2 and sys.argv[1] == "del"):
        deleteRequest(tweetID=int(sys.argv[2]))
    elif (len(sys.argv) > 1 and sys.argv[1] == "pq"):
        printQueue()
    elif (len(sys.argv) > 1 and sys.argv[1] == "trend"):
        randomTrendTweet()
    elif (len(sys.argv) > 1 and sys.argv[1] == "cb"):
        randomJobTweet(source="CB")
    else:
        randomJobTweet(source="BLS")

    shutdown()
