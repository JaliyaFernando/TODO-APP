
from __future__ import division

import re
import sys
import io
import os
import datetime

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types


import pyaudio
from six.moves import queue

RATE = 16000
CHUNK = int(RATE / 10)


class MicrophoneStream(object):
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,

            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):

        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        print('startinggg...')
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):

    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript


        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            #sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript )
            #nlu_analyze(transcript)
            if re.search(r'\b(exit|quit)\b', transcript, re.I):
                print('Exiting..')
                break
            elif re.search(r'\b(list)\b', transcript, re.I):
                viewList()
            else:
                witAi(transcript)
                num_chars_printed = 0

def wav2text(client):

    file_name = os.path.join(
        os.path.dirname(__file__),
        'resources',
        'dragndropw.wav')

    with io.open(file_name, 'rb') as audio_file:
        content = audio_file.read()
        audio = types.RecognitionAudio(content=content)

    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=22050,
        language_code='en-US')


    response = client.recognize(config, audio)
    return response
    '''
    for result in response.results:
        print('speech2text: {}'.format(result.alternatives[0].transcript))
    '''

def nlu_analyze(text):
    from google.cloud import language
    from google.cloud.language import enums
    from google.cloud.language import types

    #text = 'buy milk from supermarket next week'

    clientL = language.LanguageServiceClient.from_service_account_json('serviceAccount-credential.json')

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    entities = clientL.analyze_entities(document).entities

    for entity in entities:
        entity_type = enums.Entity.Type(entity.type)
        print('=' * 20)
        print(u'{:<16}: {}'.format('name', entity.name))
        print(u'{:<16}: {}'.format('type', entity_type.name))
        print(u'{:<16}: {}'.format('salience', entity.salience))

def witAi(transcript):

    from wit import Wit
    import os
    import json
    import datetime

    witClient = Wit('AED6DRCAVP2Q5LC6KX3RFU45KV5LESPH')
    text=transcript
    resp = witClient.message(text)

    newdate=''
    newtime=''
    current_time=str(datetime.datetime.now())
    #print(resp)
    if 'datetime' in resp['entities']:
        newDateTime=str(resp['entities']['datetime'][0]['value'])
        newdate=newDateTime[:10]
        dt_type=resp['entities']['datetime'][0]['grain']

        if dt_type in 'hour':
            newtime=newDateTime[11:16]

        else:
            newtime=current_time[11:16]
    else:
        newtime=current_time[11:16]
        newdate=current_time[:10]

    print(newtime,newdate)

    if 'agenda_entry' in resp['entities']:
        newtask=str(resp['entities']['agenda_entry'][0]['value'])
    else:
        newtask=text
                              

    newdict={newtime:newtask}

    txt_filename=newdate+'.txt'
    json_filename=newdate+'.json'
    jsondump=json.dumps(newdict)


    ######## load/save date entry   ############
    tasks={}
    times=[]
    mydays=[]
    with open("mydays.txt" , "r" ) as f:
        for line in f:
            mydays.append(str(line.strip()))



    if not newdate in mydays:

        mydays.append(newdate)
        mydays.sort()

        with open("mydays.txt", "w") as f:
            for x in mydays:
                f.write(str(x) + "\n")



        if not os.path.isfile(txt_filename):
            with open(txt_filename, "w") as f:
                f.write(newtime+"\n")


        #print(json_filename)
        if not os.path.isfile(json_filename):
            with open(json_filename, "w") as f:
                f.write(jsondump)


    elif newdate in mydays:

        with open(txt_filename , "r" ) as f:
            for line in f:
                times.append(str(line.strip()))

        if not newtime in times:
            times.append(newtime)
            times.sort()

            with open(txt_filename,"w") as f:
                for x in times:
                    f.write(str(x) + "\n")

        with open(json_filename , "r" ) as f:
            tasks=json.load(f)

        #print(tasks)

        if newtime in tasks:
            exist_task=tasks[newtime]
            tmp_task=exist_task + "," + newtask
            tasks[newtime] =  tmp_task

        else:
            tasks[newtime]=newtask

        new_json_dump=json.dumps(tasks)
        with open(json_filename, "w") as f:
            f.write(new_json_dump)

    print("entry added : " + newdate + " : " + newtime + " : " + newtask)
    print(" ----------------------------------------------------------------")


def viewList():
    import os
    import json
    print(" ----------------------------------------------------------------")
    mydays=[]
    with open('mydays.txt','r') as f:
        for line in f:
            mydays.append(str(line.strip()))

    mydays.sort()
    i=0
    while i< len(mydays) :

        print("\n\t"+mydays[i])

        times=[]
        filename=mydays[i]+'.txt'
        jfilename=mydays[i]+'.json'

        with open(filename,'r') as f:
            for line in f:
                times.append(str(line.strip()))

        times.sort()
        tasks={}
        with open(jfilename,'r') as f:
            tasks=json.load(f)

        for x in times:
            print(x +" : "+ tasks[x])

        i += 1
    print(" ----------------------------------------------------------------")

def main():
    language_code = 'en-US'
    client = speech.SpeechClient.from_service_account_json('serviceAccount-credential.json')
    responses=wav2text(client)
        '''
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)
        '''
        listen_print_loop(responses)




if __name__ == '__main__':
    main()
