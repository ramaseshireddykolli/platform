# Voicegain.ai ASR Real-Time Transcription with Websocket

from ffmpy import FFmpeg
import requests, time, os, json
import threading
import asyncio
import websockets
import datetime
import configparser


cfg = configparser.ConfigParser()
cfg.read("config.ini")
configSection = cfg.get("DEFAULT", "CONFIG")
protocol = cfg.get(configSection, "PROTOCOL")
hostPort = cfg.get(configSection, "HOSTPORT")
JWT = cfg.get(configSection, "JWT")
urlPrefix = cfg.get(configSection, "URLPREFIX")
inputFolder = cfg.get("DEFAULT", "INPUTFOLDER")
inputFile = cfg.get("DEFAULT", "INPUTFILE")

inputFilePath = f"{inputFolder}/{inputFile}"

sampleRate = 8000
channels = 2
bytesPerSample = 2

#sendingWSProtocol = "WSS"
sendingWSProtocol = "WS"

#receivingWSProtocol = "wss"
receivingWSProtocol = "ws"

#acousticModelRealTime = "VoiceGain-rho-en-us"
#acousticModelRealTime = "VoiceGain-rho"
acousticModelRealTime = "VoiceGain-kappa"

headers = {"Authorization":JWT}

# new transcription session request
# it specifies audio input via an RTP stream
# and output is via a plain websocket
body = {
    "sessions": [
        {
            "asyncMode": "REAL-TIME",
            "audioChannelSelector": "left",
            "websocket": {
                "mode": 'transceiver',
                "ssId" : 'left',
                "useSTOMP": 'false',
                "minimumDelay": 0
            },
            "content": {
                "incremental": ['words'],
                "full": []
            }
        },
        {
            "asyncMode": "REAL-TIME",
            "audioChannelSelector": "right",
            "websocket": {
                "mode": 'transceiver',
                "ssId" : 'right',
                "useSTOMP": 'false',
                "minimumDelay": 0
            },
            "content": {
                "incremental": ['words'],
                "full": []
            }
        }
    ],
    "audio": {
        "source": {"stream": {"protocol": sendingWSProtocol}},
        "format": "L16",
        "channel": "stereo",
        "rate": sampleRate,
        "capture": 'true'
    },
    "settings": {
        "asr": {
            "acousticModelRealTime" : acousticModelRealTime,
            "noInputTimeout": 59999,
            "incompleteTimeout": 3599999,
            "sensitivity": 0.4,
            "hints": [
                "Starburst:10",
                "Mars_Wrigley:10",
                "contacting:8",
                "Mars_Consumer_Care:10",
                "mints:8"
            ]
        },
        "formatters": [
            {
                "type": "digits"
            },
            {
                "type": "enhanced",
                "parameters": {
                    "CC": True,
                    "EMAIL": True
                }
            },
            {
                "type": "spelling",
                "parameters": {
                    "lang": "en-US"
                }
            },
            {
                "type": "redact",
                "parameters": {
                    "CC": "partial"
                }
            }
        ]
    }
}

def web_api_request(headers, body):
  url = "{}://{}/{}/asr/transcribe/async".format(protocol, hostPort, urlPrefix)
  print(f"making POST request to {url}", flush=True)

  init_response_raw = requests.post(url, json=body, headers=headers)
  init_response = init_response_raw.json()
  if(init_response.get("sessions") is None):
    print("did not obtain session")
    print(init_response_raw.status_code)
    print(init_response_raw.text)
    exit()

  # retrieve values from response
  # sessionId and capturedAudio are printed for debugging purposes
  session_id_left = init_response["sessions"][0]["sessionId"]
  session_id_right = init_response["sessions"][1]["sessionId"]
  audio_ws_url = init_response["audio"]["stream"]["websocketUrl"]
  capturedAudio = init_response["audio"].get("capturedAudio")

  print("        SessionId L: {}".format(session_id_left))
  print("        SessionId R: {}".format(session_id_right))
  print("Audio Websocket URL: {}".format(audio_ws_url))

  ## mod_vg_tap_ws would get this `audio_ws_url` as input parameter

  if( not(capturedAudio is None)):
    print("captured audio id: {}".format(capturedAudio))
  
  web_res = {}
  web_res["audio_ws_url"] = audio_ws_url
  return web_res 

class Channel:
    def __init__(self, msgCnt: int, stack: list):
        self.msgCnt = msgCnt
        self.stack = stack

    def __str__(self):
        return f'Channel(msgCnt={self.msgCnt}, stack={self.stack})'


