PLAYSCII

an ASCII art tool

Playscii (pronounced play-skee) is the successor to EDSCII.  It's still in very early stages of development and may not be too useful as an art tool yet.  The latest version will always be available here:

https://bitbucket.org/JPLeBreton/playscii


== Running ==

If you unpacked this readme from a zip, then you should have a Windows EXE build you can run without needing to install anything listed below.

If you got it from the project's source code repository, you can either run it from source using Python, or make a Windows EXE build.  See the "Running from Source" and "Building" sections below.


== Usage ==

If you double-click the Playscii executable or run it from the command line with no extra arguments, the program will open to a new, blank file.  You can also run it from the command line with the art file you'd like to open.  .PSCI files are Playscii's native format, and files with a .ED extension made with EDSCII can also be opened though they will be saved in the new format.  Eventually Playscii will be a complete replacement for EDSCII.


== Controls ==

W A S D: pan the view around

Mouse / arrow keys: move the cursor around

Left mouse button / enter: paint using the currently selected character, foreground color, and background color

Mouse wheel / Z / X: zoom the view in and out

C/shift-C: cycle the currently selected character forward or backward through the character set

F/shift-F: cycle the currently selected foreground color forward or backward through the palette

B/shift-B: same as above but for the currently selected background color

Right mouse button / Q: "grab" the character and colors the from cursor's current tile, akin to the eyedropper tool in other paint programs

R: toggle CRT shader

G: toggle grid

`: toggle console.  Current valid commands are: open [filename], save [filename], export, char [character set], pal [palette], quit

Shift-T: toggle camera tilt

Alt-Enter: toggle fullscreen (uses desktop resolution)

Ctrl - / +: decrease/increase UI draw scale

Shift-U: toggle UI

< / >: rewind/advance currently animation frame

[ / ]: change actively edited layer

Ctrl E: export current art to PNG

F12: take screenshot


== Running from Source ==

Running from source is only recommended if a binary isn't available for your OS and/or you want to play with the very latest version.  If you're doing so, you'll need some version of Python 3 - sorry, Python 2 is not supported - and the following libraries:

PySDL2: https://bitbucket.org/marcusva/py-sdl2/overview

PyOpenGL: http://pyopengl.sourceforge.net

Numpy: http://www.numpy.org

Python Image Library (PIL) or one of its derivatives, eg Pillow: https://github.com/python-pillow/Pillow

These libraries are all pretty easy to install using PIP, the package manager that comes with Python 3.4 and later.  Find the pip executable and run it from the command line, like so:

pip install pysdl2 pyopengl numpy pillow

In Windows the pip executable is in the Scripts\ subdirectory of your Python install folder, eg c:\Python34.  On some Unix-like systems (Linux and maybe OSX) the pip binary to run may be called "pip3" to distinguish it from any Python 2 installations.  You may also need to run pip as super user to let it install system libraries, eg by pre-pending "sudo" to the command above.

Once you have the dependencies installed, you can run Playscii from source like so:

python playscii.py [optional name of file to open]


== Building ==

To produce Windows EXE builds, in addition to the above dependencies you'll also need py2exe: http://www.py2exe.org

Simply run "build.bat" and it will place a complete build in the dist\ subdirectory.  You may need to edit your Python and SDL2.dll paths at the very top of build.bat if they're in a different location.


== A Brief Roadmap ==

1. Fully usable UI for painting on different layers and frames.

2. Export your art to PNG or animated GIF.

3. Play mode, in which game objects are represented by animating ASCII "sprites".

Bonus: Raster-to-ASCII image conversion a la EDSCII.


Lots to do yet!
