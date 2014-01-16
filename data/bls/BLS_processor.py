import os
import sys
import re
import inspect
import inflection
from collections import OrderedDict

with open("bls_rawlist.txt", "r") as jobFile:
    rawJobs = map(str.rstrip, jobFile.readlines())
    rawJobsUnique = OrderedDict.fromkeys(rawJobs).keys()


def findInList(needle, haystack):
    count = 0
    for searchString in haystack:
        if needle in searchString:
            return count
        count += 1
    return None

def lineNum():
    return inspect.currentframe().f_back.f_lineno

jobs = []
lastMods = {}
checkString = "Design"

with open("bls_filter_simple_join.txt", "r") as f:
    filterSimpleJoin = map(str.rstrip, f.readlines())
with open("bls_filter_last_word_mod.txt", "r") as f:
    filterLastWordMod = map(str.rstrip, f.readlines())
with open("bls_filter_commutative_mod.txt", "r") as f:
    filterCommutativeMod = map(str.rstrip, f.readlines())
with open("bls_filter_things_of.txt", "r") as f:
    filterThingsOf = map(str.rstrip, f.readlines())
with open("bls_filter_last_two_words_mod.txt", "r") as f:
    filterLastTwoWordsMod = map(str.rstrip, f.readlines())
with open("bls_filter_first_word_mod.txt", "r") as f:
    filterFirstWordMod = map(str.rstrip, f.readlines())
with open("bls_filter_remainder.txt", "r") as f:
    filterRemainder = map(str.rstrip, f.readlines())
with open("bls_filter_and_split.txt", "r") as f:
    filterAndSplit = map(str.rstrip, f.readlines())
with open("bls_filter_last_word_mod_simple.txt", "r") as f:
    filterLastWordModSimple = map(str.rstrip, f.readlines())
with open("bls_filter_leave_it.txt", "r") as f:
    filterLeaveIt = map(str.rstrip, f.readlines())
with open("bls_filter_first_word_mod_simple.txt", "r") as f:
    filterFirstWordModSimple = map(str.rstrip, f.readlines())
with open("bls_filter_last_two_words_mod_simple.txt", "r") as f:
    filterLastTwoWordsModSimple = map(str.rstrip, f.readlines())
with open("bls_filter_first_two_words_mod_simple.txt", "r") as f:
    filterFirstTwoWordsModSimple = map(str.rstrip, f.readlines())

# good to have a single place to debug
def addJob(jobString, raw, context):
    if len(jobString) > 0:
        jobs.append(jobString)

