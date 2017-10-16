import ctm


class State(object):
	def __init__(self):
		#"Current transform matrix"
		self.ctm = ctm.CTM()

	def get_copy(self):
		result = State()
		result.ctm = self.ctm.get_copy()
		return result
