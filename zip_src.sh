#!/bin/bash
# builds a source distribution
rm playscii_source*.zip
zip -ur9 playscii_source.zip . -i@zip_src_include -x '*/__pycache__*'
# put all this in a containing directory
# TODO: this feels like a super kludgy way to do this, find out a better way
mkdir playscii
cd playscii
unzip ../playscii_source.zip
cd ..
rm playscii_source.zip
# zip and put itch manifest at same level as playscii/ dir
zip -ur9 playscii_source-`cat version`.zip playscii/* .itch.toml
rm -rf playscii/
