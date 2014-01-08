convert \
	'image_sample.png' \
	-size %wx%h \
	-font './helvetica-ultra-compressed.ttf' \
	-pointsize 100 \
	-fill white \
	-stroke gray \
	-gravity SouthEast \
	-interline-spacing 15 \
	-annotate 0x10+20+20 'Licensed Practical Nurse\nSimulator 2014' \
	output.png
