#!/bin/bash
# builds a source distribution
rm playscii_source.zip
zip -ur9 playscii_source.zip . -i '*.py' 'charsets/*' 'palettes/*' 'scripts/*.arsc' 'shaders/*.glsl' 'ui/*.png' 'readme.txt' '*.default' 'license.txt' 'code_of_conduct.txt' '*.bat' 'zip_src.sh' 'art/hello2.psci' 'art/owell.ed' 'art/new.psci' 'art/blob_shadow.psci' 'games/test1/*.*' 'games/cronotest/*.*'
