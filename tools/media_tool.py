import platform

OS_NAME = platform.system()

if OS_NAME == "Windows":
    from .system.windows.media import (
        play_youtube_music,
        global_music_play,
        global_music_pause,
        global_music_next,
        global_music_previous
    )
elif OS_NAME == "Linux":
    from .system.linux.media import (
        play_youtube_music,
        global_music_play,
        global_music_pause,
        global_music_next,
        global_music_previous
    )
else:
    print(f"ADVERTENCIA: Jarvis: Sistema operativo no soportado para media_tool ({OS_NAME})")
    def play_youtube_music(params): pass
    def global_music_play(params=None): pass
    def global_music_pause(params=None): pass
    def global_music_next(params=None): pass
    def global_music_previous(params=None): pass