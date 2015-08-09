# PLAYSCII - an ASCII art tool

Playscii (pronounced play-skee) is the successor to EDSCII.  It's still in
development and may not be feature-complete yet.  The latest version will
always be available here:

* [http://jp.itch.io/playscii](http://jp.itch.io/playscii)
* [https://bitbucket.org/JPLeBreton/playscii](https://bitbucket.org/JPLeBreton/playscii)


## Running

If you downloaded the ZIP file with "win32" in its name, you should have a
Windows EXE build you can run without needing to install anything listed below.
A Mac application bundle file isn't available yet but I'd love to make one
available in the near future.

If you downloaded the ZIP file with "source" in its name or from the project's
source code repository, you can run Playscii from source if you have Python and
a few libraries installed.  See the "Running from Source" and "Building"
sections below.


## Usage

If you double-click the Playscii executable or run it from the command line
with no extra arguments, the program will open a new, blank file.  You can also
run it from the command line with the art file you'd like to open.  .PSCI files
are Playscii's native format, and files with a .ED extension made with EDSCII
can also be opened though they will be saved in the new format - as of version
0.5.0 Playscii is a complete replacement for EDSCII.


## Roadmap

Many of Playscii's intended features have now been implemented, but you can see
the very latest version of JP's TODO file here:

[https://bitbucket.org/JPLeBreton/playscii/src/default/docs/todo.txt](https://bitbucket.org/JPLeBreton/playscii/src/default/docs/todo.txt)


## Controls

Every keyboard shortcut available in Playscii is also shown in its pulldown
menus, so you can figure out a lot by just exploring those.  Binds can also
be changed, see the Configuration section below.

`Middle mouse drag` or `Shift + W A S D` or `Shift + arrow keys`: **Pan** the view around

`Mouse` or `arrow keys`: **Move** the cursor around

`Left mouse button` or `enter`: paint using the current tool

`Mouse wheel` or `Shift + Z` or `X`: **Zoom** the view in and out

`Space`: bring up the **Popup**.  This provides quick access to the characters and colors available in the current document.  Tool settings are available in
a separate tab.

`A`: select **Paint** tool - lays down tiles with the currently selected character, foreground and background color, and character "transform": normal, rotated 90 degrees, rotated 180, 270, mirrored, flipped.

`E`: select **Erase** tool - erases character and foreground for tiles to selected background color, including transparency.

`R`: select **Rotate** tool - painting tiles with this rotates them 90 degrees, multiple passes produce the 4 possible rotations.

`T`: select **Text** tool - click on a tile and start typing in characters, arrow keys move cursor and enter skips to next line down.  Escape ends the edit.

`S`: select **Select** tool - click and drag to select tiles.  Cut and Copy operate on the selected area, and Paint/Erase/etc operations will only affect the selected area.

`V`: select **Paste** tool - tiles previously Cut or Copied will appear on the brush as a stamp which you can paint with like any other tool.

`3` or `#`: cycle the currently selected **character** forward or backward through the character set

`4` or `$`: cycle the currently selected **foreground color** forward or backward through the palette

`5` or `%`: same as above but for the currently selected **background color**

`6` or `^`: cycle through **character transforms**, eg rotations and flips

`W`: **swap** currently selected foreground and background colors

`C`: toggle whether current tool affects **characters** or not

`F`: toggle whether current tool affects **foreground color** or not

`B`: toggle whether current tool affects **background color** or not

`X`: toggle whether current tool affects **character transform** or not

`Right mouse button` or `Q`: **Grab** the character and colors the from cursor's current tile, akin to the eyedropper tool in other paint programs

`Ctrl-X`: **Cut** - deletes current selection contents and switches to Paste tool with those contents in the clipboard.

`Ctrl-C`: **Copy** - same as Cut but doesn't delete the tiles selected

`ESC` or `Ctrl-D`: **Clear** current selection with no changes

`Ctrl-A`: Select all

`Ctrl-D`: Deselect all

`Ctrl-I`: Invert selection

`Shift-R`: toggle CRT shader

`Shift-G`: toggle grid

`` ` ``: toggle console.  Type "help" to see a list of available commands.

`Alt-Enter`: toggle fullscreen (uses desktop resolution)

`Ctrl -` or `Ctrl +`: decrease/increase UI draw scale

`Shift-U`: toggle UI

`<` or `>`: rewind/advance currently animation frame

`P`: pause/play current animation if art has multiple frames

`[` or `]`: change actively edited layer

`Ctrl-E`: export current art to PNG

`Ctrl-S`: save current art

`F12`: take screenshot

`Ctrl-Q`: quit


## Running from Source

Running from source is only recommended if a binary isn't available for your OS
and/or you want to play with the very latest version.  If you're doing so,
you'll need some version of Python 3 - sorry, Python 2 is not supported - and
the following libraries:

* PySDL2: [https://bitbucket.org/marcusva/py-sdl2/overview](https://bitbucket.org/marcusva/py-sdl2/overview)

* PyOpenGL: [http://pyopengl.sourceforge.net](http://pyopengl.sourceforge.net)

* Numpy: [http://www.numpy.org](http://www.numpy.org)

* Python Image Library (PIL) or one of its derivatives, eg Pillow: [https://github.com/python-pillow/Pillow](https://github.com/python-pillow/Pillow)

* appdirs: [https://github.com/ActiveState/appdirs](https://github.com/ActiveState/appdirs)

These libraries are all pretty easy to install using PIP, the package manager
that comes with Python 3.4 and later.  Find the pip executable and run it from
the command line, like so:

`pip install pysdl2 pyopengl numpy pillow appdirs`

In Windows the pip executable is in the `Scripts\` subdirectory of your Python
install folder, eg `c:\Python34`.  On some Unix-like systems (Linux and maybe
OSX) the pip binary to run may be called "pip3" to distinguish it from any
Python 2 installations.  On Unix-like systems you may also need to run pip as
super user to let it install system libraries, eg by pre-pending "sudo" to the
command above.

Once you have the dependencies installed, you can run Playscii from source
like so:

`python playscii.py [optional name of art file to open]`


## Building

To produce Windows EXE builds, in addition to the above dependencies you'll
also need py2exe: [http://www.py2exe.org](http://www.py2exe.org)

Simply run "build.bat" and it will place a complete build in the `dist\`
subdirectory.  You may need to edit your Python and SDL2.dll paths at the very
top of build.bat if they're in a different location.

To produce Mac Application bundles, you'll need py2app: [https://pypi.python.org/pypi/py2app](https://pypi.python.org/pypi/py2app)

As with the Windows build process, run the "mac_build.py" script.


## Configuration

Playscii places its configuration files in OS-appropriate directories, eg
C:\Users\[your username]\AppData\Local\Playscii in Windows 7+,
~/.config/Playscii in Linux, etc.

Documents (your art, color palettes, etc) are stored in eg ~/Documents/Playscii
in OSX and Linux, and the appropriate "My Documents" folder in Windows.

You can override many program defaults in the file playscii.cfg.  This file
starts with a few possible commented-out overrides to get you started.

Likewise you can change Playscii's keyboard command binds in binds.cfg.


## Game Mode

In addition to its art and animation capabilities, Playscii has a Game Mode
that allows you to write Python code to determine the behavior of game objects.
Game objects are represented by pieces of Playscii art, so you can edit your
art and animation assets on-the-fly and see your changes reflected back in
game mode instantly.

Game mode is still in heavy development, and a full documentation pass will
only make sense once its features have stabilized.  In the meantime, if you're
interested in exploring it further you can check out the two very basic
example games included with Playscii in the application's games/ directory,
"test1" and "cronotest".  Levels are stored as game state saves with a .GS
extension, Python scripts defining new types of GameObject are stored in the
scripts/ subdirectory, and art assets are stored in subdirs analogous to the
ones used outside of game mode.

If you've used game mode and have any suggestions, please let JP know!
[http://vectorpoem.com/contact.html](http://vectorpoem.com/contact.html)

<3
