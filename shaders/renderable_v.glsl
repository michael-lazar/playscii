#version 130

uniform mat4 projection;
uniform mat4 view;
//uniform mat4 rotation;
//uniform mat4 scale;
uniform int charMapWidth;
uniform int charMapHeight;

uniform float charUVWidth;
uniform float charUVHeight;

in vec3 vertPosition;
in float charIndex;
in vec2 uvMod;
//const int fgColorIndex = 0;
//const int bgColorIndex = 15;

out vec2 texCoords;
//out int theFgColorIndex;
//out int theBgColorIndex;

void main()
{
	gl_Position = projection * view * vec4(vertPosition, 1);
	
	// ian maclarty
    float tileX = mod(charIndex, charMapWidth);
    float tileY = charMapHeight - floor(charIndex / charMapWidth);
	
	// STB - cool tricks with int bits
	//float tileX = float(charIndex & charMapWidth-1);
	//float tileY = float(charMapHeight - (charIndex >> 4) & charMapHeight-1);
	
	// goldbuick
	//float tileX = mod(float(charIndex), charMapWidth);
	//float tileY = floor(float(charIndex) / charMapWidth);
	
	// TEST: plug values in directly
	//tileX *= 0.000000001;
	//tileY *= 0.000000001;
	//tileX += charMapWidth - 9;
	//tileX += charIndex - 30;
	//tileY += charMapHeight - 4;
	
    vec2 uv0 = vec2(tileX * charUVWidth, tileY * charUVHeight);
    //vec2 uv0 = vec2(tileX, tileY);
    vec2 uv1 = vec2(uvMod.x * charUVWidth, uvMod.y * -charUVHeight);
	texCoords = uv0 + uv1;
	
	/*
	// compute UVs for given character index
	int tileXi = mod(charIndex, charMapWidth);
	float tileX = float(tileXi);
	//float tileX = float(tileXi * 0.0000001) + charIndex;
	//tileX = (tileX * 0.000001) + (float(charIndex) - 32.0);
	float tileY = charMapHeight - ((charIndex - tileX) / charMapHeight);
	tileY = (tileY * 0.000000001) - 13;
	vec2 uv0 = vec2(tileX * charUVWidth, tileY * -charUVHeight);
	//vec2 uv0 = vec2(tileX, tileY);
	vec2 uv1 = vec2(uvMod.x * charUVWidth, uvMod.y * -charUVHeight);
	*/
}
