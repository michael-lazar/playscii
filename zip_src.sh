#!/bin/bash
# builds a source distribution
rm playscii_source.zip
zip -ur9 playscii_source.zip . -i '*.py' 'charsets/*' 'palettes/*' 'scripts/*.arsc' 'shaders/*.glsl' 'ui/*.png' 'README.md' 'profile' '*.default' 'license.txt' 'code_of_conduct.txt' '*.bat' 'zip_src.sh' 'art/*' 'games/*.*' -x '*/__pycache__*'
