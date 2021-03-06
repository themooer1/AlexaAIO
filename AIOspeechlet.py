from hashlib import sha256
from AIO import AIO
import random
import boto3
import decimal
import time

REGION_NAME = "us-east-1"
SESSION_TABLE_NAME = "AlexaAIOSession"
PAUSE_EXPIRE_DAYS = 10

"""
This skill can play episodes of Adventures in Odyssey from their online radio broadcast, and free episodes available on their website.
"""

# --------------- Miscellaneous Helpers ----------------------
default_session = {"Radio": False, "Free": False}


def defaultSessionIfNotSet(session_attributes:dict):
    """Returns a session with default information for this skill if session_attributes is empty."""
    global default_session
    for key, value in default_session.items():
        if key not in session_attributes:
            #print(key+" not found!  Setting to "+str(value))
            session_attributes.update({key:value})
    #print(session_attributes)
    return session_attributes


def url2token(url:str):
    """SHA256 hash the url of the mp3 file."""
    tokenGen=sha256()
    tokenGen.update(url.encode())
    return tokenGen.hexdigest()


def savePlaybackOffset(userId, audioToken, offset:int):
    """Writes the current playback timestamp to the DynamoDB table with the name stored in const SESSION_TABLE_NAME."""
    global REGION_NAME, SESSION_TABLE_NAME
    conn=boto3.resource('dynamodb',region_name=REGION_NAME)
    table=conn.Table(SESSION_TABLE_NAME)
    resp = table.update_item(Key={"userId":userId}, UpdateExpression="set audioOffset=:o, lastUpdated=:l", ExpressionAttributeValues={":l":int(time.time())+86400*PAUSE_EXPIRE_DAYS, ":o": offset}, ReturnValues="UPDATED_NEW")


def saveLastPlaying(userId,audioToken,url:str):
    """Writes the currently playing episode to the DynamoDB table with the name stored in const SESSION_TABLE_NAME."""
    global REGION_NAME, SESSION_TABLE_NAME
    conn = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = conn.Table(SESSION_TABLE_NAME)
    resp = table.update_item(Key={"userId": userId}, UpdateExpression="set lastUpdated=:l,audioOffset=:o,audioToken=:t,audioURL=:u", ExpressionAttributeValues={":l":int(time.time())+86400*PAUSE_EXPIRE_DAYS, ":o": 0, ":t": audioToken, ":u": url}, ReturnValues="UPDATED_NEW")


def getLastPlaying(userId):
    """Takes the amazon userId from a user object.  Returns a dict with keys {audioOffset, audioToken(see url2Token), audioURL, lastUpdated}"""
    global REGION_NAME, SESSION_TABLE_NAME
    conn = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = conn.Table(SESSION_TABLE_NAME)
    resp = table.get_item(Key={"userId": userId})
    if 'Item' not in resp:
        return None
    else:
        return convertAllDecToInt(resp['Item'])


def convertAllDecToInt(item):
    """Converts dynamoDB results of type decimal, which are nested in dicts, lists and sets to the python int primitive."""
    if type(item)==dict:
        i = item.copy()
        for key, value in item.items():
            if type(value)==decimal.Decimal:
                i[key]=int(value)
    elif type(item) in (list, set):
        i = item.copy()
        for j in range(0,len(i)-1):
            if type(item[j])==decimal.Decimal:
                i[j]=int(item[j])
    else:
        raise ValueError("Only works on dicts and lists")
    return i



# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session,directive=None):
    resp={
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'directives': [],
        'shouldEndSession': should_end_session
    }
    if directive:
        resp['directives'].append(directive)
    else:
        resp.pop('directives',None)
    return resp


def build_audio_directive(audioFunction: str, token: str, url:str, offset=0, playBehavior="REPLACE_ALL"):
    """Builds an audio response with the given audiofunction (Play, Pause, etc.), Unique token, url and offset=0"""
    if audioFunction not in {"Play","Stop","ClearQueue"}: return build_speechlet_response("Unsupported audio directive "+audioFunction, "Unsupported audio directive "+audioFunction+" was prevented from executing.", None, True)
    return {'type': "AudioPlayer."+audioFunction,
             'playBehavior': playBehavior,
             'audioItem': {
                 'stream': {
                     'token': token,
                     'url': url,
                     'offsetInMilliseconds': offset
                 }
                }
             }

def build_audio_control_directive(audioFunction:str):
    return {
        'outputSpeech': {},
        'card': {},
        'reprompt': {},
        'directives': [
            {'type': "AudioPlayer." + audioFunction}
        ],
        'shouldEndSession': True
    }

