import io
import queue
import threading
import wave

from elevenlabslib import ElevenLabsUser

import helper
from helper import update_config_file
from ttsProviders.__TTSProviderAbstract import TTSProvider

class ElevenlabsProvider(TTSProvider):
    def __init__(self):
        self.eventQueue = queue.Queue()
        self.readyForPlaybackEvent = threading.Event()
        self.readyForPlaybackEvent.set()

        configData = helper.get_provider_config(self)

        if configData["api_key"] == "":
            configData["api_key"] = input("Please input your elevenlabs API key. It can be found on the site, under profile.")

        user = ElevenLabsUser(configData["api_key"])
        if configData["voice_id"] == "":
            voiceList = user.get_available_voices()

            print("Voices available:")
            for voice in voiceList:
                print(str(voiceList.index(voice) + 1) + ") " + voice.initialName + " (" + voice.voiceID + ")")
            chosenVoiceIndex = -1
            while not (0 <= chosenVoiceIndex < len(voiceList)):
                try:
                    chosenVoiceIndex = int(input("Please choose a number.\n")) - 1
                except ValueError:
                    print("Not a valid number.")
            if helper.choose_yes_no("Would you like to save this voice in the config and skip having to choose one in the future?"):
                configData["voice_id"] = voiceList[chosenVoiceIndex].voiceID
            self.ttsVoice = voiceList[chosenVoiceIndex]
        else:
            self.ttsVoice = user.get_voice_by_ID(configData["voice_id"])

        helper.update_provider_config(self, configData)
        threading.Thread(target=self.waitForPlaybackReady).start()


    def synthesizeAndPlayAudio(self, prompt, outputDeviceIndex) -> None:
        newEvent = threading.Event()
        self.eventQueue.put(newEvent)
        def startcallbackfunc():
            newEvent.wait()
            print("Playing audio: " + prompt)
        def endcallbackfunc():
            print("Finished playing audio:" + prompt)
            self.readyForPlaybackEvent.set()

        self.ttsVoice.generate_and_stream_audio(prompt, outputDeviceIndex,
                                                streamInBackground=True,
                                                onPlaybackStart=startcallbackfunc,
                                                onPlaybackEnd=endcallbackfunc)

    def waitForPlaybackReady(self):
        while True:
            self.readyForPlaybackEvent.wait()
            self.readyForPlaybackEvent.clear()
            nextEvent = self.eventQueue.get()
            nextEvent.set()