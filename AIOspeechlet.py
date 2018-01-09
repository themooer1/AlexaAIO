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

def build_audio_response(audioFunction: str, token: str, url:str, offset=0, playBehavior="REPLACE_ALL"):
    """Builds an audio response with the given audiofunction (Play, Pause, etc.), Unique token, url and offset=0"""
    if audioFunction not in {"Play","Stop","ClearQueue"}: return build_speechlet_response("Unsupported audio directive "+audioFunction, "Unsupported audio directive "+audioFunction+" was prevented from executing.", None, True)
    return {
        'outputSpeech': {},
        'card': {},
        'reprompt': {},
        'directives': [
            {'type': "AudioPlayer."+audioFunction,
             'playBehavior': playBehavior,
             'audioItem': {
                 'stream': {
                     'token': token,
                     'url': url,
                     'offsetInMilliseconds': offset
                 }
                }
             }
        ],
        'shouldEndSession': True
    }


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

    latest=AIO.getRadioEpisodes()[0]

    session_attributes =default_session
    card_title = "Adventures in Odyssey"
    speech_output = "Welcome to Adventues in Odyssey. " \
                    "You can ask me to play an episode currently on the radio or a free episode from Whit's end dot org." \
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

def handlePlayByNumberIntent(intent, session):

    card_title="playByNumberFailed"
    session_attributes=session['attributes']
    should_end_session = True

    if 'EpisodeNumber' in intent['slots']:
        episodeNumber = intent['slots']['EpisodeNumber']['value']
        session_attributes = session['attributes']
        if session_attributes['Radio']==True:
            session_attributes.update({'lastPlayed':AIO.getRadioEpisodeByNumber(episodeNumber)})
            session_attributes['Radio']=False
            e=AIO.getRadioEpisodeByNumber(episodeNumber)
        else:
            session_attributes.update({'lastPlayed':AIO.getFreeEpisodeByNumber(episodeNumber)})
            session_attributes['Free']=False
            e=AIO.getFreeEpisodeByNumber(episodeNumber)
        return build_response(session_attributes,start_play_url_response(e['url']))
    else:
        speech_output = "playByName was called, but no episode name was found. " \
                        "Please try again."
        reprompt_text = None
        return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def handlePlayByNameIntent(intent, session):
    global default_session
    """Plays an Episode by it's name."""

    card_title = "playByNameFailed"
    session_attributes = session['attributes']
    should_end_session = True

    if 'EpisodeName' in intent['slots']:
        episodeName = intent['slots']['EpisodeName']['value']
        session_attributes = session['attributes']
        session_attributes.update({'lastPlayed':episodeName})
        if session_attributes['Radio']==True:
            e=AIO.getRadioEpisodeByName(episodeName)
            session_attributes['Radio']=False
        elif session_attributes['Free']==True:
            e=AIO.getFreeEpisodeByName(episodeName)
            session_attributes['Free']=False
        else:
            e=AIO.getRadioEpisodeByName(episodeName)
            if not e:
                e=AIO.getFreeEpisodeByName(episodeName)

        return build_response(session_attributes,start_play_url_response(e['url']))

    else:
        speech_output = "playByName was called, but no episode name was found. " \
                        "Please try again."
        reprompt_text = None
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
    speech_output = "I found some free episodes.  Interrupt me when you hear one you want to play, and say the name of the episode.    " + ".  ".join(["Episode {0}.  ".format(ep['Number'])+ep['Name'] for ep in AIO.getFreeEpisodes()])



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
    if intent_name == "PlayByNumberIntent":
        return handlePlayByNumberIntent(intent, session)
    elif intent_name == "PlayByNameIntent":
        return handlePlayByNameIntent(intent, session)
    elif intent_name == "ListRadioIntent":
        return handleListRadioIntent(intent, session)
    elif intent_name == "ListFreeIntent":
        return handleListFreeIntent(intent, session)
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
    #if (event['session']['application']['applicationId'] !=
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