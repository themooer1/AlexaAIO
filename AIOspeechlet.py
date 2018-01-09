from hashlib import sha256
import AIO
"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""


# --------------- Helpers that build all of the responses ----------------------

default_session={"Radio":False,"Free":False}

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
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
        'shouldEndSession': should_end_session
    }

def build_audio_response(audioFunction: str, token: str, url:str, offset):
    """Builds an audio response with the given audiofunction (Play, Pause, etc.), Unique token, url and offset"""
    if audioFunction not in {"Play","Stop","ClearQueue"}: return build_speechlet_response("Unsupported audio directive "+audioFunction, "Unsupported audio directive "+audioFunction+" was prevented from executing.", None, True)
    return {
        'outputSpeech': {},
        'card': {},
        'reprompt': {},
        'directives': [
            {'type': "AudioPlayer."+audioFunction,
             'playBehavior': "string",
             'audioItem': {
                 'stream': {
                     'token': "string",
                     'url': "string",
                     'offsetInMilliseconds': 0
                 }
                }
             }
        ],
        'shouldEndSession': True
    }

def build_audio_response(audioFunction: str, token: str, url:str):
    """Builds an audio response with the given audiofunction (Play, Pause, etc.), Unique token, url and offset=0"""
    return build_audio_response(audioFunction,token,url,0)

def start_play_url_response(url:str):
    tokenGen = sha256()
    tokenGen.update(url.encode())
    token=tokenGen.hexdigest()

    return build_audio_response("Play", token, url)



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

    session_attributes =default_session
    card_title = "Adventures in Odyssey"
    speech_output = "Welcome to Adventues in Odyssey. " \
                    "You can ask me to play an episode currently on the radio or a free episode from Whit's end dot org." \
                    "If you don't know the name of the episode you can ask - What's on the radio?" \
                    "Or just say - Play the latest episode." \
                    "If you just want to hear anything say - play anything, play whatever, or play a random episode."
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



def handlePlayByNameIntent(intent, session):
    global default_session
    """Plays an Episode by it's name."""

    card_title = ""
    session_attributes = default_session
    should_end_session = False

    if 'EpisodeName' in intent['slots']:
        episodeName = intent['slots']['EpisodeName']['value']
        session_attributes = session['attributes']+{'lastPlayed':episodeName}
        e=AIO.getFreeEpisodeByName(episodeName)
        return build_response(session_attributes,start_play_url_response(e['url']))

    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "Please try again."
        reprompt_text = "I'm not sure what your favorite color is. " \
                        "You can tell me your favorite color by saying, " \
                        "my favorite color is red."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def handleListRadioIntent():
    global default_session
    session_attributes=default_session
    session_attributes['Radio']=True
    speech_output = "I found the currently airing episodes.  Interrupt me when you hear one you want to play, and say the name of the episode.  " + ".  ".join(["Episode {0}.  ".format(ep['Number'])+ep['Name'] for ep in AIO.getRadioEpisodes()])
    reprompt_text = "Which episode do you want to play?  You can ask for a description, say the name of the episode, or say the number. "

def handleListFreeIntent():
    global default_session
    session_attributes = default_session
    session_attributes['Free']=True
    speech_output = "I found some free episodes.  Interrupt me when you hear one you want to play.  " + ".  ".join(["Episode {0}.  ".format(ep['Number'])+ep['Name'] for ep in AIO.getFreeEpisodes()])

def get_color_from_session(intent, session):
    session_attributes = {}
    reprompt_text = None

    if session.get('attributes', {}) and "favoriteColor" in session.get('attributes', {}):
        favorite_color = session['attributes']['favoriteColor']
        speech_output = "Your favorite color is " + favorite_color + \
                        ". Goodbye."
        should_end_session = True
    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "You can say, my favorite color is red."
        should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

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

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "MyColorIsIntent":
        return set_color_in_session(intent, session)
    elif intent_name == "WhatsMyColorIntent":
        return get_color_from_session(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
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
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
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
