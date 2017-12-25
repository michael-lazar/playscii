
import ctypes
from sdl2 import sdlmixer

class PlayingSound:
    "represents a currently playing sound"
    def __init__(self, filename, channel, game_object, looping=False):
        self.filename = filename
        self.channel = channel
        self.go = game_object
        self.looping = looping

class AudioLord:
    
    sample_rate = 44100
    
    def __init__(self, app):
        self.app = app
        # initialize audio
        sdlmixer.Mix_Init(sdlmixer.MIX_INIT_OGG|sdlmixer.MIX_INIT_MOD)
        sdlmixer.Mix_OpenAudio(self.sample_rate, sdlmixer.MIX_DEFAULT_FORMAT,
                               2, 1024)
        self.reset()
        # sound callback
        # retain handle to C callable even though we don't use it directly
        self.sound_cb = ctypes.CFUNCTYPE(None, ctypes.c_int)(self.channel_finished)
        sdlmixer.Mix_ChannelFinished(self.sound_cb)
    
    def channel_finished(self, channel):
        # remove sound from dicts of playing channels and sounds
        old_sound = self.playing_channels.pop(channel)
        self.playing_sounds[old_sound.filename].remove(old_sound)
        # remove empty list
        if self.playing_sounds[old_sound.filename] == []:
            self.playing_sounds.pop(old_sound.filename)
    
    def reset(self):
        self.stop_all_music()
        self.stop_all_sounds()
        # current playing sounds, of form:
        # {'filename': [list of PlayingSound objects]}
        self.playing_sounds = {}
        # current playing channels, of form:
        # {channel_number: PlayingSound object}
        self.playing_channels = {}
        # handle init case where self.musics doesn't exist yet
        if hasattr(self, 'musics'):
            for music in self.musics.values():
                sdlmixer.Mix_FreeMusic(music)
        self.musics = {}
        if hasattr(self, 'sounds'):
            for sound in self.sounds.values():
                sdlmixer.Mix_FreeChunk(sound)
        self.sounds = {}
    
    def register_sound(self, sound_filename):
        if sound_filename in self.sounds:
            return self.sounds[sound_filename]
        new_sound = sdlmixer.Mix_LoadWAV(bytes(sound_filename, 'utf-8'))
        self.sounds[sound_filename] = new_sound
        return new_sound
    
    def object_play_sound(self, game_object, sound_filename,
                          loops=0, allow_multiple=False):
        # TODO: volume param? sdlmixer.MIX_MAX_VOLUME if not specified
        # bail if same object isn't allowed to play same sound multiple times
        if not allow_multiple and sound_filename in self.playing_sounds:
            for playing_sound in self.playing_sounds[sound_filename]:
                if playing_sound.go is game_object:
                    return
        sound = self.register_sound(sound_filename)
        channel = sdlmixer.Mix_PlayChannel(-1, sound, loops)
        # add sound to dicts of playing sounds and channels
        new_playing_sound = PlayingSound(sound_filename, channel, game_object,
                                         loops == -1)
        if sound_filename in self.playing_sounds:
            self.playing_sounds[sound_filename].append(new_playing_sound)
        else:
            self.playing_sounds[sound_filename] = [new_playing_sound]
        self.playing_channels[channel] = new_playing_sound
    
    def object_stop_sound(self, game_object, sound_filename):
        if not sound_filename in self.playing_sounds:
            return
        # stop all instances of this sound object might be playing
        for sound in self.playing_sounds[sound_filename]:
            if game_object is sound.go:
                sdlmixer.Mix_HaltChannel(sound.channel)
    
    def object_stop_all_sounds(self, game_object):
        sounds_to_stop = []
        for sound_filename,sounds in self.playing_sounds.items():
            for sound in sounds:
                if sound.go is game_object:
                    sounds_to_stop.append(sound_filename)
        for sound_filename in sounds_to_stop:
            self.object_stop_sound(game_object, sound_filename)
    
    def stop_all_sounds(self):
        sdlmixer.Mix_HaltChannel(-1)
    
    def set_music(self, music_filename):
        if music_filename in self.musics:
            return
        new_music = sdlmixer.Mix_LoadMUS(bytes(music_filename, 'utf-8'))
        self.musics[music_filename] = new_music
    
    def start_music(self, music_filename, loops=-1):
        # TODO: fade in support etc
        music = self.musics[music_filename]
        sdlmixer.Mix_PlayMusic(music, loops)
        self.current_music = music_filename
    
    def pause_music(self):
        if self.current_music:
            sdlmixer.Mix_PauseMusic()
    
    def resume_music(self):
        if self.current_music:
            sdlmixer.Mix_ResumeMusic()
    
    def stop_music(self, music_filename):
        # TODO: fade out support
        sdlmixer.Mix_HaltMusic()
        self.current_music = None
    
    def is_music_playing(self):
        return bool(sdlmixer.Mix_PlayingMusic())
    
    def resume_music(self):
        if self.current_music:
            sdlmixer.Mix_ResumeMusic()
    
    def stop_all_music(self):
        sdlmixer.Mix_HaltMusic()
        self.current_music = None
    
    def update(self):
        if self.current_music and not self.is_music_playing():
            self.current_music = None
    
    def destroy(self):
        self.reset()
        sdlmixer.Mix_CloseAudio()
        sdlmixer.Mix_Quit()
