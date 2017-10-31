import ctm
import state as state_module


num_meshes = 0

class ObjectBase(object):
	def __init__(self, state, string):
		self.state = state.get_copy()
		self.string = string
	def write(self, file, line_prefix):
		for line in self.string.split("\n"):
			file.write(line_prefix+line+"\n")
class Sphere(ObjectBase):
	def __init__(self, state, radius):
		global num_meshes; name="<obj-%d>"%num_meshes; num_meshes+=1
		interface = "<unknown>"
		ObjectBase.__init__(
			self, state,
"""<object type=\"sphere\" name="%s">
	<radius value=\"%g\"/>
	<interface name="%s"/>
</object>""" % (name,radius,interface)
		)
		self.radius = radius
class PlyMesh(ObjectBase):
	def __init__(self, state, path):
		global num_meshes; name="<obj-%d>"%num_meshes; num_meshes+=1
		interface = "<unknown>"
		ObjectBase.__init__(
			self, state,
"""<object type="trimesh" name="%s" path="%s">
	<interface name="%s"/>
</object>""" % (name,path,interface)
		)
class Recurse(ObjectBase):
	def __init__(self, state, name):
		ObjectBase.__init__(
			self, state,
"""<recurse name=\"%s\"/>""" % name
		)
		self.recurse_name = name

class Node(object):
	def write(self, file, line_prefix):
		if not self.is_empty():

			transform_lcl = self._transform.get_copy()
			if self.parent != None:
				transform_lcl.erase_prefix(self.parent._transform)
			transform_lcl.write(file, line_prefix+"	")

			for obj in self._objects:
				obj.write(file, line_prefix+"	")
			for child in self._children:
				child.write(file,line_prefix+"	")

