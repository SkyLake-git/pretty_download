class CapacityUnit:
	name: str
	value: int

	def __init__(self, name: str, value: int):
		self.name = name
		self.value = value


class ConvertedCapacity:
	original: int
	converted: float
	unit: CapacityUnit

	def __init__(self, original: int, unit: CapacityUnit):
		self.original = original
		self.converted = original / unit.value
		self.unit = unit

	def to_str(self, ndigits: int):
		return str(round(self.converted, ndigits)) + self.unit.name


def convert(origin: int, unit: CapacityUnit) -> ConvertedCapacity:
	return ConvertedCapacity(origin, unit)
