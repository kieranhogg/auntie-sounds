mkdir -p icons-output

for src in dark/*.png; do
    name=$(basename "$src" .png)

    magick \
        -size 512x512 xc:none \
        -fill white \
        -stroke black \
        -strokewidth 8 \
        -draw 'roundrectangle 8,8 504,504 38,38' \
        "$src" \
        -compose over \
        -composite \
        "icons-output/${name}.png"
done
