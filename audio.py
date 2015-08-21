
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
    
    def reset(self):
        if hasattr(self, 'musics'):
            for music in self.musics.values():
                sdlmixer.Mix_FreeMusic(music)
        self.musics = {}
        self.current_music = None
        if hasattr(self, 'sounds'):
            for sound in self.sounds.values():
                sdlmixer.Mix_FreeChunk(sound)
        self.sounds = {}
    
    def destroy(self):
        self.stop_all_music()
        self.reset()
        sdlmixer.Mix_CloseAudio()
        sdlmixer.Mix_Quit()
