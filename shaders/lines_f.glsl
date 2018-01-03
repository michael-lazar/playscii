precision mediump float;

uniform vec4 objectColor;

varying vec4 theColor;

void main()
{
	gl_FragColor = theColor * objectColor;
}
