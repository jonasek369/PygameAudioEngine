import logging
import math
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import List
from uuid import uuid4

import pygame
from pygame import mixer

logging.basicConfig(level=logging.INFO)


class SoundState(Enum):
    Waiting = auto()
    Finished = auto()
    Error = auto()
    Paused = auto()
    Playing = auto()


@dataclass
class Audio:
    AudioPath: str
    Volume: float  # 0 to 1

    Position: [int, int]
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


CHANNEL_ADDER = 4

def percentage(whole, percts):
    return (whole / 100) * percts

def get_percentage(whole, number):
    return number / (whole / 100)


class AudioEngine2D:
    def __init__(self, max_channels=32):
        self.uuid = str(uuid4())
        self.loaded = {}
        self.sounds: List[Audio] = []
        self.__running = False
        self.__listener_position = [0, 0]
        self.__to_pause: List[mixer.Channel] = []
        self.__to_unpause: List[mixer.Channel] = []
        self.MAX_CHANNELS = max_channels
        mixer.pre_init(44100, -16, 2, 4096)
        mixer.init()
        mixer.set_num_channels(self.MAX_CHANNELS)

    def start(self):
        self.__running = True
        t = threading.Thread(target=self.update)
        t.start()

    def stop(self):
        self.__running = False

    def set_listener_position(self, position):
        self.__listener_position = position

    def distance_to_sound(self, distance, maxdistance):
        return 1 - (19 / 20) * math.log(distance / maxdistance + 0.1, 10)

    def distance(self, d1, d2):
        return math.sqrt((d2[0] - d1[0]) ** 2 + (d2[1] - d1[1]) ** 2)

    def update(self):
        while self.__running:
            for audio in self.sounds.copy():
                # Pause / Unpause
                for paused_channel in self.__to_pause.copy():
                    if paused_channel == audio.Channel:
                        audio.Status = SoundState.Paused
                        audio.Channel.pause()
                        self.__to_pause.pop(self.__to_pause.index(paused_channel))
                        logging.info(f" Paused {audio.AudioPath}")
                for unpaused_channel in self.__to_unpause:
                    if unpaused_channel == audio.Channel:
                        audio.Status = SoundState.Playing
                        audio.Channel.unpause()
                        self.__to_unpause.pop(self.__to_unpause.index(unpaused_channel))
                        logging.info(f" Unpaused {audio.AudioPath}")

                if audio.Channel is not None:
                    if audio.Volume != audio.get_channel_vol():
                        audio.Channel.set_volume(audio.Volume)
                        audio.set_channel_vol(audio.Volume)
                    if audio.Channel.get_busy():
                        audio_pos = audio.Position
                        listener_pos = self.__listener_position
                        dist = self.distance(audio_pos, listener_pos)
                        if dist < audio.AudioRange:
                            continue
                        volume = self.distance_to_sound(dist, audio.AudioRange)
                        if volume < 0:
                            volume = 0
                        perc = get_percentage(1.0, volume)
                        conv = percentage(audio.Volume, perc)
                        audio.Channel.set_volume(conv)
                        #logging.info(f" {conv}")
                        continue
                    if not audio.Channel.get_busy() and audio.Status == SoundState.Playing:
                        audio.Status = SoundState.Finished
                        self.sounds.pop(self.sounds.index(audio))
                        logging.info(f"Disposing {audio.AudioPath}")
                        continue
                load = mixer.Sound(audio.AudioPath)
                print(load)
                channel = mixer.find_channel()
                if channel is None:
                    self.MAX_CHANNELS += CHANNEL_ADDER
                    mixer.set_num_channels(self.MAX_CHANNELS)
                    channel = mixer.find_channel()
                    logging.info(f"raising the maximum of channels to {self.MAX_CHANNELS}")
                audio.Channel = channel
                audio.Status = SoundState.Playing
                channel.play(load)
                channel.set_volume(audio.Volume)
                audio._CHANNEL_VOLUME_SET = audio.Volume

    def get_playing(self) -> List[Audio]:
        audios = []
        for audio in self.sounds:
            if audio.Status == SoundState.Playing:
                audios.append(audio)
        return audios

    def pause(self, channel: mixer.Channel):
        self.__to_pause.append(channel)

    def unpause(self, channel: mixer.Channel):
        self.__to_unpause.append(channel)

    def remove_song(self, aud: Audio or mixer.Channel):
        try:
            if isinstance(aud, Audio):
                chan = aud.Channel
                if chan is None:
                    logging.warning(f"Channel is not set in audio")
                    self.sounds.pop(self.sounds.index(aud))
                    return
                chan.stop()
            else:
                chan = aud
                chan.stop()
                for audio in self.sounds.copy():
                    if audio.Channel == chan:
                        self.sounds.pop(self.sounds.index(audio))
                        break
        except ValueError:
            logging.warning(f"Could not find this audio")

    def add(self, audio: Audio):
        self.sounds.append(audio)

    def get_channel_by_name(self, playing_name) -> mixer.Channel:
        for audio in self.sounds:
            if playing_name in audio.AudioPath.lower():
                return audio.Channel

    def get_audio_by_name(self, playing_name) -> Audio:
        for audio in self.sounds:
            if playing_name in audio.AudioPath.lower():
                return audio