def build_audio_stop_directive(messageID:str=str(random.random()),dialogID:str=str(random.random())):
    return {
        "header": {
            "namespace": "AudioPlayer",
            "name": "Stop",
            "messageId": messageID,
            "dialogRequestId": dialogID
        },
        "payload": {
        }
    }


def start_play_url_response(url:str, title="Playing", output="Now Playing", reprompt_text=None, should_end_session=True, offset=0, **kwargs):
    session = kwargs['session'] if 'session' in kwargs else None
    token=url2token(url)
    if session:
        print("Saving Session")
        saveLastPlaying(session['user']['userId'], token, url)
    return build_speechlet_response(title, output, reprompt_text,should_end_session, directive=build_audio_directive("Play", token, url, offset))



def build_response(session_attributes, speechlet_response):
    """The outer layer of the JSON response sent to Alexa."""
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------
# Note: Each of these functions has been named to match the intent which it handles.

def get_welcome_response():
    global default_session

    # Initialize the session.
    session_attributes = default_session

    # Get the first episode
    latest = AIO.getRadioEpisodes()[0]

    card_title = "Adventures in Odyssey"
    speech_output = "Welcome to Adventues in Odyssey.  " \
                    "The latest episode is episode {0}, {1}.".format(latest['Number'],latest['Name']) +\
                    "  What would you like to do?"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "You can ask to play an episode by name, list available episodes, or play a random episode. "
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    """Returns a response that says nothing and closes the skill."""
    card_title = "Farewell from Adventures in Odyssey"
    speech_output = ""
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def handlePauseIntent(intent,session):
    return {"response": {"shouldEndSession": True, "directives": [{"type": "AudioPlayer.Stop"}]}, "version": "1.0"}

def handleStopIntent(intent,session):
    return handle_session_end_request()

