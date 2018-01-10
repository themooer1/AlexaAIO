from hashlib import sha256
import AIO
import random
"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

# --------------- Miscellaneous Helpers ----------------------
default_session={"Radio":False,"Free":False}

def defaultSessionIfNotSet(session_attributes:dict):
    global default_session
    for key, value in default_session.items():
        if key not in session_attributes:
            #print(key+" not found!  Setting to "+str(value))
            session_attributes.update({key:value})
    #print(session_attributes)
    return session_attributes

def url2token(url:str):
    tokenGen=sha256()
    tokenGen.update(url.encode())
    return tokenGen.hexdigest()

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session,directive=None):
    resp={
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
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


def start_play_url_response(url:str,title="Playing", output="Now Playing", reprompt_text=None, should_end_session=True):
    token=url2token(url)
    return build_speechlet_response(title,output,reprompt_text,should_end_session,directive=build_audio_directive("Play", token, url))



def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    global default_session
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    latest=AIO.getRadioEpisodes()[0]

    session_attributes =default_session
    card_title = "Adventures in Odyssey"
    speech_output = "Welcome to Adventues in Odyssey. " \
                    "You can ask me to play an episode currently on the radio or a free episode from whitsend.org." \
                    "If you don't know the name of the episode you can ask - What's on the radio?" \
                    "Or just say - Play the latest episode." \
                    "If you just want to hear anything say - play anything, play whatever, or play a random episode." \
                    "The latest episode is episode {0}, {1}".format(latest['Number'],latest['Name'])
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "You can ask to play an episode by name, list available episodes, or play a random episode. "
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Farewell from Adventures in Odyssey"
    speech_output = None
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def handlePauseIntent(intent,session):
    return build_response(session['attributes'], build_speechlet_response("Pause", "Paused", None, True,directive=build_audio_stop_directive()))

def handleStopIntent(intent,session):
    return build_response(session['attributes'],build_speechlet_response("Stop","Stopping",None,True,directive=build_audio_stop_directive()))

def handleResumeIntent(intent,session):
    return build_response(session['attributes'],build_speechlet_response("ResumeNotImplemented","Unfortunately, the resume function is not yet implemented.","Just ask to play an episode by name or number.",False))

def handlePlayLatestIntent(intent, session):
    card_title="playLatestFailed"
    session_attributes=session['attributes']
    session_attributes=defaultSessionIfNotSet(session_attributes)
    should_end_session=True
    e=AIO.getRadioEpisodes()[0]
    session_attributes.update({'lastPlayed':e})
    return build_response(session_attributes,start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name']))

def handlePlayAnyIntent(intent, session):
    card_title="playAnyFailed"
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes=defaultSessionIfNotSet(session_attributes)
    should_end_session=True
    e=random.choice(AIO.getRadioEpisodes()+AIO.getFreeEpisodes())
    session_attributes.update({'lastPlayed':e})
    return build_response(session_attributes,start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name']))

def handlePlayByNumberIntent(intent, session):

    card_title="playByNumberFailed"
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    should_end_session = True


    if 'EpisodeNumber' in intent['slots']:
        episodeNumber = intent['slots']['EpisodeNumber']['value'].zfill(3)
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
            return build_response(session_attributes, start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name']))
        except TypeError as e:
            raise(e)
            speech_output = "I couldn't find episode {0} in {1}.".format(str(episodeNumber),"radio episodes" if session_attributes['Radio'] else "free episodes")
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False

    else:
        speech_output = "playByNumber was called, but no episode name was found. " \
                        "Please try again."
        reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handlePlayByNameIntent(intent, session):

    card_title="playByNameFailed"
    session_attributes=session['attributes']
    session_attributes=defaultSessionIfNotSet(session_attributes)
    should_end_session = True


    if 'EpisodeName' in intent['slots']:
        episodeName = intent['slots']['EpisodeName']['value']
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
            return build_response(session_attributes, start_play_url_response(e['url'],"Playing: "+e['Name'],"Now playing "+e['Name']))
        except TypeError as e:
            raise(e)
            speech_output = "I couldn't find episode {0} in {1}.".format(str(episodeName),"radio episodes" if session_attributes['Radio'] else "free episodes")
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False

    else:
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

def handleDescribeEpisodeIntent(intent, session):
    session_attributes = session['attributes'] if 'attributes' in session else {}
    session_attributes = defaultSessionIfNotSet(session_attributes)
    if 'EpisodeName' in intent['slots']:
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
            return build_response(session_attributes, build_speechlet_response("Description","{0}: {1}".format(e['Name'],e['Summary']),"You can ask to play this episode or play something else.",False))
        except TypeError as e:
            raise(e)
            speech_output = "I couldn't find episode {0}'s description in {1}.".format(str(episodeName),"radio episodes" if session_attributes['Radio'] else "free episodes")
            reprompt_text = "Please try again."
            session_attributes['Radio']=False
            session_attributes['Free']=False

    else:
        speech_output = "playByName was called, but no episode name was found. " \
                        "Please try again."
        reprompt_text = None

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))



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
    """ Called when the user specifies an intent for this skill """
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
    elif intent_name == "DescribeEpisodeIntent":
        return handleDescribeEpisodeIntent(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
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
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    #if (event['session']['application']['applicationId'] !=
    #         "amzn1.ask.skill.84156db1-d05b-4c44-8e27-c02e34b6157f"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

print("\n\n\n\n")