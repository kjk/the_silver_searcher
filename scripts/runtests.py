#!/usr/bin/env python

"""
Build ag and run tests.

Run as: ./scripts/runtests.py (because I'm lazy and it's easier to
hard-code such things).

It'll use a temporary directory ../ag_tests during tests.

To make it easy and compact to write additional tests:
- test descriptions are in files in tests directory
- a single file describes multiple tests
- for each test, it says:
  - what files exist and their content
  - command to run (presumably ag with apropriate flags)
  - expected result of the command
- tests stop when the output is different that the expected result. When that
  happens, ../ag_tests directory contains the data for the test so that a developer
  can investigate the problem
"""

import sys, os, shutil, codecs
import util


# set to True only when testing, speeds up test cycle by not compiling
# the executable if it already exists
NO_BUILD_IF_EXE_EXISTS = True


def fatal(msg):
	print(msg); sys.exit(1)


@util.memoize
def top_level_dir():
	# auto-detect either being in top-level or inside scripts
	if os.path.exists("runtests.py"):
		dir = ".."
	else:
		dir = "."
	path = os.path.realpath(dir)
	os.chdir(path)
	return path


@util.memoize
def ag_tests_dir():
	return os.path.realpath(os.path.join(top_level_dir(), "..", "ag_tests"))


def delete_dir(path):
	if os.path.exists(path):
		shutil.rmtree(path, True)


def delete_ag_tests_dir():
	delete_dir(ag_tests_dir())


def recreate_ag_tests_dir():
	delete_ag_tests_dir()
	path = ag_tests_dir()
	os.mkdir(path)


def is_win():
	return sys.platform.startswith("win")


def is_mac():
	return sys.platform == "darwin"


@util.memoize
def ag_exe_path_win():
	return os.path.join(top_level_dir(), "rel", "ag.exe")


@util.memoize
def ag_exe_path():
	if is_win():
		return ag_exe_path_win()
	else:
		# mac and unix
		return os.path.realpath(os.path.join(top_level_dir(), "ag"))


def verify_started_in_right_directory():
	path = os.path.join(top_level_dir(), "scripts", "runtests.py")
	if not os.path.exists(path):
		fatal("Must be in top level of source directory and run as ./scripts/runtests.py.\npath=%s" % path)


# just to be safe, if ../ag_tests directory exists we won't run tests and
# ask the user to delete it manually. This is either a conflict with a directory
# that a user created or left-over from previous failed run.
def verify_ag_tests_dir_doesnt_exist():
	if not os.path.exists(ag_tests_dir()): return
	print("ag_tests directory ('%s') directory from previous run exist" % ag_tests_dir())
	fatal("Please delete it manually.")


def print_error(out, err, errcode):
	print("Failed with error code %d" % errcode)
	if len(out) > 0: print("Stdout:\n%s" % out)
	if len(err) > 0: print("Stderr:\n%s" % err)


def build_mac():
	(out, err, errcode) = util.run_cmd("./build.sh")
	if errcode != 0:
		print_error(out, err, errcode)
		# trying to be helpful and tell user how to resolve specific problems
		# TODO: also detect lack of pcre
		if "No package 'liblzma' found" in err:
			fatal("\nIf you're using homebrew, you need to install xz package to get liblzma\nRun: brew install xz")
		sys.exit(1)


def build_win():
	util.run_cmd_throw("premake4", "vs2010")
	curr_dir = os.getcwd()
	os.chdir("vs-premake")
	util.kill_msbuild()
	util.run_cmd_throw("devenv", "ag.sln", "/Build", "Release", "/Project", "ag.vcxproj")
	assert os.path.exists(ag_exe_path_win()), "%s doesn't exist" % ag_exe_path_win()
	os.chdir(curr_dir)


# TODO: support unix?
def build():
	if NO_BUILD_IF_EXE_EXISTS and os.path.exists(ag_exe_path()):
		return
	if is_win():
		build_win()
	elif is_mac():
		build_mac()
	else:
		fatal("Don't know how to build on this platform. sys.platform=%s, os.name=%s" % (sys.platform, os.name))


def path_unix_to_native(path):
	parts = path.split("/")
	return os.path.join(*parts)