def handleResumeIntent(intent,session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    lp=getLastPlaying(session['user']['userId'])
    if lp == None:
        return build_response(session_attributes,build_speechlet_response("None Resumed",random.choice(["I couldn't find an episode to resume.","I can't seem to find what you were listening to.","I don't see any episode previously playing."])+"  What would you like me to play?","You can ask me to play another episode.  For example: Alexa, play Happy Hunting.",False))
    e=AIO.getEpisodeByUrl(lp['audioURL'])
    return build_response(session_attributes,start_play_url_response(e['url'], "Resuming: " + e['Name'], "Resuming " + e['Name'],offset=lp['audioOffset']))

def handlePlayLatestIntent(intent, session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    should_end_session=True
    e=AIO.getRadioEpisodes()[0]
    session_attributes.update({'lastPlayed':e})
    return build_response(session_attributes,start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name'],session=session))

def handlePlayAnyIntent(intent, session):
    card_title="Play Random Episode Failed"
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes=defaultSessionIfNotSet(session_attributes)
    should_end_session=True
    e=random.choice(AIO.getRadioEpisodes()+AIO.getFreeEpisodes())
    session_attributes.update({'lastPlayed':e})
    return build_response(session_attributes,start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name'],session=session))

def handlePlayByNumberIntent(intent, session):

    card_title="Play Episode {} Failed"
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    should_end_session = True


    if 'EpisodeNumber' in intent['slots'] and 'value' in intent['slots']['EpisodeNumber']:
        episodeNumber = intent['slots']['EpisodeNumber']['value'].zfill(3)
        card_title=card_title.format(str(episodeNumber))
        try:
            if session_attributes['Radio'] and not session_attributes['Free']:
                print("Radio")
                session_attributes['Radio']=False
                e=AIO.getRadioEpisodeByNumber(episodeNumber)
                session_attributes.update({'lastPlayed': e})
            elif session_attributes['Free'] and not session_attributes['Radio']:
                print("Free")
                e = AIO.getFreeEpisodeByNumber(episodeNumber)
                session_attributes['Free'] = False
                session_attributes.update({'lastPlayed': e})
            else:
                print("Searching Radio")
                e = AIO.getRadioEpisodeByNumber(episodeNumber)
                if not e:
                    print("Searching Free")
                    e = AIO.getFreeEpisodeByNumber(episodeNumber)
            return build_response(session_attributes, start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name'],session=session))
        except TypeError as e:
            speech_output = "I couldn't find episode {0} in {1}.".format(str(episodeNumber),"radio episodes" if session_attributes['Radio'] else "free episodes")
            if not session_attributes['Radio'] and session_attributes['Free']:
                speech_output = "I couldn't find episode {0}.".format(str(episodeNumber))
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False

    else:
        card_title=card_title.format("")
        speech_output = "No episode with that number was found. " \
                        "Please try again."
        reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handlePlayByNameIntent(intent, session):
    card_title = "Play Episode: {} Failed"
    session_attributes=session['attributes']
    session_attributes=defaultSessionIfNotSet(session_attributes)
    should_end_session = True


    if 'EpisodeName' in intent['slots'] and 'value' in intent['slots']['EpisodeName']:
        episodeName = intent['slots']['EpisodeName']['value']
        card_title = card_title.format(str(episodeName))
        #print(episodeName)
        #print(type(episodeName))
        try:
            if session_attributes['Radio'] and not session_attributes['Free']:
                print("Radio")
                e = AIO.getRadioEpisodeByName(episodeName)
                session_attributes.update({'lastPlayed':e})
                session_attributes['Radio']=False
            elif session_attributes['Free'] and not session_attributes['Radio']:
                print("Free")
                e = AIO.getFreeEpisodeByName(episodeName)
                session_attributes.update({'lastPlayed': e})
                session_attributes['Free'] = False
            else:
                print("Searching Radio")
                e = AIO.getRadioEpisodeByName(episodeName)
                if not e:
                    print("Searching Free")
                    e = AIO.getFreeEpisodeByName(episodeName)
            return build_response(session_attributes, start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name'], session=session))
        except ValueError as e:
            speech_output = "I couldn't find episode {0} in {1}.".format(str(episodeName),"radio episodes" if session_attributes['Radio'] else "free episodes")
            if not session_attributes['Radio'] and session_attributes['Free']:
                speech_output = "I couldn't find episode {0}.".format(str(episodeName))
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False

    else:
        card_title = card_title.format("")
        speech_output = "playByName was called, but no episode name was found. " \
                        "Please try again."
        reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handleListRadioIntent(intent, session):
    session_attributes=session['attributes']
    session_attributes['Radio']=True
    speech_output = "I found the currently airing episodes.  Interrupt me when you hear one you want to play, and say the name of the episode.  " + ".  ".join(["Episode {0}.  ".format(ep['Number'])+ep['Name'] for ep in AIO.getRadioEpisodes()])
    reprompt_text = "Which episode do you want to play?  You can ask for a description, say the name of the episode, or say the number. "
    return build_response(session_attributes,build_speechlet_response("Currently Airing",speech_output,reprompt_text,False))


def handleListFreeIntent(intent, session):
    session_attributes = session['attributes']
    session_attributes['Free']=True
    speech_output = "I found some free episodes.  Interrupt me when you hear one you want to play, and say the name of the episode.    " + ".  ".join(["Episode {0}.  ".format(ep['Number'])+ep['Name'] for ep in AIO.getFreeEpisodes()])
    reprompt_text = "Which episode do you want to play?  You can ask for a description, say the name of the episode, or say the number. "
    return build_response(session_attributes,build_speechlet_response("Free Episodes", speech_output, reprompt_text, False))


def handleDescribeEpisodeByNameIntent(intent, session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    if 'EpisodeName' in intent['slots'] and 'value' in intent['slots']['EpisodeName']:
        episodeName = intent['slots']['EpisodeName']['value']
        try:
            if session_attributes['Radio'] and not session_attributes['Free']:
                print("Radio")
                e = AIO.getRadioEpisodeByName(episodeName)
                session_attributes['Radio']=False
            elif session_attributes['Free'] and not session_attributes['Radio']:
                print("Free")
                e = AIO.getFreeEpisodeByName(episodeName)
                session_attributes['Free'] = False
            else:
                print("Searching Radio")
                e = AIO.getRadioEpisodeByName(episodeName)
                if not e:
                    print("Searching Free")
                    e = AIO.getFreeEpisodeByName(episodeName)
            return build_response(session_attributes, build_speechlet_response("Description","{0}: {1}".format(e['Name'],e['Summary']),"You can ask to play this episode or play something else.",True))
        except TypeError as e:
            speech_output = "I couldn't find episode {0}'s description in {1}.".format(str(episodeName),"radio episodes" if session_attributes['Radio'] else "free episodes")
            if not session_attributes['Radio'] and session_attributes['Free']:
                speech_output = "I couldn't find episode {0}'s description.".format(str(episodeName))
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False
    else:
        speech_output = "I didn't catch the episode you wanted to know more about.  " \
                        "Can you tell me again?"
        reprompt_text = None
    return build_response(session_attributes, build_speechlet_response("Describe Episode: Name Not Heard", speech_output, reprompt_text, False))


def handleDescribeEpisodeByNumberIntent(intent, session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    if 'EpisodeNumber' in intent['slots'] and 'value' in intent['slots']['EpisodeNumber']:
        episodeNumber = intent['slots']['EpisodeNumber']['value']
        try:
            if session_attributes['Radio'] and not session_attributes['Free']:
                print("Radio")
                e = AIO.getRadioEpisodeByNumber(episodeNumber)
                session_attributes['Radio'] = False
            elif session_attributes['Free'] and not session_attributes['Radio']:
                print("Free")
                e = AIO.getFreeEpisodeByNumber(episodeNumber)
                session_attributes['Free'] = False
            else:
                print("Searching Radio")
                e = AIO.getRadioEpisodeByNumber(episodeNumber)
                if not e:
                    print("Searching Free")
                    e = AIO.getFreeEpisodeByNumber(episodeNumber)
            return build_response(session_attributes, build_speechlet_response("Description","{0}: {1}".format(e['Name'],e['Summary']),"You can ask to play this episode or play something else.",True))
        except TypeError as e:
            speech_output = "I couldn't find episode {0}'s description in {1}.".format(str(episodeNumber),"radio episodes" if session_attributes['Radio'] else "free episodes")
            if not session_attributes['Radio'] and session_attributes['Free']:
                speech_output = "I couldn't find episode {0}'s description.".format(str(episodeNumber))
            reprompt_text = "Please try again."
            session_attributes['Radio'] = False
            session_attributes['Free'] = False
    else:
        speech_output = "I didn't hear the number of the episode you wanted to know more about.  " \
                        "Can you say that again?"
        reprompt_text = None
    return build_response(session_attributes, build_speechlet_response("Describe Episode: Number Not Heard", speech_output, reprompt_text, True))


def handleHelpIntent(intent, session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    speech_output = "You can ask me to play an episode currently on the radio or a free episode from whitsend.org." \
    "  If you don't know the name of the episode you can ask - What's on the radio?" \
    "   Or just say - Play the latest episode." \
    "  If you just want to hear anything say - play anything, play whatever, or play a random episode." \
    "  What would you like me to play?"
    reprompt_text = None
    return build_response(session_attributes,build_speechlet_response("Help",speech_output,reprompt_text,False))

        # --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    if not 'attributes' in session:
        session['attributes']={}

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill.  Chooses an intent handler to call.  Link new intents here."""
    if 'attributes' not in session:
        session['attributes']={}
    session['attributes'] = defaultSessionIfNotSet(session['attributes'])

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "PlayByNumberIntent":
        return handlePlayByNumberIntent(intent, session)
    elif intent_name == "PlayByNameIntent":
        return handlePlayByNameIntent(intent, session)
    elif intent_name == "PlayLatestIntent":
        return handlePlayLatestIntent(intent, session)
    elif intent_name == "PlayAnyIntent":
        return handlePlayAnyIntent(intent, session)
    elif intent_name == "ListRadioIntent":
        return handleListRadioIntent(intent, session)
    elif intent_name == "ListFreeIntent":
        return handleListFreeIntent(intent, session)
    elif intent_name == "DescribeEpisodeByNameIntent":
        return handleDescribeEpisodeByNameIntent(intent, session)
    elif intent_name == "DescribeEpisodeByNumberIntent":
        return handleDescribeEpisodeByNumberIntent(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return handleHelpIntent(intent, session)
    elif intent_name == "AMAZON.PauseIntent":
        return handlePauseIntent(intent,session)
    elif intent_name == "AMAZON.ResumeIntent":
        return handleResumeIntent(intent,session)
    elif intent_name == "AMAZON.StopIntent":
        return handleStopIntent(intent,session)
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    #Respond to special requests

    if event['request']['type'] == "AudioPlayer.PlaybackStopped":
        return savePlaybackOffset(event['context']['System']['user']['userId'], event['request']['token'], event['request']['offsetInMilliseconds'])

    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    if (event['session']['application']['applicationId'] !=
             "amzn1.ask.skill.84156db1-d05b-4c44-8e27-c02e34b6157f"):
         raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

print("\n\n")

# e=random.choice(AIO.getRadioEpisodes())
# saveLastPlaying("user3",url2token(e['url']),e['url'])
# savePlaybackOffset("user3",url2token(e['url']),56)
# lp=getLastPlaying("user3")
# assert lp['audioURL']==e['url']
# assert lp['audioOffset']==56
# assert lp['audioToken']==url2token(e['url'])