channnelData = {}
channnelData["left"] = Channel(0, [])
channnelData["right"] = Channel(0, [])

# function to process JSON with incremental transcription results sent as messages over websocket
def process_ws_msg(wsMsg):
  global channnelData, startTime

  # uncomment this to see raw messages 
  # print(prefix+" "+wsMsg, flush=True)

  try:
    data = json.loads(wsMsg)
    ssId = data.get('ssId')
    channel = channnelData.get(ssId)
    utter = data.get('utt')
    if( utter is None ):
      toDel = data.get('del')
      if( toDel is None):
        # unknown edit
        print("EDIT->"+wsMsg, flush=True)
      else:
        # delete and edits
        for i in range(toDel):
          channel.stack.pop()
        edits = data.get('edit')
        if(not (edits is None)):
          for edit in edits:
            utter = edit.get('utt')
            channel.stack.append(utter)
    else:
      # simple utterance
      channel.stack.append(utter)
      if( len(channel.stack) > 50 ):
        while(len(channel.stack) > 30):
          channel.stack.pop(0)

    time_difference = time.time() - startTime
    formatted_time_difference = format(time_difference, '.3f')

    if ssId == "right":
      #'\033[92m'
      print("\033[92m\n\t"+formatted_time_difference +' '+ssId+" \t"+' '.join(channel.stack) + '\033[0m', flush=True)
    else:
      print("\033[94m\n\t"+formatted_time_difference +' '+ssId+" \t"+' '.join(channel.stack) + '\033[0m', flush=True)
  except Exception as e: 
    print("ERROR: "+str(e), flush=True)


# function to read audio from file and convert it to ulaw and send to websocket
async def stream_audio(file_name, websocket):
  global epoch_start_audio_stream
  print("START stream_audio", flush=True)
  conv_fname = (file_name+'.ulaw')
  ff = FFmpeg(
      inputs={file_name: []},
      #outputs={conv_fname : ['-ar', '8000', '-f', 'mulaw', '-y']}
      outputs={conv_fname : ['-ar', str(sampleRate), '-f', 's16le', '-y']}
  )
  ff.cmd
  ff.run()
  print("\nstreaming "+conv_fname+" to websocket", flush=True)
  with open(conv_fname, "rb") as f:
    try:
      print(str(datetime.datetime.now())+" connected", flush=True)
      global startTime
      startTime = time.time()
      n_buf = 1 * 1024
      byte_buf = f.read(n_buf)
      start = time.time()
      epoch_start_audio_stream = start
      elapsed_time_fl = 0
      count = 0
      while byte_buf:
        n = len(byte_buf)
        print(".", end =" ", flush=True)
        try:
          await websocket.send(byte_buf)
        except Exception as e:
            print(str(datetime.datetime.now())+" Exception 1 when sending audio via websocket: "+str(e)) # usually because the session closed due to NOMATCH or NOINPUT
            break
        count += n
        elapsed_time_fl = (time.time() - start)
        expected_time_fl = count / (sampleRate * channels * bytesPerSample)
        time_to_wait = expected_time_fl - elapsed_time_fl
        if time_to_wait >= 0: 
          time.sleep(time_to_wait) # to simulate real time streaming
        byte_buf = f.read(n_buf)
      elapsed_time_fl = (time.time() - start)
      print(str(datetime.datetime.now())+" done streaming audio in "+str(elapsed_time_fl), flush=True)
      print("Waiting 10 seconds for processing to finish...", flush=True)  
      time.sleep(10.0)
      print("done waiting", flush=True)  
      global keep_running
      keep_running = False
      await websocket.close()
      print(str(datetime.datetime.now())+" websocket closed", flush=True)
    except Exception as e:
      print(str(datetime.datetime.now())+" Exception 2 when sending audio via websocket: "+str(e)) 


async def receive_messages(websocket):
    async for message in websocket:
        process_ws_msg(message)

async def main():
    web_res = web_api_request(headers, body)
    uri = web_res["audio_ws_url"]
    
    async with websockets.connect(uri, 
      # we need to lower the buffer size - otherwise the sender will buffer for too long
      write_limit=128, 
      # compression needs to be disabled otherwise will buffer for too long
      compression=None) as websocket:
        send_task = asyncio.create_task(stream_audio(inputFilePath, websocket))
        receive_task = asyncio.create_task(receive_messages(websocket))
        
        await asyncio.gather(send_task, receive_task)

if __name__ == "__main__":
    asyncio.run(main())