def create_dir_for_file(path):
	dir = os.path.dirname(path)
	if not os.path.exists(dir):
		os.makedirs(dir)


# here path is always in unix format
def write_to_file(path, content):
	create_dir_for_file(path)
	with codecs.open(path, "wb", "utf8") as fo:
		fo.write(content)


class FileInfo(object):
	def __init__(self, path):
		#print("Constructing FileInfo(%s)" % path)
		self.path = path
		self.data = None
	def write(self, dir):
		#print("Writing %s with data:'%s'" % (str(self.path), str(self.data)))
		p = os.path.join(dir, path_unix_to_native(self.path))
		write_to_file(p, self.data)


class CmdInfo(object):
	def __init__(self, cmd, expected):
		self.cmd = cmd
		self.expected = expected


class TestInfo(object):
	def __init__(self):
		self.files = []  # of FileInfo
		# TODO: should test_name be part of CmdInfo?
		self.test_name = "" # optional
		self.cmds = [] # of CmdInfo


# context for parsing functions
class Tests(object):
	def __init__(self, test_file):
		self.test_file = test_file # for debugging
		self.lines = []
		with codecs.open(test_file, "rb", "utf8") as fo:
			self.lines = fo.readlines()
		self.lines = [line.rstrip() for line in self.lines]
		self.curr_line = 0
		self.curr_test_info = None
		self.test_infos = []

	def start_new_test(self):
		t = TestInfo()
		self.curr_test_info = t
		self.test_infos.append(t)

	def unget_line(self):
		self.curr_line -= 1
		return self.lines[self.curr_line]

	def next_line(self):
		if self.curr_line >= len(self.lines):
			return None
		l = self.lines[self.curr_line]
		self.curr_line += 1
		#print(":%s" % l)
		return l

	def get_curr_line(self):
		return self.lines[self.curr_line]

	def raise_error(self):
		print("Invalid format of tests file '%s'" % self.test_file)
		curr_line = self.unget_line()
		print("Curr line no %d:\n'%s'" % (self.curr_line, curr_line))
		raise "Error"


TEST_START = "test:"
CMD_START = "cmd:"
FILE_START = "file:"
NEW_TEST = "--"


# helper function that chooses next parsing function based on current line
def select_parsing_function(tests, *valid):
	curr_line = tests.get_curr_line()
	if curr_line.startswith(TEST_START):
		if TEST_START in valid: return parse_test_line
	elif curr_line.startswith(CMD_START):
		if CMD_START in valid: return parse_cmd_line
	elif curr_line.startswith(FILE_START):
		if FILE_START in valid: return parse_file_line
	elif curr_line == NEW_TEST:
		if NEW_TEST in valid:
			tests.next_line()
			return parse_new_test
	# TODO: more cases?
	raise BaseException("Invalid state, curr_line=`%s`, valid=%s" % (curr_line, str(valid)))


def read_file_cmd_content(tests):
	data_lines = []
	while True:
		line = tests.next_line()
		#print(":%s" % line)
		for valid in [CMD_START, FILE_START]:
			if line.startswith(valid):
				#print("*'%s'" % valid)
				tests.unget_line()
				return "\n".join(data_lines)
		data_lines.append(line)


# file: ...
# ... # file data
def parse_file_line(tests):
	line = tests.next_line()
	parts = line.split(":", 2)
	path = parts[1].strip()
	fileInfo = FileInfo(path)
	#print("File: %s" % path)
	fileInfo.data = read_file_cmd_content(tests)
	tests.curr_test_info.files.append(fileInfo)
	#print("File data: \n'%s'\n" % fileInfo.data)
	return select_parsing_function(tests, CMD_START, FILE_START)


# cmd: ...
# ... # output of the command
def parse_cmd_line(tests):
	line = tests.next_line()
	parts = line.split(":", 2)
	cmd = parts[1].strip()
	expected_lines = []
	while True:
		line = tests.next_line()
		if line == None or line == "--" or line.startswith(CMD_START):
			break
		expected_lines.append(line)
	cmd_info = CmdInfo(cmd, "\n".join(expected_lines))
	tests.curr_test_info.cmds.append(cmd_info)
	if line == None: return None
	if line == "--": return parse_new_test
	assert line.startswith(CMD_START)
	tests.unget_line()
	return parse_cmd_line


