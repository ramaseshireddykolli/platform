
import requests, time, os, json, re
import threading
import asyncio
import datetime


platform = "voicegain"
#platform = "ascalon"
JWT = "<your JWT token>"
headers = {"Authorization":JWT}

# Audio file and Upload settings
#  
#audio_fname = 'pcm_stereo_10sec.wav'
#audio_fname = "cbA2_stereo.wav" ## apply prepaid card to account -- 6 minutes 6 seconds
#audio_fname = "wtB19-stereo.wav" ## cancel radio -- 1 minute 36 seconds
#audio_fname = "wtB41-stereo.wav" ## broken radio -- 3 minutes 17 seconds
audio_fname = "spotlight-order-mono.mp3"

audio_type = "audio/wav"

data_url = "https://api.{}.ai/v1/data/file".format(platform)

data_body = {
    "name" : re.sub("[^A-Za-z0-9]+", "-", audio_fname),
    "description" : audio_fname,
    "contentType" : audio_type,
    "tags" : ["test"]
}

multipart_form_data = {
    'file': (audio_fname, open(audio_fname, 'rb'), audio_type),
    'objectdata': (None, json.dumps(data_body), "application/json")
}

# Speech Analytics Configuration
#
sa_config_name = "SA-Offline-Demo-script-test-0008-dev"

sa_body = {
    "name": sa_config_name,
 
    "sentiment": True,
    "summary": True,
    "wordCloud": False,
    "gender": True,
    "age": False,
    "profanity": True,    
    "overtalkTotalPercentageThreshold": 1.0,
    "overtalkSingleDurationMaximumThreshold": 1,
    "silenceTotalPercentageThreshold": 10.0,
    "silenceSingleDurationMaximumThreshold": 3,

    "moods": [
        "anger"
    ],

    "entities": [
        "ADDRESS",
        "PHONE",
        "PERSON",
        "MONEY",
        "DATE",
        "TIME"
    ],

    "keywords": [
        {
            "tag": "SPOTLIGHT",
            "examples": [
                {
                    "phrase": "spotlight",
                    # "usage": null
                }
            ],
            "expand": False,
            "hide": False
        },
        {
            "tag": "VISA",
            "examples": [
                {"phrase": "visa"}, {"phrase": "visa card"}, {"phrase": "visa credit card"}
            ],
            "expand": False,
            "hide": False
        }
    ],

    "phrases": [
        {
            "tag": "AGENT_GREETING",
            "builtIn": False,
            "examples": [
                {
                    "sentence": "Thank you for calling.",
                    "sensitivity": 0.75
                }
            ],
            "location" : {
            #    "channel" : "caller",
                "time" : 20000
             },
            "hideIfGroup": False
        },         
        {
            "tag": "AGENT_INTRO",
            "builtIn": False,
            "examples": [
                {
                    "sentence": "This is Eve speaking.",
                    "sensitivity": 0.5
                },
                {
                    "sentence": "My name is Eve",
                    "sensitivity": 0.5
                }
            ],
            "slots" : {
              "entities" : [
                {
                  "entity" : "PERSON",
                  "required" : True
                }
              ]
              },
              "location" : {
            #    "channel" : "caller",
                "time" : 20000
            },
            "hideIfGroup": False
        },         
        {
            "tag": "OFFER_ASSISTANCE",
            "builtIn": False,
            "examples": [
                {
                    "sentence": "How can I help you today?",
                    "sensitivity": 0.75
                }
            ],
            "location" : {
            #    "channel" : "caller",
                "time" : 20000
            },
            "hideIfGroup": False
        },         
        {
            "tag": "ACCOUNT_VERIFY",
            "builtIn": False,
            "examples": [
                {
                    "sentence": "can you please verify your phone number for me",
                    "sensitivity": 0.75
                }
            ],
            "hideIfGroup": False
        },
        {
            "tag": "ANYTHING_ELSE_HELP",
            "builtIn": False,
            "examples": [
                {
                    "sentence": "is there anything else I can help you with?",
                    "sensitivity": 0.75
                }
            ],
            "hideIfGroup": False
        }
    ]
}
sa_config_id = None
object_id = None

