PLAYSCII

an ASCII art tool

Playscii (pronounced play-skee) is the successor to EDSCII.  It's still in very early stages of development and may not be too useful as an art tool yet.  The latest version will always be available here:

https://bitbucket.org/JPLeBreton/playscii


== Running ==

If you unpacked this readme from a zip, then you should have a Windows EXE build you can run without needing to install anything listed below.

If you got it from the project's source code repository, you can either run it from source using Python, or make a Windows EXE build.  See the "Running from Source" and "Building" sections below.


== Usage ==

If you double-click the Playscii executable or run it from the command line with no extra arguments, the program will open a new, blank file.  You can also run it from the command line with the art file you'd like to open.  .PSCI files are Playscii's native format, and files with a .ED extension made with EDSCII can also be opened though they will be saved in the new format - before long Playscii will be a complete replacement for EDSCII.


== Controls ==

Middle mouse drag / Shift + W A S D / Shift + arrow keys: pan the view around

Mouse / arrow keys: move the cursor around

Left mouse button / enter: paint using the current tool

Mouse wheel / Shift + Z / X: zoom the view in and out

A: select Paint tool - lays down tiles with the currently selected character, foreground and background color, and character "transform": normal, rotated 90 degrees, rotated 180, 270, mirrored, flipped.

E: select Erase tool - erases character and foreground for tiles to selected background color, including transparency.

R: select Rotate tool - painting tiles with this rotates them 90 degrees, multiple passes produce the 4 possible rotations.

T: select Text tool - click on a tile and start typing in characters, arrow keys move cursor and enter skips to next line down.  Escape ends the edit.

3/#: cycle the currently selected character forward or backward through the character set

4/$: cycle the currently selected foreground color forward or backward through the palette

5/%: same as above but for the currently selected background color

6/^: cycle through character transforms

W: swap currently selected foreground and background colors

C: toggle whether current tool affects characters or not

F: toggle whether current tool affects foreground color or not

B: toggle whether current tool affects background color or not

X: toggle whether current tool affects character transform or not

Right mouse button / Q: "grab" the character and colors the from cursor's current tile, akin to the eyedropper tool in other paint programs

Shift-R: toggle CRT shader

G: toggle grid

`: toggle console.  Current valid commands are: open [filename], save [filename], export, char [character set], pal [palette], quit

Shift-T: toggle camera tilt

Alt-Enter: toggle fullscreen (uses desktop resolution)

Ctrl - / +: decrease/increase UI draw scale

Shift-U: toggle UI

< / >: rewind/advance currently animation frame

P: pause/play current animation if art has multiple frames

[ / ]: change actively edited layer

Ctrl E: export current art to PNG

Ctrl S: save current art

F12: take screenshot

Ctrl Q: quit


== Running from Source ==

Running from source is only recommended if a binary isn't available for your OS and/or you want to play with the very latest version.  If you're doing so, you'll need some version of Python 3 - sorry, Python 2 is not supported - and the following libraries:

PySDL2: https://bitbucket.org/marcusva/py-sdl2/overview

PyOpenGL: http://pyopengl.sourceforge.net

Numpy: http://www.numpy.org

Python Image Library (PIL) or one of its derivatives, eg Pillow: https://github.com/python-pillow/Pillow

These libraries are all pretty easy to install using PIP, the package manager that comes with Python 3.4 and later.  Find the pip executable and run it from the command line, like so:

pip install pysdl2 pyopengl numpy pillow

In Windows the pip executable is in the Scripts\ subdirectory of your Python install folder, eg c:\Python34.  On some Unix-like systems (Linux and maybe OSX) the pip binary to run may be called "pip3" to distinguish it from any Python 2 installations.  On Unix-like systems you may also need to run pip as super user to let it install system libraries, eg by pre-pending "sudo" to the command above.

Once you have the dependencies installed, you can run Playscii from source like so:

python playscii.py [optional name of art file to open]


== Building ==

To produce Windows EXE builds, in addition to the above dependencies you'll also need py2exe: http://www.py2exe.org

Simply run "build.bat" and it will place a complete build in the dist\ subdirectory.  You may need to edit your Python and SDL2.dll paths at the very top of build.bat if they're in a different location.


== A Brief Roadmap ==

1. Fully usable UI for painting on different layers and frames.

2. Export your art to PNG or animated GIF.

3. Play mode, in which game objects are represented by animating ASCII "sprites".

Bonus: Raster-to-ASCII image conversion a la EDSCII.


Lots to do yet!