# test: ...
def parse_test_line(tests):
	assert tests.curr_test_info.test_name == "" # shouldn't be callsed twice
	line = tests.next_line()
	parts = line.split(":", 2)
	tests.curr_test_info.test_name = parts[1].strip()
	return select_parsing_function(tests, NEW_TEST, CMD_START, FILE_START)


def parse_new_test(tests):
	tests.start_new_test()
	return select_parsing_function(tests, TEST_START, CMD_START, FILE_START)


def parse_at_file_start(tests):
	while True:
		line = tests.next_line()
		if None == line:
			return None
		# skip comments at the top of the file
		if line.startswith("#"):
			continue
		if line == NEW_TEST:
			return parse_new_test(tests)
		tests.raise_error()


# returns an array of TestInfo objects
def parse_test_file(test_file):
	tests = Tests(test_file)
	parse_func = parse_at_file_start
	while parse_func != None:
		parse_func = parse_func(tests)
	return tests


def run_ag_and_verify_results(cmd_info):
	args = [ag_exe_path()] + cmd_info.cmd.split()
	(stdout, stderr, errcmd) = util.run_cmd(*args)
	if errcmd != 0:
		fatal("Error %d. Stdout:\n'%s'\n Stderr:\n'%s'\n" % (errcmd, stdout, stderr))
	if stderr != "":
		fatal("Non-empty stderr. Stdout:\n'%s'\n Stderr:\n'%s'\n" % (stdout, stderr))
	# TODO: don't know why there's 0 at the end of stdout, so strip it
	if len(stdout) > 0 and stdout[-1] == chr(0):
		stdout = stdout[:-1]
	result = util.normalize_str(stdout)
	if len(result) > 0 and result[-1] == '\n':
		result = result[:-1]
	expected = util.normalize_str(cmd_info.expected)
	if result != expected:
		fatal("Unexpected value. Stdout:\n'%s'\nExpected:\n'%s'\n" % (result, expected))


def run_one_test(test_info, test_no):
	recreate_ag_tests_dir()
	for file_info in test_info.files:
		file_info.write(ag_tests_dir())
	subtests = len(test_info.cmds)
	name = str(test_info.test_name)
	print("Running test %d (%s), %d subtests" % (test_no, name, subtests))
	dir = os.getcwd()
	os.chdir(ag_tests_dir())
	map(run_ag_and_verify_results, test_info.cmds)
	os.chdir(dir)


def run_tests_in_file(test_file):
	print(test_file)
	tests = parse_test_file(test_file)
	print("%d tests in %s" % (len(tests.test_infos), test_file))
	test_no = 1
	for test_info in tests.test_infos:
		run_one_test(test_info, test_no)
		test_no += 1


def run_tests():
	ag_cmd = ag_exe_path()
	if not os.path.exists(ag_cmd):
		fatal("Didn't find ag executable. Expected: '%s'" % ag_cmd)
	test_files = [os.path.join("testskjk", f) for f in os.listdir("testskjk")]
	map(run_tests_in_file, test_files)
	# if everything went ok, delete the temporary tests directory
	delete_ag_tests_dir()


def verify_ag_exe_exists():
	(out, err) = util.run_cmd_throw(ag_exe_path(), "--version")
	print(out)


def clean_win():
	delete_ag_tests_dir()
	delete_dir(os.path.join(top_level_dir(), "rel"))
	delete_dir(os.path.join(top_level_dir(), "vs-premake"))


def clean_mac():
	delete_ag_tests_dir()
	assert False, "TODO: finish implementing clean_mac()"


def clean():
	print("Doing a clean rebuild")
	if is_win():
		clean_win()
	elif is_mac():
		clean_mac()
	else:
		assert False, "Unknown platform (not win or mac)"


def main():
	#print("top_level_dir = %s\nag_tests_dir =  %s\n" % (top_level_dir(), ag_tests_dir()))
 	verify_started_in_right_directory()
	if "-clean" in sys.argv:
		clean()
	verify_ag_tests_dir_doesnt_exist()
	build()
	verify_ag_exe_exists()
	run_tests()


if __name__ == "__main__":
	main()
