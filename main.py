from __future__ import print_function
import os, sys
import time
import traceback

from scene import *
from state import *
import parse_helpers
import tokenizer


def parse_tokens(dir, tokenstream, scene):
	num_tokens = len(tokenstream)
	print("  Parsing %d tokens . . ."%num_tokens)

	t0 = time.time()
	tlast = t0
	while True:
		token = tokenstream.pop_next()

		if   token == "WorldBegin":
			scene.state.ctm.clear()
		elif token == "WorldEnd":
			break
		elif token == "AttributeBegin":
			scene.state.push()
		elif token == "AttributeEnd":
			scene.state.pop()
		elif token == "ObjectBegin":
			name = tokenstream.pop_next()[1:-1]
			scene.state.begin_defer(name)
		elif token == "ObjectInstance":
			name = tokenstream.pop_next()[1:-1]
			scene.add_recurse(name)
		elif token == "ObjectEnd":
			scene.state.end_defer()

		elif token == "ConcatTransform":
			transform = list(map(float, parse_helpers.parse_array(tokenstream) ))
			scene.apply_transform(transform)
		elif token == "LookAt":
			transform = list(map(float, tokenstream.pop_next(9) ))
			scene.apply_lookat(transform)
		elif token == "ReverseOrientation":
			#Flips orientation of one-sided primitives.  Ignored.
			pass
		elif token == "Rotate":
			transform = list(map(float, tokenstream.pop_next(4) ))
			scene.apply_rotate(transform)
		elif token == "Scale":
			transform = list(map(float, tokenstream.pop_next(3) ))
			scene.apply_scale(transform)
		elif token == "Transform":
			transform = list(map(float, parse_helpers.parse_array(tokenstream) ))
			scene.replace(transform)
		elif token == "Translate":
			transform = list(map(float, tokenstream.pop_next(3) ))
			scene.apply_translate(transform)

		elif token == "Camera":
			_,type_cam,params = parse_helpers.parse_varfunction(tokenstream, token, scene)
			scene.fov_deg = float(params["float fov"][0])
			scene.camera_transform = scene.state.ctm.get_copy()
		elif token == "Film":
			_,_,params = parse_helpers.parse_varfunction(tokenstream, token, scene)
			scene.res = (
				int(params["integer xresolution"][0]),
				int(params["integer yresolution"][0])
			)

		elif token == "Shape":
			_,type_shape,params =  parse_helpers.parse_varfunction(tokenstream, token, scene)
			if   type_shape == "cone":        assert False
			elif type_shape == "curve":       assert False
			elif type_shape == "cylinder":    assert False
			elif type_shape == "disk":        assert False
			elif type_shape == "hyperboloid": assert False
			elif type_shape == "paraboloid":  assert False
			elif type_shape == "sphere":
				radius = 1
				if "float radius" in params: radius=float(params["float radius"][0])
				zmin=-radius; zmax=radius
				if "float zmin"   in params: zmin  =float(params["float zmin"  ][0])
				if "float zmax"   in params: zmax  =float(params["float zmax"  ][0])
				phimax = 360.0
				if "float phimax" in params: phimax=float(params["float phimax"][0])
				scene.add_object_sphere(radius, zmin,zmax, phimax)
			elif type_shape == "trianglemesh":
				verts = []
				for i in range(0,len(params["P"]),3):
					verts.append( params["P"][i:i+3] )
				indices = params["integer indices"]
				#TODO: other attributes; esp. "normal N"!
				scene.add_object_trimesh(verts,indices)
			elif type_shape in ["heightfield","loopsubdiv","nurbs"]: pass
			elif type_shape == "plymesh": #TODO: alpha stuff
				scene.add_object_plymesh(params["string filename"][1:-1])
			else: assert False
		elif token in [
			"Sampler", "PixelFilter",
			"Integrator",
			"AreaLightSource",
			"Material", "MakeNamedMaterial", "Texture"
		]:
			parse_helpers.parse_varfunction(tokenstream, token, scene)

		elif token == "Include":
			filename = tokenstream.pop_next()[1:-1]
			file = open(os.path.join(dir,filename),"r")
			lines = file.readlines()
			file.close()
			moretokens = tokenizer.tokenize(lines)
			tokenstream.add_tokenstream_at_current(moretokens)
			num_tokens += len(moretokens)

		tnow = time.time()
		if tnow-tlast > 0.1:
			print("\r  Parsed token %d / %d . . ."%(num_tokens-len(tokenstream),num_tokens),end="")
			tlast = tnow

	t1 = time.time()
	print("\r  Parsed %d tokens in %f seconds."%(num_tokens,t1-t0))

def parse(dir, lines):
	tokenstream = tokenizer.tokenize(lines)

	state = State()
	scene = Scene(state)
	parse_tokens(dir, tokenstream, scene)

	return scene

def main():
	#path_in = "C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/pbrt-book/book.pbrt"
	path_in = "C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/vw-van/vw-van.pbrt"
	#path_in = "C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-0.pbrt"

	#path_out = "scene.xml"#"C:/Users/Ian Mallett/Desktop/scene.xml"
	path_out = os.path.splitext(path_in)[0] + ".xml"

	path_in  = os.path.abspath(path_in ).replace("\\","/")
	path_out = os.path.abspath(path_out).replace("\\","/")

	print("Reading input file . . .")
	t0 = time.time()
	file = open(path_in,"r")
	lines = file.readlines()
	file.close()
	t1 = time.time()
	print("Read input file in %f seconds."%(t1-t0))

	print("Parsing input . . .")
	t0 = time.time()
	dir = os.path.dirname(path_in)
	scene = parse(dir, lines)
	t1 = time.time()
	print("Input parsed in %f seconds."%(t1-t0))

	print("Writing output file . . .")
	t0 = time.time()
	file = open(path_out,"w")
	scene.write_xml(file, dir,path_in,path_out)
	file.close()
	t1 = time.time()
	print("Wrote output file in %f seconds."%(t1-t0))

if __name__ == "__main__": main()
#if __name__ == "__main__":
#	try:
#		main()
#	except:
#		traceback.print_exc()
#		input()
