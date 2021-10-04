
This directory stores different HTML templates used for the rendering on
the web browser

**schematic_render.html**
Standalone render with d3HwSchematic, it renders the hwELK JSON in the
schematic format. To render replace JSON variable `ELKJson` in the script
section

**elk_render.html**
Render typical ELK layout in the SVG format.
This is useful while using any other layout kernel than `layerd`

**svg_render.html**
D3 based SVG render with Zoom functionality

**canvas_render.html**
Pixie based rendering on the canvas for more complex structures.
It converts SVG to Canvas and allows faster rendering with limited
interactivity.