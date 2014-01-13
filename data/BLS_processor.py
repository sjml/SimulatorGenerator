import os
import sys
from collections import OrderedDict

with open("bls_rawlist.txt", "r") as jobFile:
    rawJobs = map(str.rstrip, jobFile.readlines())
    rawJobsUnique = OrderedDict.fromkeys(rawJobs).keys()

def analyze():
    commacount = 0
    flscount = 0
    inccount = 0
    for job in rawJobsUnique:
        if ", " in job:
            print job
            commacount += 1
        if "First-Line Supervisors" in job:
            flscount += 1
        if "Including" in job:
            inccount += 1

    print "%i jobs with commas." % (commacount)
    print "%i jobs with fls." % (flscount)
    print "%i jobs with including." % (inccount)

def findInList(needle, haystack):
    count = 0
    for word in haystack:
        if needle in word:
            return count
        count += 1
    return None

jobs = []
for job in rawJobsUnique:
    # split on commas
    jobSplit = map(str.strip, job.split(","))
    if len(jobSplit) == 1:
        jobs.append(job)
        continue

    # <sigh> there are typos in this list
    jobSplit = filter(lambda x: len(x) > 0, jobSplit)

    # if any elements have "except", remove them and everything after
    index = findInList("Except", jobSplit)
    if index:
        jobSplit = jobSplit[:index]

    # if last element is "all other" or "first-line supervisor", discard
    if jobSplit[-1] == "All Other":
        jobSplit = jobSplit[:-1]
    if jobSplit[-1] == "First-Line Supervisors":
        jobSplit = jobSplit[:-1]

    # if last element starts with "and" -- break into separate jobs
    if jobSplit[-1].startswith("and "):
        jobSplit[-1] = jobSplit[-1][len("and "):]
        for j in jobSplit:
            jobs.append(j)
        continue

    # if last element is modifier that doesn't make sense to invert, drop it
    for badmod in ["Hand", "Miscellaneous", "Other", "General", ]:
        if jobSplit[-1] == badmod:
            jobSplit = jobSplit[:-1]

    modifiers = []
    # if any element contains "including" -- break into separate jobs
    index = findInList("Including", jobSplit)
    if index:
        modifiers = jobSplit[index:]
        modifiers[0] = modifiers[0][len("Including "):]
        jobSplit = jobSplit[:index]

    # invert remainder
    if (len(jobSplit) <= 2):
        if len(modifiers) > 0:
            for mod in modifiers:
                jobs.append("%s (%s)" % (' '.join(jobSplit), mod))
        else:
            jobs.append(' '.join(jobSplit))
        continue

    print jobSplit
    # break

    # add to list


## invert
# Accountants, Certified Public

## split out
# Actors, Producers, and Directors

## remove post except
# Administrative Assistants, Except Legal, Medical, and Executive

## remove All Other
# Administrative Support Workers, All Other

## remove FLS
# Administrative Support Workers, First-Line Supervisors

## just to make sure this double-and doesn't trip us up
# Agents and Business Managers of Artists, Performers, and Athletes

## remove except, THEN invert
# Agents, Purchasing, Except Wholesale, Retail, and Farm Products

## separate categories?
# Artists, Fine, Including Painters, Sculptors, and Illustrators

## wtf why -- ah, simple invert
# Boring Machine Tool Operators, Metal and Plastic
# Buffing Machine Tool Operators, Metal and Plastic
# Buffing Machine Tool Setters, Metal and Plastic
# Buffing Machine Tool Tenders, Metal and Plastic

### got down to Digitizers, Apparel Embroidery


# Handlers, Pesticide, Vegetation
# Drivers, Bus, Intercity
# Drivers, Bus, School or Special Client
# Drivers, Bus, Transit

# Repairers, Electronics, Powerhouse

# Representatives, Sales, Wholesale and Manufacturing, Except Technical and Scientific Products
# Representatives, Sales, Wholesale and Manufacturing, Technical and Scientific Products
