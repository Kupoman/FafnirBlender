#version 420
#extension GL_ARB_shader_storage_buffer_object: enable

#define VOXEL

const float epsilon = 0.000001;
const uint LIST_END = 0xFFFFFFFF;

layout(binding=0) uniform usampler3D voxels;
// layout(r32ui, binding = 0) uniform uimage3D voxels;
layout(binding=1) uniform usampler2D link_list;
uniform int num_triangles;

uniform float u_size;
uniform float u_res;

struct Triangle {
	uint v0, v1, v2, pad;
};

layout(std430, binding=0) buffer TriBuffer {
	Triangle tri_buffer[];
};

struct Vertex {
	vec4 position;
	vec4 normal;
};

layout(std430, binding=1) buffer VertBuffer {
	Vertex vertex_buffer[];
};

in vec3 in_vertex;
in vec3 in_ray_o;
in vec3 in_ray_d;
in vec3 in_ray_inv;

out vec3 out_color;

bool trace_list(uint ptr, float closest_t)
{
	Vertex v0, v1, v2;
	vec3 v0p, v1p, v2p;
	Triangle triangle;
	vec3 e0, e1, T, P, Q;
	float det=1.0, inv_det, t, u=1.0, v=1.0;

	float closest_u, closest_v;
	// float closest_t = 1000.0;
	uint closest_tri = -1;

	vec3 ray_d = in_ray_d;

#ifdef VOXEL
	while (ptr != LIST_END) {
		uvec2 link = texelFetch(link_list, ivec2(ptr%1024, ptr/1024), 0).rg;
		triangle = tri_buffer[link.x];
		ptr = link.y;
#else
	uint i = 0;
	for (; i < num_triangles; ++i) {
		triangle = tri_buffer[i];
#endif

		v0 = vertex_buffer[triangle.v0 + triangle.pad];
		v1 = vertex_buffer[triangle.v1 + triangle.pad];
		v2 = vertex_buffer[triangle.v2 + triangle.pad];
		v0p = v0.position.xyz;
		v1p = v1.position.xyz;
		v2p = v2.position.xyz;

		e0 = v1p - v0p;
		e1 = v2p - v0p;

		P = cross(ray_d, e1);
		det = dot(e0, P);

		if (det < epsilon) continue;

		T = in_ray_o - v0p;

		u = dot(T, P);
		if (u < 0.0 || u > det) continue;

		Q = cross(T, e0);

		v = dot(ray_d, Q);
		if (v < 0.0 || u + v > det) continue;


		inv_det = 1.0 / det;

		t = dot(e1, Q) * inv_det;

		if (t < closest_t) {
			closest_t = t;
			closest_u = u * inv_det;
			closest_v = v * inv_det;
#ifdef VOXEL
			closest_tri = link.x;
#else
			closest_tri = i;
#endif
		}
	}
	if (closest_tri != -1) {
		u = closest_u;
		v = closest_v;

		triangle = tri_buffer[closest_tri];

		vec3 pos = vertex_buffer[triangle.v0 + triangle.pad].position.xyz * (1-u-v);
		pos += vertex_buffer[triangle.v1 + triangle.pad].position.xyz * u;
		pos += vertex_buffer[triangle.v2 + triangle.pad].position.xyz * v;

		vec3 norm = vertex_buffer[triangle.v0 + triangle.pad].normal.xyz * (1-u-v);
		norm += vertex_buffer[triangle.v1 + triangle.pad].normal.xyz * u;
		norm += vertex_buffer[triangle.v2 + triangle.pad].normal.xyz * v;

		vec3 L = normalize(vec3(3.0, -4.0, 6.0) - pos);
		vec3 N = normalize(norm);

		out_color = vec3(dot(N, L) * 0.8);
		return true;
	}

	out_color = vec3(0.2, 0.2, 0.2);
	return false;
}

void main()
{
#ifdef VOXEL
	Triangle triangle;
	vec3 uv = vec3(in_vertex.xy * 0.5 + 0.5, 0.5);
	ivec3 mask;

	vec3 ray_d = normalize(in_ray_d);
	vec3 ray_o = in_ray_o / u_size;
	ray_o = ray_o * 0.5 + vec3(0.5);

	// Make sure we are in the voxel grid
	{
		vec3 t1 = -ray_o / ray_d;
		vec3 t2 = (vec3(1.0) - ray_o) / ray_d;
		vec3 v_tmin = min(t1, t2);
		vec3 v_tmax = max(t1, t2);

		float tmin = max(max(v_tmin.x, v_tmin.y), v_tmin.z);
		float tmax = min(min(v_tmax.x, v_tmax.y), v_tmax.z);

		if (tmax >= tmin) {
			if (tmin > 0.0)
				ray_o += (tmin + epsilon) * ray_d;
		}
		else
			discard;
	}
	ivec3 grid = ivec3(ray_o * u_res);

	ray_o = ray_o * 2.0 - vec3(1.0);
	ray_o *= u_size;

	float cell_width = 2.0 * u_size / u_res;
	ivec3 gstep = ivec3(sign(ray_d));
	vec3 t_delta = cell_width * gstep / ray_d;

	// vec3 t_max = (step(vec3(0.0), gstep) - fract(ray_o)) / ray_d;
	vec3 boundary = gstep * 1.0 + gstep * 0.5 * cell_width;
	vec3 t_max = (boundary - ray_o) / ray_d;

	// out_color = abs(vec3(gstep.x * 1.0 + boundary.x - ray_o.x) / (cell_width * 0.5));
	// out_color = t_max/16;
	// out_color = vec3(min(min(t_max.x, t_max.y), t_max.z));
	while (!(any(lessThan(grid, ivec3(0)))) && !(any(greaterThan(grid, ivec3(u_res-1))))) {
		uint ptr = texelFetch(voxels, grid, 0).r;
		// if (ptr != LIST_END)
		// {
			// out_color = vec3(1.0);
			// return;
		// }

		// break;
		float t = min(min(t_max.x, t_max.y), t_max.z);
		if (trace_list(ptr, t))
			return;
		mask = ivec3(step(-t, -t_max));
		grid += mask * gstep;
		t_max += mask * t_delta;
	}

	// out_color = vec3(0.2);
#else
	trace_list(0);
#endif
}