uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec3 objectScale;
uniform int charMapWidth;
uniform int charMapHeight;

uniform float charUVWidth;
uniform float charUVHeight;

in vec3 vertPosition;
in float charIndex;
in vec2 uvMod;
in float fgColorIndex;
in float bgColorIndex;

out vec2 texCoords;
out float theFgColorIndex;
out float theBgColorIndex;

mat4 scale(float x, float y, float z)
{
    return mat4(
        vec4(x,   0.0, 0.0, 0.0),
        vec4(0.0, y,   0.0, 0.0),
        vec4(0.0, 0.0, z,   0.0),
        vec4(0.0, 0.0, 0.0, 1.0)
    );
}

void main()
{
	vec4 model = vec4(vertPosition, 1);
	model *= scale(objectScale.x, objectScale.y, objectScale.z);
	model += vec4(objectPosition, 0);
	gl_Position = projection * view * model;
	// translate 1D character index into tile UV coordinates
	// thanks Ian MacLarty, Sean Barrett and goldbuick for help with this!
    float tileX = mod(charIndex, charMapWidth);
    float tileY = charMapHeight - floor(charIndex / charMapWidth);
    vec2 uv0 = vec2(tileX * charUVWidth, tileY * charUVHeight);
    vec2 uv1 = vec2(uvMod.x * charUVWidth, uvMod.y * -charUVHeight);
	texCoords = uv0 + uv1;
	theFgColorIndex = fgColorIndex;
	theBgColorIndex = bgColorIndex;
}
