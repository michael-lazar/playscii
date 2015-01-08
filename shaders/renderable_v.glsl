#version 130

uniform mat4 projection;
uniform mat4 view;
//uniform mat4 rotation;
//uniform mat4 scale;
uniform int charMapWidth;
uniform int charMapHeight;

uniform float charUVWidth;
uniform float charUVHeight;

attribute vec3 vertPosition;
attribute float charIndex;
attribute vec2 uvMod;
attribute float fgColorIndex;
attribute float bgColorIndex;

out vec2 texCoords;
out float theFgColorIndex;
out float theBgColorIndex;

void main()
{
	gl_Position = projection * view * vec4(vertPosition, 1);
    float tileX = mod(charIndex, charMapWidth);
    float tileY = charMapHeight - floor(charIndex / charMapWidth);
    vec2 uv0 = vec2(tileX * charUVWidth, tileY * charUVHeight);
    vec2 uv1 = vec2(uvMod.x * charUVWidth, uvMod.y * -charUVHeight);
	texCoords = uv0 + uv1;
	theFgColorIndex = fgColorIndex;
	theBgColorIndex = bgColorIndex;
}
