"""
Loop through all of the art files in the specified directory and convert+save
them using the playscii file format.
"""
from playscii import *
from formats.in_txt import TextImporter

# get paths for config file, later to be passed into Application
config_dir, documents_dir, cache_dir = get_paths()
# start logger even before Application has initialized so we can write to it
# startup message: application and version #
logger = Logger(config_dir)
logger.log("%s v%s" % (APP_NAME, get_version()))
# see if "autoplay this game" file exists and has anything in it
autoplay_game = None
if os.path.exists(AUTOPLAY_GAME_FILENAME):
    ap = open(AUTOPLAY_GAME_FILENAME).readlines()
    if len(ap) > 0:
        autoplay_game = ap[0].strip()
# load in config - may change above values and submodule class defaults
cfg_filename = config_dir + CONFIG_FILENAME
logger.log("Loading config from %s..." % cfg_filename)
# execute cfg line by line so we can continue past lines with errors.
# this does mean that commenting out blocks with triple-quotes fails,
# but that's not a good practice anyway.
cfg_lines = open(cfg_filename).readlines()
# compile a new cfg with any error lines stripped out
new_cfg_lines = []
for i, cfg_line in enumerate(cfg_lines):
    cfg_line = cfg_line.strip()
    exec(cfg_line)
    new_cfg_lines.append(cfg_line + "\n")

new_cfg = open(cfg_filename, "w")
new_cfg.writelines(new_cfg_lines)
new_cfg.close()
logger.log("Config loaded.")
art_to_load, game_dir_to_load, state_to_load = None, None, None
app = Application(
    config_dir,
    documents_dir,
    cache_dir,
    logger,
    art_to_load or DEFAULT_ART_FILENAME,
    game_dir_to_load,
    state_to_load,
    autoplay_game,
)

# Everything above this point was boilerplate to get the app object
directory = sys.argv[1]
for filename in os.listdir(directory):
    if not filename.endswith(".txt"):
        continue
    print(f"Loading {filename}")
    importer = TextImporter(app, os.path.join(directory, filename))
    importer.art.save_to_file()

