from __future__ import print_function
import os, sys
import time
import traceback

from math_helpers import rndint
from scene import *
from state import *
import parse_helpers
import tokenizer


def scalarize(params, param_name):
	param = params[param_name]

	if type(param)==type([]): param=param[0]

	if   param_name.startswith("float" ): param=float(param)
	elif param_name.startswith("int"   ): param=  int(param)
	elif param_name.startswith("string"): pass
	else: assert False

	return param

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

		elif token == "Identity":
			scene.replace_identity()
		elif token == "Translate":
			transform = list(map(float, tokenstream.pop_next(3) ))
			scene.apply_translate(transform)
		elif token == "Scale":
			transform = list(map(float, tokenstream.pop_next(3) ))
			scene.apply_scale(transform)
		elif token == "Rotate":
			transform = list(map(float, tokenstream.pop_next(4) ))
			scene.apply_rotate(transform)
		elif token == "LookAt":
			transform = list(map(float, tokenstream.pop_next(9) ))
			scene.apply_lookat(transform)
		elif token == "CoordinateSystem":
			assert False
		elif token == "CoordSysTransform":
			assert False
		elif token == "Transform":
			transform = list(map(float, parse_helpers.parse_array(tokenstream) ))
			scene.replace_transform(transform)
		elif token == "ConcatTransform":
			transform = list(map(float, parse_helpers.parse_array(tokenstream) ))
			scene.apply_transform(transform)

		elif token == "TransformBegin":
			scene.state.push_transform()
		elif token == "TransformEnd":
			scene.state.pop_transform()

		elif token == "ReverseOrientation":
			#Flips orientation of one-sided primitives.  Ignored.
			pass

		elif token == "Camera":
			_,type_cam,params = parse_helpers.parse_varfunction(tokenstream, token, scene)
			fov_deg = scalarize(params,"float fov")
			scene.fov_deg = fov_deg
			scene.camera_transform = scene.state.ctm.get_copy()
		elif token == "Film":
			_,_,params = parse_helpers.parse_varfunction(tokenstream, token, scene)
			xres = scalarize(params,"integer xresolution")
			yres = scalarize(params,"integer yresolution")
			while xres>1920 or yres>1080:
				xres *= 0.9
				yres *= 0.9
			scene.res = ( rndint(xres), rndint(yres) )
			if "float scale" in params.keys():
				sensitivity = scalarize(params,"float scale")
				scene.sensitivity = sensitivity
			if "float cropwindow" in params.keys():
				x0,x1,omy0,omy1 = [float(x) for x in params["float cropwindow"]]
				y0=1.0-omy1; y1=1.0-omy0
				dx = rndint((x1 - x0)*xres)
				dy = rndint((y1 - y0)*yres)
				x0 = rndint(x0*xres)
				y0 = rndint(y0*yres)
				scene.rect = ( x0,y0, dx,dy )
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
				if "float radius" in params: radius=scalarize(params,"float radius")
				zmin=-radius; zmax=radius
				if "float zmin"   in params: zmin  =scalarize(params,"float zmin"  )
				if "float zmax"   in params: zmax  =scalarize(params,"float zmax"  )
				phimax = 360.0
				if "float phimax" in params: phimax=scalarize(params,"float phimax")
				scene.add_object_sphere(radius, zmin,zmax, phimax)
			elif type_shape in ["trianglemesh","loopsubdiv"]:
				verts = []
				for i in range(0,len(params["point P"]),3):
					vert = params["point P"][i:i+3]
					verts.append([float(xyz) for xyz in vert])
				indices = []
				for i in range(len(params["integer indices"])):
					indices.append(int( params["integer indices"][i] ))
				#TODO: other attributes; esp. "normal N"!
				scene.add_object_trimesh(verts,indices)
			elif type_shape in ["heightfield","nurbs"]: pass
			elif type_shape == "plymesh": #TODO: alpha stuff
				scene.add_object_plymesh(scalarize(params,"string filename")[1:-1])
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
			print("")
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

def convert(path_in):
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

def main():
	for path_in in [
		"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/barcelona-pavilion/pavilion-day.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/caustic-glass/glass.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/crown/crown.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/ecosys/ecosys.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/killeroos/killeroo-simple.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-0.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-1.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-2.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-3.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/landscape/view-4.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/pbrt-book/book.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/sanmiguel/sanmiguel.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/villa/villa-daylight.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/vw-van/vw-van.pbrt",
		#"C:/dev/Prebuilt Data/objects/pbrt-v3-scenes/white-room/whiteroom-daytime.pbrt",
	]:
		convert(path_in)

if __name__ == "__main__": main()
#if __name__ == "__main__":
#	try:
#		main()
#	except:
#		traceback.print_exc()
#		input()
