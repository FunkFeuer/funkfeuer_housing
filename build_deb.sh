#!/bin/sh

VERSION=`cat version`

# clean up from last build
rm -r deb_dist
rm -r dist

# build binary package
# rm -r deb_dist
# python setup.py --command-packages=stdeb.command bdist_deb

python setup.py sdist
py2dsc-deb dist/funkfeuer-housing*.tar.gz
cp debian/py3dist-overrides deb_dist/funkfeuer-housing-0.2/debian/
cd deb_dist/funkfeuer-housing-0.2/
dpkg-buildpackage -b --no-sign
