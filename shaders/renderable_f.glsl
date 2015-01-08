#version 130

uniform sampler2D charset;
uniform sampler2D palette;
// width of the generated palette texture, ie palette.MAX_COLORS
uniform float palTextureWidth;

in vec2 texCoords;
in float theFgColorIndex;
in float theBgColorIndex;

out vec4 outColor;

void main()
{
	outColor = texture2D(charset, texCoords);
	// look up fg/bg colors from palette texture
	vec2 colorUV = vec2(0.0, 0.0);
	colorUV.x = theFgColorIndex / palTextureWidth;
	vec4 fgColor = texture2D(palette, colorUV);
	// multiple charset pixel value by FG color
	// tinting >1 color charsets isn't officially supported but hey
	outColor.rgb *= fgColor.rgb;
	// any totally transparent pixels get the BG color
	colorUV.x = theBgColorIndex / palTextureWidth;
	vec4 bgColor = texture(palette, colorUV);
	if ( outColor.a == 0.0 ) {
		outColor = bgColor;
	}
}
