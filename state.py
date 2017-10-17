import ctm


class State(object):
	def __init__(self):
		#"Current transform matrix"
		self.ctm = ctm.CTM()
		self.deferred_name = None

		self._stack = []

	def push(self):
		self._stack.append(self.ctm.get_copy())
	def pop(self):
		self.ctm = self._stack.pop()

	def get_copy(self):
		result = State()
		result.ctm = self.ctm.get_copy()
		result.deferred_name = self.deferred_name
		return result

	def begin_defer(self, name):
		assert self.deferred_name == None
		self.deferred_name = name
	def end_defer(self):
		assert self.deferred_name != None
		self.deferred_name = None