for job in rawJobsUnique:
    # split on commas
    jobSplit = map(str.strip, job.split(","))

    # <sigh> there are typos in this list
    jobSplit = filter(lambda x: len(x) > 0, jobSplit)

    # no commas!
    if len(jobSplit) == 1:
        if " and " in jobSplit[0]:
            if jobSplit[0].startswith("Other ") or jobSplit[0].startswith("First-Line Supervisors") or jobSplit[0].startswith("Supervisors"):
                continue
            if str(jobSplit) in filterAndSplit:
                split = jobSplit[0].split(" and ")
                for s in split:
                    addJob(s, job, lineNum())
                continue
            if str(jobSplit) in filterLastWordModSimple:
                lastSplit = jobSplit[-1].split()
                mod = lastSplit[-1]
                jobSplit[-1] = jobSplit[-1][:-(len(mod)+1)]
                for j in jobSplit[0].split(" and "):
                    jobString = "%s %s" % (j, mod)
                    addJob(j, job, lineNum())
                continue
            if str(jobSplit) in filterLeaveIt:
                addJob(jobSplit[0], job, lineNum())
                continue
            if str(jobSplit) in filterFirstWordModSimple:
                andSplit = jobSplit[0].split(" and ")
                mod = andSplit[0].split()[0]
                andSplit[0] = andSplit[0][len(mod)+1:]
                for a in andSplit:
                    jobString = "%s %s" % (mod, a)
                    addJob(jobString, job, lineNum())
                continue
            if jobSplit[0].endswith("Operators and Tenders"):
                jobSplit[0] = jobSplit[0][:-(len("Operators and Tenders"))]
                addJob("%s%s" % (jobSplit[0], "Operators"), job, lineNum())
                addJob("%s%s" % (jobSplit[0], "Tenders"), job, lineNum())
                continue
            if str(jobSplit) in filterLastTwoWordsModSimple:
                lastSplit = jobSplit[-1].split()
                mod = ' '.join(lastSplit[-2:])
                jobSplit[-1] = jobSplit[-1][:-(len(mod)+1)]
                for j in jobSplit[0].split(" and "):
                    jobString = "%s %s" % (j, mod)
                    addJob(j, job, lineNum())
                continue
            if jobSplit[0].endswith("Installers and Repairers"):
                jobSplit[0] = jobSplit[0][:-(len("Installers and Repairers"))]
                addJob("%s%s" % (jobSplit[0], "Installers"), job, lineNum())
                addJob("%s%s" % (jobSplit[0], "Repairers"), job, lineNum())
                continue
            if str(jobSplit) in filterFirstTwoWordsModSimple:
                andSplit = jobSplit[0].split(" and ")
                mod = ' '.join(andSplit[0].split()[:2])
                jobSplit[0] = jobSplit[0][len(mod)+1:]
                andSplit[0] = andSplit[0][len(mod)+1:]
                for a in andSplit:
                    jobString = "%s %s" % (mod, a)
                    addJob(jobString, job, lineNum())
                continue
            # alas, fuggit
            addJob(jobSplit[0], job, lineNum())
        else:
            addJob(job, job, lineNum())
        continue

    # if any elements have "except", remove them and everything after
    index = findInList("Except", jobSplit)
    if index != None:
        jobSplit = jobSplit[:index]

    # if last element is "all other", discard
    if jobSplit[-1] == "All Other":
        jobSplit.pop(-1)

    # ugh, supervisors 
    # TODO: restore these into the list
    if jobSplit[-1] == "First-Line Supervisors":
        jobSplit.pop(-1)

    if (jobSplit[-1].endswith("and Tenders")):
        if (jobSplit[-1] == "and Tenders"):
            jobTypes = ["Tenders"]
            jobSplit.pop(-1)
        elif (jobSplit[-1].endswith("Operators and Tenders")):
            jobTypes = ["Operators", "Tenders"]
            jobSplit[-1] = jobSplit[-1][:-len(" Operators and Tenders")]
        if (jobSplit[-1] == "Operators"):
            jobTypes.append("Operators")
            jobSplit.pop(-1)
        if (jobSplit[-1].endswith("Setters")):
            jobSplit[-1] = jobSplit[-1][:-len(" Setters")]
            jobTypes.append("Setters")
        for jobType in jobTypes:
            jobString = "%s %s" % (', '.join(jobSplit), jobType)
            addJob(jobString, job, lineNum())
        continue

    # I don't like this, but there's no good pattern to these
    if jobSplit[-1].startswith("and "):
        jstr = str(jobSplit)
        if (jstr in filterSimpleJoin):
            jobSplit[-1] = jobSplit[-1][len("and "):]
            for j in jobSplit:
                addJob(j, job, lineNum())
            continue
        if (jstr in filterLastWordMod):
            jobSplit[-1] = jobSplit[-1][len("and "):]
            lastSplit = jobSplit[-1].split()
            mod = lastSplit.pop(-1)
            jobSplit.pop(-1)
            jobSplit += lastSplit
            for j in jobSplit:
                jobString = "%s %s" % (j, mod)
                addJob(jobString, job, lineNum())
            continue
        if (jstr in filterCommutativeMod):
            firstSplit = jobSplit[0].split()
            mod = ' '.join(firstSplit[:-1])
            jobSplit[0] = firstSplit[-1]
            jobSplit[-1] = jobSplit[-1][len(" and"):]
            for j in jobSplit:
                jobString = "%s %s" % (mod, j)
                addJob(jobString, job, lineNum())
            continue
        if (jstr in filterThingsOf):
            firstSplit = jobSplit[0].split(" of ")
            jobSplit[0] = firstSplit[1]
            lmod = firstSplit[0]
            jobSplit[-1] = jobSplit[-1][len(" and"):]
            lastSplit = jobSplit[-1].split()
            if (len(lastSplit) > 1):
                rmod = lastSplit.pop(-1)
            else:
                rmod = ""
            for j in jobSplit:
                jobString = "%s of %s %s" % (lmod, j, rmod)
                jobString = jobString.rstrip()
                addJob(jobString, job, lineNum())
            continue
        if (jstr in filterLastTwoWordsMod):
            jobSplit[-1] = jobSplit[-1][len("and "):]
            lastSplit = jobSplit[-1].split()
            mod = ' '.join(lastSplit[-2:])
            jobSplit[-1] = jobSplit[-1][:-(len(mod)+1)]
            for j in jobSplit:
                jobString = "%s %s" % (j, mod)
                addJob(jobString, job, lineNum())
            continue
        hvacFound = findInList("(HVAC)", jobSplit)
        if hvacFound != None:
            hvac = "Heating, Ventilation, and Air Conditioning (HVAC)"
            if not jobSplit[hvacFound].endswith("(HVAC)"):
                hvacJob = jobSplit[hvacFound].split("(HVAC)")[1].strip()
                if (jobSplit[0] != "Heating"):
                    hvacJob += " " + jobSplit[0]
                jobString = "%s %s" % (hvac, hvacJob)
            else:
                jobString = "%s %s" % (hvac, jobSplit[0])
            addJob(jobString, job, lineNum())
            continue
        if (jstr in filterFirstWordMod):
            incIndex = findInList("Including", jobSplit)
            if (incIndex != None):
                jobSplit = jobSplit[incIndex:]
                jobSplit[0] = jobSplit[0][len("Including "):]
                if (jobSplit[-1].startswith("and ")):
                    jobSplit[-1] = jobSplit[-1][len("and "):]
                for j in jobSplit:
                    addJob(j, job, lineNum())
                continue
            andFound = None
            for i in range(len(jobSplit)):
                if jobSplit[i].startswith("and "):
                    andFound = i
                    break
            if andFound != len(jobSplit)-1:
                mods = []
                for j in jobSplit[:andFound+1]:
                    mods.append(j)
                if mods[-1].startswith("and "):
                    mods[-1] = mods[-1][len("and "):]
                lmSplit = mods[-1].split()
                localMod = lmSplit[-1]
                mods = ["%s %s" % (s, localMod) for s in mods]
                jobSplit = jobSplit[andFound+1:]
            else:
                mods = [jobSplit.pop(0)]
            if (jobSplit[-1].startswith("and ")):
                jobSplit[-1] = jobSplit[-1][len("and "):]
                if jobSplit[-1].startswith("Related"):
                    jobSplit.pop(-1)
            for j in jobSplit:
                for m in mods:
                    jobString = "%s %s" % (j, m)
                    addJob(jobString, job, lineNum())
            continue
        cbrnIndex = findInList("(CBRN)", jobSplit)
        if (cbrnIndex != None):
            jobString = "Chemical, Biological, Radiological, and Nuclear (CBRN) Officers"
            addJob(jobString, job, lineNum())
            continue
        if jobSplit[0].startswith("Helpers--"):
            jobSplit[0] = jobSplit[0][len("Helpers--"):]
            jobSplit[-1] = jobSplit[-1][len("and "):]
            for j in jobSplit:
                addJob(j, job, lineNum())
            continue

        # fuck it, not contriving any more patterns. special case these last few
        if str(jobSplit) in filterRemainder:
            if jobSplit[0].startswith("Butchers"):
                addJob("Butchers", job, lineNum())
                addJob("Meat Processing Workers", job, lineNum())
                addJob("Poultry Processing Workers", job, lineNum())
                addJob("Fish Processing Workers", job, lineNum())
                continue
            if jobSplit[0] == "Carpet":
                addJob("Carpet Installers", job, lineNum())
                addJob("Carpet Finishers", job, lineNum())
                addJob("Floor Installers", job, lineNum())
                addJob("Floor Finishers", job, lineNum())
                addJob("Tile Installers", job, lineNum())
                addJob("Tile Finishers", job, lineNum())
                continue
            if jobSplit[0] == "Electric Motor":
                addJob("Electric Motor Repairers", job, lineNum())
                addJob("Power Tool Repairers", job, lineNum())
                continue
            if jobSplit[0] == "Farm":
                addJob("Farmworkers", job, lineNum())
                addJob("Ranch Farmworkers", job, lineNum())
                addJob("Aquacultural Farmworkers", job, lineNum())
                continue
            if jobSplit[0] == "Industrial":
                addJob("Industrial Machinery Installation Workers", job, lineNum())
                addJob("Industrial Machinery Repair Workers", job, lineNum())
                addJob("Industrial Machinery Maintenance Workers", job, lineNum())
                continue
            if jobSplit[0] == "Meat":
                addJob("Meat Cutters and Trimmers", job, lineNum())
                addJob("Poultry Cutters and Trimmers", job, lineNum())
                addJob("Fish Cutters and Trimmers", job, lineNum())
                continue
            if jobSplit[0] == "Metal Furnace Operators":
                addJob("Metal Furnace Operators", job, lineNum())
                addJob("Metal Furnace Tenders", job, lineNum())
                addJob("Metal Furnace Pourers", job, lineNum())
                addJob("Metal Furnace Casters", job, lineNum())
                continue
            if jobSplit[0] == "Radio":
                addJob("Radio Tower Equipment Installers", job, lineNum())
                addJob("Radio Tower Equipment Repairers", job, lineNum())
                addJob("Cellular Tower Equipment Repairers", job, lineNum())
                addJob("Cellular Tower Equipment Repairers", job, lineNum())
                continue
            if jobSplit[0] == "Television":
                addJob("Television Camera Operators", job, lineNum())
                addJob("Television Camera Editors", job, lineNum())
                addJob("Video Camera Operators", job, lineNum())
                addJob("Video Camera Editors", job, lineNum())
                addJob("Motion Picture Camera Operators", job, lineNum())
                addJob("Motion Picture Camera Editors", job, lineNum())
                continue
            else:
                addJob("Vehicle Mechanics", job, lineNum())
                addJob("Vehicle Installers", job, lineNum())
                addJob("Vehicle Repairers", job, lineNum())
                addJob("Mobile Equipment Mechanics", job, lineNum())
                addJob("Mobile Equipment Installers", job, lineNum())
                addJob("Mobile Equipment Repairers", job, lineNum())
                continue

    # if last element is modifier that doesn't make sense to invert, drop it
    for badmod in ["Hand", "Miscellaneous", "Other", "General", ]:
        if jobSplit[-1] == badmod:
            jobSplit.pop(-1)

    modifiers = []
    # if any element contains "including" -- break into separate jobs
    index = findInList("Including", jobSplit)
    if index != None:
        modifiers = jobSplit[index:]
        modifiers[0] = modifiers[0][len("Including "):]
        jobSplit = jobSplit[:index]

    # invert remainder
    if (len(jobSplit) <= 2):
        if len(modifiers) > 0:
            for mod in modifiers:
                jobString = "%s (%s)" % (' '.join(jobSplit), mod)
                addJob(jobString, job, lineNum())
        else:
            jobSplit.reverse()
            jobString = ' '.join(jobSplit)
            addJob(jobString, job, lineNum())
        continue

    # special cases
    if (jobSplit[-1] == "Postsecondary"):
        jobSplit.pop(-1)
        if (jobSplit[-1].endswith("Teachers") and jobSplit[-1].startswith("and ")):
            jobSplit[-1] = jobSplit[-1][:-len(" Teachers")]
            jobSplit.insert(0, "Teachers")

        jobTitle = jobSplit[0]
        jobSplit.pop(0)
        jobString = "%s %s %s" % (
            "Postsecondary",
            ' '.join(jobSplit),
            "Teachers",
        )

        addJob(jobString, job, lineNum())
        continue

    materials = (
        "Metal and Plastic", 
        "Synthetic and Glass Fibers", 
        "Wood", 
        "Plastics", 
        "Food and Tobacco"
    )
    matIndex = findInList(jobSplit[-1], materials)
    if (matIndex != None):
        jobSplit = map(lambda x: re.sub("Operator$", "Operators", x), jobSplit)
        material = materials[matIndex]
        setIndex = findInList("Setters", jobSplit)
        opIndex = findInList("Operators", jobSplit)
        tendIndex = findInList("and Tenders", jobSplit)
        if (opIndex != None and opIndex == tendIndex):
            jobSplit.insert(0, jobSplit.pop(-1))
            jobString = ', '.join(jobSplit)
            addJob(jobString, job, lineNum())
            continue
        if (setIndex != None and opIndex != None and tendIndex != None):
            jobSplit[setIndex] = jobSplit[setIndex][:-len(" Setters")]
            jobSplit.pop(tendIndex)
            jobSplit.pop(opIndex)

            # oddball
            remainingSetIndex = findInList("Setters", jobSplit)
            if remainingSetIndex != None:
                jobSplit[remainingSetIndex] = jobSplit[remainingSetIndex][:-len(" Setters")]
            jobSplit = filter(lambda x: len(x) > 0, jobSplit)

            jobSplit.pop(-1)
            for jobTitle in ("Setters", "Operators", "Tenders"):
                jobString = "%s %s %s" % (
                    material,
                    ', '.join(jobSplit),
                    jobTitle
                )
                addJob(jobString, job, lineNum())
            continue

        jobSplit.pop(-1)
        jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.insert(0, material)
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if (jobSplit[0] == "Operators"):
        jobSplit.pop(0)
        jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.append("Operators")
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if (jobSplit[0] == "Repairers"):
        jobSplit.pop(0)
        if jobSplit[0] == "Electronic Equipment":
            jobSplit.insert(1, "for")
        jobSplit.append("Repairers")
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if (jobSplit[0] == "Installers"):
        jobSplit.pop(0)
        if jobSplit[0] == "Electronic Equipment":
            jobSplit.insert(1, "for")
        jobSplit.append("Installers")
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if (jobSplit[0] == "Teachers"):
        jobSplit.pop(0)
        if (jobSplit[0] == "Career/Technical Education" or 
            jobSplit[0] == "Special Education"):
            jobSplit.insert(0, jobSplit.pop(-1))
        jobSplit.append("Teachers")
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if (jobSplit[0] == "Drivers"):
        jobSplit.pop(0)
        jobSplit.insert(0, jobSplit.pop(1))
        jobSplit.append("Drivers")
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue


    if (jobSplit[-1].startswith("and ")):
        jobString = ', '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    if jobSplit[0] == "Sales Representatives":
        jobSplit.pop(0)
        jobSplit.insert(0, "Sales")
        jobSplit.insert(0, "Representatives")

    if jobSplit[0] == "Representatives":
        selling = []
        if len(jobSplit) > 3:
            selling = jobSplit[3:]
            jobSplit = jobSplit[:3]
        jobSplit.reverse()
        if len(selling) > 0:
            jobSplit.append("for")
            jobSplit.append(' '.join(selling))
        jobString = ' '.join(jobSplit)
        addJob(jobString, job, lineNum())
        continue

    # hmmm, this feels someone defending a very specific job...
    if jobSplit[-1].endswith("Enhanced Operators/Maintainers"):
        jobSplit[-1] = jobSplit[-1][:-len(" Enhanced Operators/Maintainers")]
        jobString = "%s for %s" % (
            "Enhanced Operators/Maintainers",
            ', '.join(jobSplit)
        )
        addJob(jobString, job, lineNum())
        continue

    # if there's still an "and" in the last element, assume an Oxford comma was dropped
    #  and pick it up
    if " and " in jobSplit[-1]:
        last = jobSplit.pop(-1)
        jobSplit = jobSplit + map(str.strip, last.split(" and "))
        for j in jobSplit:
            addJob(j, job, lineNum())
        continue

    # if there's an "and" in the penultimate slot, the last word is a modifier
    if jobSplit[-2].startswith("and "):
        mod = jobSplit.pop(-1)
        jobSplit[-1] = jobSplit[-1][len("and "):]
        firstSplit = jobSplit[0].split()
        if len(firstSplit) > 1:
            mod += " " + firstSplit[0]
            jobSplit[0] = ' '.join(firstSplit[1:])
        for j in jobSplit:
            jobString = "%s %s" % (mod, j)
            addJob(jobString, job, lineNum())
        continue

    # finally down to some simple inversions
    jobSplit.reverse()
    jobString = ' '.join(jobSplit)
    addJob(jobString, job, lineNum())


# unique-ify
jobs = list(set(jobs))
jobs.sort()

# singularize
for j in range(len(jobs)):
    jobSplit = jobs[j].split(" ")
    for i in range(len(jobSplit)):
        jobSplit[i] = inflection.singularize(jobSplit[i])
    jobs[j] = " ".join(jobSplit)

with open("bls_normalized.txt", "w") as normalizedFile:
    normalizedFile.write('\n'.join(jobs))
