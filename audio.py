
import ctypes
from sdl2 import sdlmixer

class AudioLord:
    
    sample_rate = 44100
    
    def __init__(self, app):
        self.app = app
        # initialize audio
        sdlmixer.Mix_Init(sdlmixer.MIX_INIT_OGG|sdlmixer.MIX_INIT_MOD)
        sdlmixer.Mix_OpenAudio(self.sample_rate, sdlmixer.MIX_DEFAULT_FORMAT,
                               2, 1024)
        self.reset()
        
        #void Mix_ChannelFinished(void (*channel_finished)(int channel))
        
        # TODO: figure out how to properly use this callback
        self.CBFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        # NOTE: Make sure you keep references to CFUNCTYPE() objects as long as they are used from C code.
        self.c_cb = self.CBFUNC(self.channel_finished)
        
        # FIX: the following line crashes
        #sdlmixer.Mix_ChannelFinished(ctypes.byref(self.c_cb))
    
    def channel_finished(self, channel):
        print('channel %s finished' % channel)
    
    def reset(self):
        self.stop_all_music()
        self.stop_all_sounds()
        # dict of objects, containing dicts of filenames + lists of
        # channels playing, eg:
        # { 'Object1': {'sound1.wav': [1, 2, 3]} }
        self.obj_sounds = {}
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
        # TODO: volume param
        #volume = volume if volume != -1 else sdlmixer.MIX_MAX_VOLUME
        
        # bail if given object already playing given sound and we don't allow
        # duplicates of this sound
        object_is_playing_sound = game_object.name in self.obj_sounds
        if not allow_multiple and object_is_playing_sound and sound_filename in self.obj_sounds[game_object.name]:
            return
        sound = self.register_sound(sound_filename)
        channel = sdlmixer.Mix_PlayChannel(-1, sound, loops)
        if game_object.name in self.obj_sounds:
            self.obj_sounds[game_object.name][sound_filename].append(channel)
        else:
            self.obj_sounds[game_object.name] = {sound_filename: [channel]}
    
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
        for obj_name,obj_sounds in self.obj_sounds.items():
            for channel in obj_sounds:
                pass
    
    def destroy(self):
        self.reset()
        sdlmixer.Mix_CloseAudio()
        sdlmixer.Mix_Quit()
