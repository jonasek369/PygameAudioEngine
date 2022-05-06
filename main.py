import math
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import List
from uuid import uuid4

from pygame import mixer


class SoundState(Enum):
    Waiting = auto()
    Finished = auto()
    Error = auto()
    Paused = auto()
    Playing = auto()


@dataclass
class Audio:
    AudioPath: str
    Volume: float  # 0.0 to 1.0

    Position: List
    # in units same as position
    AudioRange: float
    Channel: mixer.Channel = None
    Status: SoundState = SoundState.Waiting
    Uuid = str(uuid4())
    _CHANNEL_VOLUME_SET = -1

    def set_channel_vol(self, vol):
        self._CHANNEL_VOLUME_SET = vol

    def get_channel_vol(self):
        return self._CHANNEL_VOLUME_SET


@dataclass
class ChangePositionCommand:
    TargetUuid: str
    NewPosition: List


class AudioEngine2D:
    def __init__(self, max_channels=32):
        self.uuid = str(uuid4())
        self.loaded = {}
        self.sounds: List[Audio] = []
        self.__running = False
        self.__listener_position = [0, 0]
        self.__to_pause: List[str] = []
        self.__to_unpause: List[str] = []
        self.__change_pos: List[ChangePositionCommand] = []
        self.MAX_CHANNELS = max_channels
        self.CHANNEL_ADDER = 4
        #  you can chose if you want 2D audio
        self.AUDIO_2D = True
        mixer.pre_init(44100, -16, 2, 4096)
        mixer.init()
        mixer.set_num_channels(self.MAX_CHANNELS)

    # start the main function in thread so you can do anything on the main one
    def start(self):
        self.__running = True
        threading.Thread(target=self.update).start()

    # stops the self.update function and the thread
    def stop(self):
        self.__running = False

    # Sets the position of listener (player)
    def set_listener_position(self, position):
        self.__listener_position = position

    # STATIC METHODS
    # I just wanted to be in the class so it wont litter the namespace if you import *

    # Logarithmic graph function for getting volume
    @staticmethod
    def distance_to_sound(distance, maxdistance):
        return 1 - (19 / 20) * math.log(distance / maxdistance + 0.1, 10)

    # gets the distance between 2 points (params are Lists of 2 numbers)
    @staticmethod
    def distance(d1, d2):
        return math.sqrt((d2[0] - d1[0]) ** 2 + (d2[1] - d1[1]) ** 2)

    @staticmethod
    def percentage(whole, percts):
        return (whole / 100) * percts

    @staticmethod
    def get_percentage(whole, number):
        return number / (whole / 100)

    # main function for managing and playing all the audios
    def update(self):
        while self.__running:
            for audio in self.sounds.copy():
                # Change sound position
                for cpc in self.__change_pos.copy():
                    cpc_index = self.__change_pos.index(cpc)
                    if cpc.TargetUuid == audio.Uuid:
                        audio.Position = cpc.NewPosition
                        self.__change_pos.pop(cpc_index)
                        break

                # Pause
                for paused_uuid in self.__to_pause.copy():
                    if paused_uuid == audio.Uuid:
                        audio.Status = SoundState.Paused
                        audio.Channel.pause()
                        self.__to_pause.pop(self.__to_pause.index(paused_uuid))
                        break

                # Unpause
                for unpaused_uuid in self.__to_unpause:
                    if unpaused_uuid == audio.Uuid:
                        audio.Status = SoundState.Playing
                        audio.Channel.unpause()
                        self.__to_unpause.pop(self.__to_unpause.index(unpaused_uuid))
                        break

                if audio.Channel is not None:
                    # Set volume
                    if audio.Volume != audio.get_channel_vol():
                        audio.Channel.set_volume(audio.Volume)
                        audio.set_channel_vol(audio.Volume)

                    # If sound finished dispose
                    if not audio.Channel.get_busy() and audio.Status == SoundState.Playing:
                        audio.Status = SoundState.Finished
                        self.sounds.pop(self.sounds.index(audio))
                        continue

                    # Changing volume base on user distance and sound distance
                    if audio.Channel.get_busy():
                        if not self.AUDIO_2D:
                            continue
                        audio_pos = audio.Position
                        listener_pos = self.__listener_position
                        dist = self.distance(audio_pos, listener_pos)
                        if dist < audio.AudioRange:
                            continue
                        volume = self.distance_to_sound(dist, audio.AudioRange)
                        if volume < 0:
                            volume = 0
                        perc = self.get_percentage(1.0, volume)
                        conv = self.percentage(audio.Volume, perc)
                        audio.Channel.set_volume(conv)
                        continue

                # If sound is not playing load up audio and find channel for it
                load = self.loaded[audio.AudioPath]
                channel = mixer.find_channel()

                # Not sure if this actually works but if there are not enough channels to play a sound
                # Add new based on CHANNEL_ADDER
                if channel is None:
                    self.MAX_CHANNELS += self.CHANNEL_ADDER
                    mixer.set_num_channels(self.MAX_CHANNELS)
                    channel = mixer.find_channel()

                # Start the sound
                audio.Channel = channel
                audio.Status = SoundState.Playing
                channel.play(load)
                channel.set_volume(audio.Volume)
                audio._CHANNEL_VOLUME_SET = audio.Volume

    # Get all playing sounds as list of Audio class
    def get_playing(self) -> List[Audio]:
        audios = []
        for audio in self.sounds:
            if audio.Status == SoundState.Playing:
                audios.append(audio)
        return audios

    def pause(self, uuid: str):
        self.__to_pause.append(uuid)

    def unpause(self, uuid: str):
        self.__to_unpause.append(uuid)

    # removes song from list
    def remove_song(self, uuid: str):
        try:
            for audio in self.sounds.copy():
                if uuid == audio.Uuid:
                    audio.Channel.stop()
                    self.sounds.pop(self.sounds.index(audio))
                    break
        except ValueError:
            print(f"Could not find this audio")

    # This function loads up the sound file and saves it for later use, saves audio to sounds so self.update can use it
    def add(self, audio: Audio):
        self.loaded[audio.AudioPath] = mixer.Sound(audio.AudioPath)
        self.sounds.append(audio)

    # This function just saves the provided mixer.Sound and saves the audio so self.update can use it
    def add_preloaded(self, audio: Audio, sound: mixer.Sound):
        self.loaded[audio.AudioPath] = sound
        self.sounds.append(audio)

    # This should not be relied upon because it searches through the AudioPath so it can find false things
    def get_uuid(self, song_name) -> str:
        for audio in self.sounds:
            if song_name in audio.AudioPath.lower():
                return audio.Uuid

    # This should not be relied upon because it searches through the AudioPath so it can find false things
    def get_audio(self, song_name) -> Audio:
        for audio in self.sounds:
            if song_name in audio.AudioPath.lower():
                return audio

    # This makes ChangePositionCommand and saves so self.update can process it
    def set_audio_position(self, uuid: str, new_pos):
        self.__change_pos.append(ChangePositionCommand(uuid, new_pos))
