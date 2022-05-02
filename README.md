# PygameAudioEngine
Just a wrapper for pygame mixer adding 2D audio with distance dropoff
 
```py
from main import AudioEngine2D, Audio
import pygame

ae = AudioEngine2D()
            # Filepath, volume, Sound Position, Sound range
sound_effect = Audio("sfx.ogg", 0.05, [200, 200], 20)
# for preloaded sound just make a mixer.Sound and save it with special function
sound_effect_sound = mixer.Sound("KILLKA.ogg")

# ae.add(sound_effect) to do this automatically

ae.add_preloaded(sound_effect, sound_effect_sound)

# if you're using this with pygame create your screen before ae.start() there's some weird bug so that pygame window won't show
# until like 10-15 seconds later

screen = pygame.display.set_mode((1280, 720))

ae.start() # <- running on another thread

# ... do anything if you want to play sound effects again just ae.add_preloaded(sound_effect, sound_effect_sound) or ae.add

```