# new SA session request
# 
body = {
  "asyncMode": "OFF-LINE",
  "metadata" : [
    {"name" : "launchedFrom", "value" : "offline-sa-mono.py"}
  ],
  "audio":{
      "source": {
          "dataStore": {
              "uuid": object_id
          }
      }
  },
  "virtualDualChannelEnabled" : True,
   "speakerChannels" : [
     { "audioChannelSelector" : "mix"}
     ],
  "asr": {
    "acousticModelNonRealTime" : "VoiceGain-omega-x",
    "noInputTimeout": 60000,
    "completeTimeout": 5000,
    "sensitivity" : 0.5,
    "speedVsAccuracy" : 0.5
  },
  "saConfig":sa_config_id
}


# API request setup SA configuration
def web_api_request_sa_config(headers, body):
  print("create new SA config")
  init_response_raw = requests.post("https://api.{}.ai/v1/sa/config".format(platform), json=body, headers=headers)
  init_response = init_response_raw.json()
  if("BAD_REQUEST" == init_response.get("status") and  "the specified name is being used" in  init_response.get("message")):
    print(init_response.get("message"))
    init_response_raw = requests.get("https://api.{}.ai/v1/sa/config?name={}".format(platform, sa_config_name), headers=headers)
    sa_config_list = init_response_raw.json()
    existing_sa_config_id = None
    for sa_config in sa_config_list:
      if(sa_config_name == sa_config.get("name")):
        existing_sa_config_id = sa_config.get("saConfId")
        print("existing SA config: "+existing_sa_config_id)
    if(existing_sa_config_id is None):
      exit()
    ## delete old config
    print("delete old SA config: "+existing_sa_config_id)
    init_response_raw = requests.delete("https://api.{}.ai/v1/sa/config/{}".format(platform, existing_sa_config_id), headers=headers)
    print(init_response_raw.status_code)
    print(init_response_raw.text)
    ## create new config
    web_api_request_sa_config(headers, sa_body)
    return
  elif(init_response.get("saConfId") is None):
    print("did not start create SA config")
    print(init_response_raw.status_code)
    print(init_response_raw.text)
    exit()
  else:
    print("response: {}".format(str(init_response)))

  # retrieve values from response
  global sa_config_id
  sa_config_id = init_response["saConfId"]

  print("          SA Config: {}".format(sa_config_id))


# api request to upload data
def web_api_request_post_data(headers, audio_fname, audio_type):
  data_url = "https://api.{}.ai/v1/data/file".format(platform)

  data_body = {
      "name" : re.sub("[^A-Za-z0-9]+", "-", audio_fname),
      "description" : audio_fname,
      "contentType" : audio_type,
      "tags" : ["test"]
  }

  multipart_form_data = {
      'file': (audio_fname, open(audio_fname, 'rb'), audio_type),
      'objectdata': (None, json.dumps(data_body), "application/json")
  }
  print("uploading audio data ...", flush=True)
  data_response = requests.post(data_url, files=multipart_form_data, headers=headers).json()
  print("data response: {}".format(data_response), flush=True)
  global object_id
  object_id = data_response["objectId"]
  print("objectId: {}".format(object_id), flush=True)


# api request to start SA session
def web_api_request_sa(headers, body):
  body["saConfig"] = sa_config_id
  print("saConfig: {}".format(body["saConfig"]), flush=True)
  body["audio"]["source"]["dataStore"]["uuid"] = object_id
  print("POST /sa: {}".format(body), flush=True)
  init_response_raw = requests.post("https://api.{}.ai/v1/sa".format(platform), json=body, headers=headers)
  init_response = init_response_raw.json()
  if(init_response.get("saSessionId") is None):
    print("did not start SA session")
    print(init_response_raw.status_code)
    print(init_response_raw.text)
    exit()

  print("response: {}".format(str(init_response)))

  # retrieve values from response
  # sessionId and capturedAudio are printed for debugging purposes
  sa_session_id = init_response["saSessionId"]
  session_id_transcribe = init_response["speakerChannels"][0]["transcribeSessionId"]
  poll_url = init_response["poll"]["url"] 

  print("        SA SessionId: {}".format(sa_session_id))
  print("SessionId Transcribe: {}".format(session_id_transcribe))
  print("            Poll URL: {}".format(poll_url))

  web_res = {}
  web_res["sa_session_id"] = sa_session_id
  web_res["poll_url"] = poll_url
  return web_res 