class Scene(object):
	def __init__(self, state):
		self.sample_count = 1 #PBRT default `16`

		self.camera_transform = None
		self.fov_deg = None

		self.objects = []

		self.state = state

		self.sensitivity = 1

	def _add_object(self, object):
		self.objects.append(object)
	def add_object_sphere(self, radius, zmin,zmax, phimax):
		self._add_object(Sphere(self.state,radius))
	def add_object_trimesh(self, verts, indices):
		pass
	def add_object_plymesh(self, path):
		self._add_object(PlyMesh(self.state,path))
	def add_recurse(self, name):
		self._add_object(Recurse(self.state,name))

	def apply_transform(self, transform):
		self.state.ctm.apply_transform(transform)
	def apply_lookat(self, transform):
		self.state.ctm.apply_lookat(transform)
	def apply_rotate(self, transform):
		self.state.ctm.apply_rotate(transform)
	def apply_scale(self, transform):
		self.state.ctm.apply_scale(transform)
	def replace(self, transform):
		self.state.ctm.replace(transform)
	def apply_translate(self, transform):
		self.state.ctm.apply_translate(transform)

	def _write_objects(self, file, line_prefix, objects,deferred_name=None):
		if len(objects) > 0:
			if deferred_name==None: file.write(line_prefix+"<node>\n")
			else:                   file.write(line_prefix+"<node-defer name=\""+deferred_name+"\" disable=\"true\">\n")

			while True:
				#See if we have any objects with no remaining transforms on them (i.e., they're
				#	happy in the currently transformed node)

				found_empty = False
				for object in objects:
					if len(object.state.ctm._stack) == 0:
						found_empty = True
						break

				if found_empty:
					#If we do, then write them out, add the remaining objects recursively, and
					#	we're done.

					#		Need to make sure we don't recurse twice to the same object, because
					#			that'd be pointless and wasteful (some PBRT files do this,
					#			presumably erroneously).
					recursed_to = set()

					objects_remaining = []
					for object in objects:
						if len(object.state.ctm._stack) == 0:
							if (hasattr(object,"recurse_name")):
								if object.recurse_name not in recursed_to:
									object.write(file,line_prefix+"	")
									recursed_to.add(object.recurse_name)
							else:
								object.write(file,line_prefix+"	")
						else:
							objects_remaining.append(object)
					self._write_objects(file, line_prefix+"	", objects_remaining)
					break
				else:
					#If we don't, then every object has at least one more transform.  Figure out
					#	how many different initial transforms there are.

					first_transforms = {}
					for object in objects:
						key = object.state.ctm._stack[0]
						if key not in first_transforms:
							first_transforms[key] = []
						first_transforms[key].append(object)
					assert len(first_transforms) > 0

					if len(first_transforms) == 1:
						#	If there's only one unique initial transform all objects share, apply
						#		it to the node and loop back around to check all the objects again.
						objects[0].state.ctm._stack[0].write(file, line_prefix+"	");
						for object in objects:
							object.state.ctm.pop_first()
					else:
						#	Otherwise, group the objects by their initial transforms and write each
						#		group separately and recursively, and we're done.
						for obj_list in first_transforms.values():
							self._write_objects(file, line_prefix+"	", obj_list)
						break

			if deferred_name==None: file.write(line_prefix+"</node>\n")
			else:                   file.write(line_prefix+"</node-defer>\n")
	def write_xml(self, file, dir,path_in,path_out):
		#XML file beginning
		file.write(
"""<xml>
	<scene>
		<!--
			Auto-converted scenefile:
				PBRT in:     "%s"
				libmcrt out: "%s"
		-->
""" % (path_in,path_out)
		)

		#Nodes
		#	Separate the normal and the deferred objects
		normal_objects = []
		deferred_objects = {}
		for object in self.objects:
			if object.state.deferred_name != None:
				if object.state.deferred_name not in deferred_objects:
					deferred_objects[object.state.deferred_name] = []
				deferred_objects[object.state.deferred_name].append(object)
			else:
				normal_objects.append(object)
		#	Write the deferred objects
		if len(deferred_objects) > 0:
			file.write("\n		<!-- Deferred Objects -->\n")
			for name in deferred_objects:
				self._write_objects(file,"		",deferred_objects[name],name)
			#		Yes; the empty recursion points too, as they may be referenced.
			for name in state_module.deferred_names:
				if name not in deferred_objects:
					file.write("\n		<node-defer name=\""+name+"\" disable=\"true\"/>")
		#	Write the normal objects
		file.write("\n		<!-- Main Scene -->\n")
		self._write_objects(file,"		",normal_objects)

		file.write(
"""
		<!-- Lights -->
		<node>
			<object type="point" name="pointLight">
				<interface name="mtl-point-lgt"/>
				<position x="0" y="0" z="22"/>
			</object>
		</node>
"""
		)

		#Camera
		file.write(
"""
		<!-- Camera -->
		<node>
"""
		)
		self.camera_transform.write(file,"			")
		file.write(
"""			<camera>
				<aperture type="point"><position value="0"/></aperture>
				<sensor>
					<position fov-degrees-"""
		)
		if self.res[0] < self.res[1]: file.write("x")
		else:                         file.write("y")
		file.write("""="%g"/>
""" % self.fov_deg
		)
		file.write(
"""					<size-y value="1"/>
					<width value="%d"/>
					<height value="%d"/>
""" % self.res
		)
		file.write( #TODO: don't ignore reconstruction type
"""					<sensitivity value="%g"/>
					<reconstruction type="mitchell-netravali"/>
				</sensor>
				<frames>
					<frame name="0" t0="0.000" t1="1.000"/>
				</frames>
			</camera>
		</node>
""" % self.sensitivity
		)

		#Materials
		file.write(
"""
		<!-- Materials -->
		<interface-stack name="mtl-point-lgt">
			<edf type="lambert"><spectrum value="500.0"><cie-illuminant type="E"/></spectrum></edf>
			<bsdf type="delta"/>
		</interface-stack>
		<interface-stack name="<unknown>">
			<bsdf>
				<brdf type="lambert"><diffuse r="1" g="1" b="1"/></brdf>
				<btdf/>
			</bsdf>
		</interface-stack>
"""
		)

		#Accel type
		file.write(
"""
		<!-- Acceleration Structure -->
		<accel type=\"LBVH-2\"/>
"""
		)

		file.write("	</scene>\n")

		#Integrator
		file.write(
"""
	<!-- Integrator -->
	<integrator type="normals" absolute="true">
		<max-depth-eye value="6"/>
		<color-miss r="1" g="0" b="1"/>
		<sample-pixels type="centered" value="%d"/>
	</integrator>
""" % self.sample_count
		)

		file.write("</xml>")
