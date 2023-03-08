import os
import sys
import time
import urllib.error
from typing import *
from urllib import request

from .units import *


class DownloadTarget:
	urls: List[str]
	output: str

	def __init__(self, urls: List[str], output: str):
		self.urls = urls
		self.output = output


class DownloadSettings:
	stream_chunk_size: int
	intentional_sleep: float
	display_interval: float

	def __init__(self, stream_chunk_size: int, intentional_sleep: float, display_interval: float):
		self.stream_chunk_size = stream_chunk_size
		self.intentional_sleep = intentional_sleep
		self.display_interval = display_interval


class Formats:
	animation_uv: str
	total_size: str
	total_size_in_bytes: str
	speed_per_second: str
	speed_per_second_in_bytes: str

	def __init__(self, animation_uv: str, total_size: str, total_size_in_bytes: str, speed_per_second: str,
			speed_per_second_in_bytes: str) -> None:
		self.animation_uv = animation_uv
		self.total_size = total_size
		self.total_size_in_bytes = total_size_in_bytes
		self.speed_per_second = speed_per_second
		self.speed_per_second_in_bytes = speed_per_second_in_bytes

	def to_kwargs(self):
		return {
			"animation_uv": self.animation_uv,
			"total_size": self.total_size,
			"total_size_in_bytes": self.total_size_in_bytes,
			"speed_per_second": self.speed_per_second,
			"speed_per_second_in_bytes": self.speed_per_second_in_bytes
		}


OutputTunnel = NewType('OutputTunnel', Callable[[str], None])
Formatter = NewType('Formatter', Callable[[Formats], str])

min_unit = CapacityUnit("b", 1)

capacity_units = {
	min_unit,
	CapacityUnit("kb", 1024 ** 1),
	CapacityUnit("mb", 1024 ** 2),
	CapacityUnit("gb", 1024 ** 3),
	CapacityUnit("tb", 1024 ** 4)
}


def to_perfect_unit(origin_bytes: int, offset: int) -> ConvertedCapacity:
	unit = min_unit

	for check_unit in capacity_units:
		if origin_bytes + offset > check_unit.value > unit.value:
			unit = check_unit

	return ConvertedCapacity(origin_bytes, unit)


class PrefixCreator:
	prefix: str

	def __init__(self, prefix: str):
		self.prefix = prefix

	def create_tunnel(self) -> OutputTunnel:
		self.prefix.lower()  # to fix lint (static transformation suggest)
		return lambda t: default_output_tunnel(t)

	def create_formatter(self) -> Formatter:
		return lambda formats: (
				"{animation_uv} | " + f"{self.prefix}" + ": {total_size} ({speed_per_second}/s)").format(
			**formats.to_kwargs())


def default_formatter(formats: Formats) -> str:
	return ">> {animation_uv} | {total_size} ({speed_per_second}/s)".format(**formats.to_kwargs())


def default_output_tunnel(t: str) -> None:
	sys.stdout.write(f"\r{t}           ")


def download(target: DownloadTarget, settings: DownloadSettings,
		output_tunnel: OutputTunnel = default_output_tunnel,
		formatter: Formatter = default_formatter) -> bool:
	files = []
	last_display = 0
	total_bytes = 0
	current_uv = 0
	count = 0

	times = 0
	ascii_art_uv = ['\\', '/', "-"]

	if len(target.urls) == 0:
		return False

	for url in target.urls:
		count += 1
		st_url = time.time()
		seq_output = target.output + "." + str(count)
		try:
			url_data = request.urlopen(url)
		except urllib.error.HTTPError:
			continue

		end_url = time.time()

		diff = end_url - st_url
		last_display -= diff
		update_trans_time = True
		trans_base_bytes = 0
		bps = 0

		with open(seq_output, mode="wb") as f:
			while True:
				if settings.intentional_sleep > 0:
					time.sleep(settings.intentional_sleep)  # 故意的なスリープ

				if update_trans_time:
					last_trans = time.time()

				chunk_data = url_data.read(settings.stream_chunk_size)
				if not chunk_data:
					break
				trans_time = time.time() - last_trans

				update_trans_time = trans_time >= 0.3

				f.write(chunk_data)
				downloaded_bytes = len(chunk_data)

				cur_time = time.time()
				total_bytes += downloaded_bytes
				trans_base_bytes += downloaded_bytes
				times += 1

				if update_trans_time:
					bps = int(trans_base_bytes / trans_time)
					trans_base_bytes = 0

				if cur_time - last_display >= settings.display_interval:
					current_uv += 1
					if len(ascii_art_uv) <= current_uv:
						current_uv = 0
					uv = ascii_art_uv[current_uv]

					total_perfect = to_perfect_unit(total_bytes, 0)
					bps_perfect = to_perfect_unit(bps, 0)
					total_perfect_in_bytes = ConvertedCapacity(total_bytes, min_unit)
					bps_perfect_in_bytes = ConvertedCapacity(bps, min_unit)
					output_tunnel(formatter(
						Formats(uv, total_perfect.to_str(2), total_perfect_in_bytes.to_str(2), bps_perfect.to_str(2),
							bps_perfect_in_bytes.to_str(2))))

					last_display = cur_time

			files.append(seq_output)

	with open(target.output, "wb") as host_f:
		for file in files:
			with open(file, "rb") as read_f:
				host_f.write(read_f.read())
			os.unlink(file)

	return True
