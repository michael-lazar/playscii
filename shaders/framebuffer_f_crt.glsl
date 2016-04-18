// CRT shader via Mattias Gustavsson - https://www.shadertoy.com/view/lsB3DV
// (screen warp, scanlines, and vignetting removed)

precision mediump float;

uniform sampler2D fbo_texture;
uniform float elapsed_time;
uniform vec2 resolution;
out vec4 f_outPixel;

vec3 sample( sampler2D tex, vec2 tc )
{
    // FIXME: apparently tons of these "dependent texture reads" are what
    // kills linux intel GPU perf
    vec3 s = pow(texture(tex,tc).rgb, vec3(2.2));
    return s;
}

vec3 blur(sampler2D tex, vec2 tc, float offs)
{
    vec4 xoffs = offs * vec4(-2.0, -1.0, 1.0, 2.0) / resolution.x;
    vec4 yoffs = offs * vec4(-2.0, -1.0, 1.0, 2.0) / resolution.y;
    
    // remember: GLSL is picky about casts, every # literal should be a float!  
    vec3 color = vec3(0.0, 0.0, 0.0);

    color += sample(tex,tc + vec2(xoffs.x, yoffs.x)) * 0.00366;
    color += sample(tex,tc + vec2(xoffs.y, yoffs.x)) * 0.01465;
    color += sample(tex,tc + vec2(    0.0, yoffs.x)) * 0.02564;
    color += sample(tex,tc + vec2(xoffs.z, yoffs.x)) * 0.01465;
    color += sample(tex,tc + vec2(xoffs.w, yoffs.x)) * 0.00366;

    color += sample(tex,tc + vec2(xoffs.x, yoffs.y)) * 0.01465;
    color += sample(tex,tc + vec2(xoffs.y, yoffs.y)) * 0.05861;
    color += sample(tex,tc + vec2(    0.0, yoffs.y)) * 0.09524;
    color += sample(tex,tc + vec2(xoffs.z, yoffs.y)) * 0.05861;
    color += sample(tex,tc + vec2(xoffs.w, yoffs.y)) * 0.01465;

    color += sample(tex,tc + vec2(xoffs.x, 0.0)) * 0.02564;
    color += sample(tex,tc + vec2(xoffs.y, 0.0)) * 0.09524;
    color += sample(tex,tc + vec2(    0.0, 0.0)) * 0.15018;
    color += sample(tex,tc + vec2(xoffs.z, 0.0)) * 0.09524;
    color += sample(tex,tc + vec2(xoffs.w, 0.0)) * 0.02564;

    color += sample(tex,tc + vec2(xoffs.x, yoffs.z)) * 0.01465;
    color += sample(tex,tc + vec2(xoffs.y, yoffs.z)) * 0.05861;
    color += sample(tex,tc + vec2(    0.0, yoffs.z)) * 0.09524;
    color += sample(tex,tc + vec2(xoffs.z, yoffs.z)) * 0.05861;
    color += sample(tex,tc + vec2(xoffs.w, yoffs.z)) * 0.01465;

    color += sample(tex,tc + vec2(xoffs.x, yoffs.w)) * 0.00366;
    color += sample(tex,tc + vec2(xoffs.y, yoffs.w)) * 0.01465;
    color += sample(tex,tc + vec2(    0.0, yoffs.w)) * 0.02564;
    color += sample(tex,tc + vec2(xoffs.z, yoffs.w)) * 0.01465;
    color += sample(tex,tc + vec2(xoffs.w, yoffs.w)) * 0.00366;

    return color;
}

// http://stackoverflow.com/questions/4200224/random-noise-functions-for-glsl
float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main(void) {
    vec2 q = gl_FragCoord.xy / resolution.xy;
    vec2 uv = q;
    vec3 oricol = texture( fbo_texture, vec2(q.x,q.y) ).xyz;
    float orialpha = texture( fbo_texture, vec2(q.x,q.y) ).a;
    vec3 col;
    // warbley in X
    float x = sin(0.1*elapsed_time+uv.y*21.0)*sin(0.23*elapsed_time+uv.y*29.0)*sin(0.3+0.11*elapsed_time+uv.y*31.0)*0.0017;
    // tone it waay down
    x *= 0.05;
    float o = 2.0*mod(gl_FragCoord.y,1.0)/resolution.x;
    x += o;
    col.r = 1.0*blur(fbo_texture,vec2(x+uv.x+0.0009,uv.y+0.0009),1.2).x+0.005;
    col.g = 1.0*blur(fbo_texture,vec2(x+uv.x+0.000,uv.y-0.0015),1.2).y+0.005;
    col.b = 1.0*blur(fbo_texture,vec2(x+uv.x-0.0015,uv.y+0.000),1.2).z+0.005;
    col.r += 0.2*blur(fbo_texture,vec2(x+uv.x+0.0009,uv.y+0.0009),2.25).x-0.005;
    col.g += 0.2*blur(fbo_texture,vec2(x+uv.x+0.000,uv.y-0.0015),1.75).y-0.005;
    col.b += 0.2*blur(fbo_texture,vec2(x+uv.x-0.0015,uv.y+0.000),1.25).z-0.005;
    float ghs = 0.05;
    col.r += ghs*(1.0-0.299)*blur(fbo_texture,0.75*vec2(x-0.01, -0.027)+vec2(uv.x+0.001,uv.y+0.001),7.0).x;
    col.g += ghs*(1.0-0.587)*blur(fbo_texture,0.75*vec2(x+-0.022, -0.02)+vec2(uv.x+0.000,uv.y-0.002),5.0).y;
    col.b += ghs*(1.0-0.114)*blur(fbo_texture,0.75*vec2(x+-0.02, -0.0)+vec2(uv.x-0.002,uv.y+0.000),3.0).z;
    col = clamp(col*0.4+0.6*col*col*1.0,0.0,1.0);
    col *= vec3(0.95,1.05,0.95);
    col = mix( col, col * col, 0.3) * 3.8;
    col *= 1.0+0.0015*sin(300.0*elapsed_time);
    col*=1.0-0.15*vec3(clamp((mod(gl_FragCoord.x+o, 2.0)-1.0)*2.0,0.0,1.0));
    col *= vec3( 1.0 ) - 0.25*vec3( rand( uv+0.0001*elapsed_time),  rand( uv+0.0001*elapsed_time + 0.3 ),  rand( uv+0.0001*elapsed_time+ 0.5 )  );
    col = pow(col, vec3(0.45));
    if (uv.x < 0.0 || uv.x > 1.0)
        col *= 0.0;
    if (uv.y < 0.0 || uv.y > 1.0)
        col *= 0.0;
    // improvise alpha based on source + intensity
    orialpha += (col.r + col.g + col.b) / 3.0;
    f_outPixel = vec4(col,orialpha);
}
