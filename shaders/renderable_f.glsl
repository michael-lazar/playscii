#version 130

uniform sampler2D charset;
//uniform sampler2D palette;

in vec2 texCoords;
//in int theFgColorIndex;
//in int theBgColorIndex;
//const int theFgColorIndex = 3;
//const int theBgColorIndex = 8;

out vec4 outColor;

void main()
{
	outColor = texture2D(charset, texCoords);
	//outColor.r = texCoords.x;
	//outColor.g = texCoords.y;
	outColor.a = 0.25;
	
	/*
	// this is apparently what passes for debugging in GLSL :]
	if ( texCoords.y > 15.95 ) {
		outColor.r += 0.5;
	}
	if ( texCoords.y < -69190000.0 ) {
		outColor.g += 0.5;
	}
	*/
	
	/*
	vec2 colorUV = vec2(0.0, 0.0);
	
	// TODO: replace magic 255 w/ uniform for palette texture width
	colorUV.x = float(theFgColorIndex) / 255;
	vec4 fgColor = texture(palette, colorUV);
	outColor.rgb = fgColor.rgb;
	
	colorUV.x = float(theBgColorIndex) / 255;
	vec4 bgColor = texture(palette, colorUV);
	if ( outColor.a == 0.0 ) {
		outColor = bgColor;
	}
	*/
}
