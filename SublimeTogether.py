import os
import sublime, sublime_plugin
import webbrowser

config_file = '.sublimetogether'
server_url = 'https://github.com/learning/SublimeTogetherServer'

class SublimetogetherGetServerCommand(sublime_plugin.WindowCommand):
	'''Get SublimeTogetherServer'''
	def run(self):
		webbrowser.open(server_url)

class SublimetogetherConvertCommand(sublime_plugin.WindowCommand):
	'''Convert A Project to SublimeTogether Project'''
	def run(self, paths = []):
		pass
	def is_enabled(self, paths = []):
		path = paths[0]
		if os.path.isdir(path):
			# get all sublime open project folders
			windows = sublime.windows()
			folders = []
			for window in windows:
				folders += window.folders()
			if path in folders:
				# It's a sublime project
				if os.path.exists(path + '/' + config_file):
					# config file already exists
					return False
				else:
					# not a SublimeTogether project
					return True
			else:
				# not a sublime project
				return False
		else:
			# not a folder
			return False

class SublimetogetherConfigCommand(sublime_plugin.WindowCommand):
	def run(self):
		pass
	def is_enabled(self, paths = []):
		path = paths[0]
		windows = sublime.windows()
		folders = []
		for window in windows:
			folders += window.folders()
		return os.path.exists(path + '/' + config_file) and path in folders