#!/bin/bash
# builds a source distribution
rm playscii_source.zip
zip -ur9 playscii_source.zip . -i '*.py' 'charsets/*' 'palettes/*' 'scripts/*.arsc' 'shaders/*.glsl' 'ui/*.png' 'readme.txt' '*.default' 'license.txt' '*.bat' 'zip_src.sh' 'art/hello2.psci' 'art/owell.ed' 'games/test1/*.*'
