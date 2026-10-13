Plivo Assignment by Nidhi Meda :D
The task required us to build an application that lets a user make a call to "InspireWorks" and verify themselves using their OTP (hardcoded here) and lets them hear a ringtone or call an associate (dummy number here).

This project folder contains the following files:
app.py - the main python file that has all the logic of the application
requirements.txt - all necessary requirements to be installed
.env - an environment file that has all the auth tokens, otp, sender and receivers phone number
templates/index.html - for the simple UI for this project

**ngrok**
Before running the application, you have to download ngrok, do so by going to ngrok.com/download. 
Once completed, sign up and get your auth token.
Next, run ngrok config add-authtoken <token from the ngrok dashboard>
Run ngrok http 5000
Copy the Forwarding link and paste it in the .env file (should look something like https://abcd-1234.ngrok-free.app)

**run the application**
Here's how you can run this application...
On the first terminal, run:
pip install -r requirements.txt
ngrok http 5000

On another terminal:
python app.py
Then open the url that pops up (it should look like this: http://127.0.0.1:5000)


for the .env file, have the following details:
PLIVO_AUTH_ID=MAMTAWMGI0MZCTNTYZZS
PLIVO_AUTH_TOKEN=ZDRmNzIxMTgtNWE5Mi00ZDE3LWI2NmMtMmNiZGE4
PLIVO_NUMBER=918035454161
ASSOCIATE_NUMBER=912264236412
BASE_URL=https://oval-rentable-overfeed.ngrok-free.dev
OTP=0303
AUDIO_URL=https://s3.amazonaws.com/plivocloud/Trumpet.mp3

