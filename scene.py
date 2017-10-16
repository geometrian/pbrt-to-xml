import ctm


num_meshes = 0

class ObjectBase(object):
	def __init__(self, string):
		self.string = string
	def write(self, file, line_prefix):
		for line in self.string.split("\n"):
			file.write(line_prefix+line+"\n")
class Sphere(ObjectBase):
	def __init__(self, radius):
		self.radius = radius
		ObjectBase.__init__(
			self,
"""<object type=\"sphere\">
	<radius value=\"%g\"/>
	<interface name="<unknown>"/>
</object>""" % radius
		)
class PlyMesh(ObjectBase):
	def __init__(self, path):
		global num_meshes
		name = "<obj-%d>"%num_meshes; num_meshes+=1
		interface = "<unknown>"
		ObjectBase.__init__(
			self,
"""<object type="trimesh" name="%s" path="%s">
	<interface name="%s"/>
</object>""" % (name,path,interface)
		)
class Recurse(ObjectBase):
	def __init__(self, name):
		ObjectBase.__init__(
			self,
"""<recurse name=\"%s\"/>""" % name
		)

class Node(object):
	def __init__(self, parent):
		self.name = ""

		self.parent = parent

		self._children = []

		self._objects = []

		self._transform = None

	def is_empty(self):
		if len(self._children)>0: return False
		if len(self._objects )>0: return False
		return True

	def add_child(self, child, ctm):
		if self.is_empty():
			self._transform = ctm.get_copy()
			self._children.append(child)
		elif self._transform != ctm:
			tmp = Node(self)
			tmp.add_child(child,ctm)
			self._children.append(tmp)
		else:
			self._children.append(child)
	def add_object(self, object, ctm):
		if self.is_empty():
			self._transform = ctm.get_copy()
			self._objects.append(object)
		elif self._transform != ctm:
			tmp = Node(self)
			tmp.add_object(object,ctm)
			self._children.append(tmp)
		else:
			self._objects.append(object)
	def add_recurse(self, name, ctm):
		self.add_object(Recurse(name),ctm)

	def write(self, file, line_prefix):
		if not self.is_empty():
			if self.name == "":
				file.write(line_prefix+"<node>\n")
			else:
				file.write(line_prefix+"<node-defer name=\""+self.name+"\" disable=\"true\">\n")

			transform_lcl = self._transform.get_copy()
			if self.parent != None:
				transform_lcl.erase_prefix(self.parent._transform)
			transform_lcl.write(file, line_prefix+"	")

			for obj in self._objects:
				obj.write(file, line_prefix+"	")
			for child in self._children:
				child.write(file,line_prefix+"	")

			if self.name == "":
				file.write(line_prefix+"</node>\n")
			else:
				file.write(line_prefix+"</node-defer>\n")

class Scene(object):
	def __init__(self, state):
		self.sample_count = 16

		self.camera_transform = None
		self.fov_deg = None

		self.node_root = Node(None)
		self.node_current = self.node_root

		self.state = state
		self.stack = []

	def start_node(self):
		node = Node(self.node_current)
		self.node_current.add_child(node,self.state.ctm)
		self.node_current = node

		self.stack.append(self.state.get_copy())
	def set_node_name(self, name):
		assert self.node_current.name == ""
		self.node_current.name = name
	def end_node(self):
		self.state = self.stack[-1]
		self.stack = self.stack[:-1]

		self.node_current = self.node_current.parent

	def add_object_sphere(self, radius, zmin,zmax, phimax):
		self.node_current.add_object(Sphere(radius),self.state.ctm)
	def add_object_trimesh(self, verts, indices):
		pass
	def add_object_plymesh(self, path):
		self.node_current.add_object(PlyMesh(path),self.state.ctm)
	def add_recurse(self, name):
		self.node_current.add_recurse(name,self.state.ctm)

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
		self.node_root.write(file,"		")

		file.write(
"""		<node>
			<object type="point" name="pointLight">
				<interface name="mtl-point-lgt"/>
				<position x="0" y="0" z="22"/>
			</object>
		</node>
"""
		)

		#Camera
		file.write("		<node>\n")
		self.camera_transform.write(file,"			")
		file.write(
"""			<camera>
				<aperture type="point"><position value="0"/></aperture>
				<sensor>
					<position fov-degrees="%g"/>
""" % self.fov_deg
		)
		file.write(
"""					<size-y value="1"/>
					<width value="%d"/>
					<height value="%d"/>
""" % self.res
		)
		file.write( #TODO: don't ignore reconstruction type
"""					<sensitivity value="1"/>
					<reconstruction type="mitchell-netravali"/>
				</sensor>
				<frames>
					<frame name="0" t0="0.000" t1="1.000"/>
				</frames>
			</camera>
		</node>
"""
		)

		#Materials
		file.write(
"""		<interface-stack name="mtl-point-lgt">
			<edf type="lambert"><spectrum value="500.0"><cie-illuminant type="E"/></spectrum></edf>
			<bsdf type="delta"/>
		</interface-stack>
		<interface-stack name="<unknown>">
			<bsdf>
				<brdf type="lambert"><diffuse r="1" g="1" b="1"/></brdf>
				<btdf/>
			</bsdf>
		</interface-stack>
""")

		#Accel type
		file.write("		<accel type=\"LBVH-2\"/>\n")

		file.write("	</scene>\n")

		#Integrator
		file.write(
"""	<integrator type="normals" absolute="true">
		<max-depth-eye value="6"/>
		<color-miss r="1" g="0" b="1"/>
		<sample-pixels type="centered" value="64"/>
	</integrator>
"""
		)

		file.write("</xml>")
