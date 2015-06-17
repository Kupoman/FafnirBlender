#version 330


uniform mat4 view_matrix;
uniform mat4 proj_matrix;

in vec3 vertex;

out vec3 in_vertex;
out vec3 in_ray_o;
out vec3 in_ray_d;
out vec3 in_ray_inv;

void main()
{
	in_vertex = vertex;

	mat4 inv_view_mat = inverse(view_matrix);
	in_ray_o = (inv_view_mat * vec4(0.0, 0.0, 0.0, 1.0)).xyz;

	mat4 inv_proj_mat = inverse(proj_matrix);
	vec4 ray_d = inv_proj_mat * vec4(vertex, 1.0);
	// ray_d /= ray_d.w;
	in_ray_d = (inv_view_mat * vec4(ray_d.xyz, 0.0)).xyz;
	in_ray_inv = vec3(1.0) / in_ray_d;

	gl_Position = vec4(vertex, 1.0);
}