# api request to check is SA session is done
def poll_sa(headers, poll_url, start):
  init_response_raw = requests.get(poll_url, headers=headers, timeout=15)
  init_response = init_response_raw.json()
  status = init_response.get("status")
  print("status: {}  {:.2f}sec".format(status, (time.time()-start)), flush=True)
  if(status not in ("processing", "ready")):
    print("for poll url "+str(poll_url)+" error: "+str(init_response_raw.text), flush=True)
  return status

# api request to get final results
def get_sa(headers, sa_session_id):
  init_response_raw = requests.get("https://api.{}.ai/v1/sa/{}/data?summary=true&emotion=true&keywords=true&entities=true&phrases=true".format(platform, sa_session_id), headers=headers)
  init_response = init_response_raw.json()
  status = init_response.get("status")
  print("status: {}  ".format(status), flush=True)
  if(status not in ("processing", "ready")):
    print("for session "+str(sa_session_id)+" error: "+str(init_response_raw.text), flush=True)

  # print("JSON for ses {}".format(sa_session_id), flush=True)  
  # print(str(init_response), flush=True)

  print(" saSessionId: {}".format(init_response.get("saSessionId")), flush=True)
  print("    metadata: {}".format(init_response.get("metadata")), flush=True)
  print("     summary: {}".format(init_response.get("summary")), flush=True)
  print("CH1  speaker: {}".format(init_response["channels"][0].get("spk")), flush=True)
  print("CH2  speaker: {}".format(init_response["channels"][1].get("spk")), flush=True)
  print("CH1    agent: {} (guessing which diarized channel is Agent is not implemented yet)".format(init_response["channels"][0].get("isAgent")), flush=True)
  print("CH2    agent: {} (guessing which diarized channel is Agent is not implemented yet)".format(init_response["channels"][1].get("isAgent")), flush=True)
  print("CH1   gender: {}".format(init_response["channels"][0].get("gender")), flush=True)
  print("CH2   gender: {}".format(init_response["channels"][1].get("gender")), flush=True)
  print("CH1 keywords: {}".format(json.dumps( init_response["channels"][0].get("keywords"), indent=3)), flush=True)
  print("CH2 keywords: {}".format(json.dumps( init_response["channels"][1].get("keywords"), indent=3)), flush=True)
  print("CH1 entities: {}".format(json.dumps( init_response["channels"][0].get("namedEntities"), indent=3)), flush=True)
  print("CH2 entities: {}".format(json.dumps( init_response["channels"][1].get("namedEntities"), indent=3)), flush=True)
  print("CH1  phrases: {}".format(json.dumps( init_response["channels"][0].get("phrases"), indent=3)), flush=True)
  print("CH2  phrases: {}".format(json.dumps( init_response["channels"][1].get("phrases"), indent=3)), flush=True)  
  print("CH1  emotion: {}".format(json.dumps( init_response["channels"][0].get("emotion"), indent=3)), flush=True)
  print("CH2  emotion: {}".format(json.dumps( init_response["channels"][1].get("emotion"), indent=3)), flush=True)
  print("CH1     talk: {}".format(json.dumps( init_response["channels"][0].get("talk"), indent=3)), flush=True)
  print("CH2     talk: {}".format(json.dumps( init_response["channels"][1].get("talk"), indent=3)), flush=True)
  print("phraseGroups: {}".format(json.dumps( init_response.get("phraseGroups"), indent=3)), flush=True)

  sections_array = init_response.get("multiChannelWords")

  utterances = []

  # Go through each JSON object in the array
  for json_object in sections_array:
      # For each 'words' array in the JSON object
      for word in json_object['words']:
          # Extract the 'utterance' field and append to the list
          utterances.append(word['utterance'])

  utterances_string = ' '.join(utterances)

  print("words (speakers combined): {}".format(utterances_string), flush=True)

  return status

############
### MAIN ###
############


web_api_request_sa_config(headers, sa_body)

web_api_request_post_data(headers, audio_fname, audio_type)

web_res = web_api_request_sa(headers, body)

start = time.time()
time.sleep(1.0)
status = poll_sa(headers, web_res.get("poll_url"), start)

while (status == "processing"):
  time.sleep(1)
  status = poll_sa(headers, web_res.get("poll_url"), start)

print("final status: {}".format(status), flush=True)


get_sa(headers, web_res.get("sa_session_id"))