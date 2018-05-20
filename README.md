# AlexaAIO
An Alexa Skill for playing Adventures in Odyssey Episodes!

### What is it?
AlexaAIO is a skill demonstrating audio playback on Alexa.  It is designed to run on AWS Lambda and is ready to deploy with [python-lambda](https://github.com/nficano/python-lambda).  All episode data is gathered from [aiowiki.com](http://www.aiowiki.com/wiki/Main_Page).

### How do I get started?
First, install python-lambda `pip3 install --user python-lambda`.  Once that's finished, activate the virtualenv.  You can now use `lambda invoke -v` to test the function with event.json as the input.

### It Works... Now what?
To function fully, the program needs to store information about the play state (time and episode) for each user.  Create a role on AWS with minimally, lambda_basic_execution and access to a DynamoDB table which will store this information.  Change SESSION_TABLE_NAME at the top of AIOspeechlet.py to the name of your new table, and REGION_NAME to the AWS region your will be using.  The program is now functional *YAY!*  You can now run `lambda deploy` to upload it to your AWS.

### The Alexa Interaction Model
The Alexa Voice Service translates spoken phrases into intents with slots, which it passes to an https API endpoint, which processes those inputs and returns a response.  The Alexa service does this by analyzing example mappings from utterances to intents, which are collectively an *interaction model.*  On the [Alexa Developer](https://developer.amazon.com/alexa) website, intents can be added one by one via a GUI, or as a JSON document.

The interaction model for this skill is included [here](interaction_model.json).

### To Be Continued...

