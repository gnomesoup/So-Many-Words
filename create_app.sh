mkdir icon.iconset
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 16 -h 16 -o icon.iconset/icon_16x16.png icon_small.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 32 -h 32 -o icon.iconset/icon_16x16@2x.png icon_small.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 32 -h 32 -o icon.iconset/icon_32x32.png icon_small.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 64 -h 64 -o icon.iconset/icon_32x32@2x.png icon_small.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 128 -h 128 -o icon.iconset/icon_128x128.png icon.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 256 -h 256 -o icon.iconset/icon_128x128@2x.png icon.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 256 -h 256 -o icon.iconset/icon_256x256.png icon.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 512 -h 512 -o icon.iconset/icon_256x256@2x.png icon.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 512 -h 512 -o icon.iconset/icon_512x512.png icon.svg
/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 1028 -h 1028 -o icon.iconset/icon_512x512@2x.png icon.svg
iconutil -c icns icon.iconset
rm -R icon.iconset

/Applications/Inkscape.app/Contents/MacOS/Inkscape -w 1028 -h 1028 -o icon.png icon.svg

pyinstaller --icon icon.icns --windowed --onefile --name 'So Many Words' --noconfirm --add-data "./icon.png:." main.py
rm -Rf "./dist/So Many Words"
hdiutil create -srcfolder dist "So Many Words v2023.04.0.dmg"
