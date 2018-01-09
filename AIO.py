import requests
from random import choice
import re

radioURL="http://www.aiowiki.com/audioplayer/data/radio.php"
freeURL="http://www.aiowiki.com/audioplayer/data/free.php"
podcastURL="http://www.aiowiki.com/audioplayer/data/podcast.php"

months = {"January":"01","February":"02","March":"03","April":"04","May":"05","June":"06","July":"07","August":"08","September":"09","October":"10","November":"11","December":"12"}


class InvalidDateException(Exception):
    pass

def transformDate(date):
    global months
    parts=date.split(" ")
    if parts[0] in months.keys():
        month=months[parts[0]]
    else:
        raise(InvalidDateException(parts[0]+" is not a valid month"))
    year=parts[2]
    day=parts[1].strip(",")
    return year+month+day.zfill(2)

def dateValue(date):
    if ',' in date:
        date=transformDate(date)
    return int(date)

def makeRadioURL(date):
    urlbase="http://media.focusonthefamily.com/fotf/mp3/aio/"
    urltip="aio_{0}.mp3".format(date)
    if requests.get(urlbase+urltip,timeout=2,stream=True).status_code==200:
        return urlbase+urltip
    else:
        return urlbase+urltip.replace("aio","aiow")


def getRadioEpisodes()->list:
    global radioURL
    e = requests.get(radioURL,timeout=1).json()
    for i in e['Episodes']:
        e['Episodes'][e['Episodes'].index(i)]['url']=makeRadioURL(transformDate(e['Episodes'][e['Episodes'].index(i)]['Date']))
    e['Episodes']=sorted(e['Episodes'],key=lambda x:dateValue(x['Date']),reverse=True)
    return e['Episodes']

def getFreeEpisodes()->list:
    global freeURL
    e=requests.get(freeURL,timeout=2).json()['Episodes']
    for episode in e:
        e[e.index(episode)]['Summary']=stringChoice(episode['Summary'])
    return e

def stringChoice(string):
    choiceRegex="\[\[.*?\]\]"
    choices=re.findall(choiceRegex,string)
    for c in choices:
        string=string.replace(c,choice(c.strip("[").strip("]").split("|")))
    return string

def getRadioEpisodeByName(name):
    candidates = list(filter(lambda x: fuzzyMatch(x['Name'], name), getRadioEpisodes()))
    return candidates[0] if len(candidates) > 0 else None

def getFreeEpisodeByName(name):
    candidates=list(filter(lambda x:fuzzyMatch(x['Name'],name),getFreeEpisodes()))
    return candidates[0] if len(candidates)>0 else None

def getRadioEpisodeByNumber(episodeNumber):
    candidates=list(filter(lambda x: x['Number']==episodeNumber, getRadioEpisodes()))
    return candidates[0] if len(candidates) > 0 else None

def getFreeEpisodeByNumber(episodeNumber):
    candidates=list(filter(lambda x: x['Number']==episodeNumber, getFreeEpisodes()))
    return candidates[0] if len(candidates) > 0 else None

def fuzzyMatch(string1, string2):
    replacements={"1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine","gonna":"going to"}
    whiteout='.,"\'!?/$()'
    string1=string1.strip().lower()
    string2 = string2.strip().lower()
    for num, word in replacements.items():
        string1=string1.replace(num,word)
        string2 = string2.replace(num, word)
    for char in whiteout:
        string1 = string1.replace(char,"")
        string2 = string2.replace(char,"")
    return string1==string2


#print(stringChoice("blah blah blah [[me|you]] candle brick sandwich. Summary information [[this|that]][[who|what]]in the world."))
#print(list(map(lambda x:x['URL'],getRadioEpisodes()['Episodes'])))
#print(getFreeEpisodes())
#print(getFreeEpisodeByName("Youre Not going to believe this!!!"))