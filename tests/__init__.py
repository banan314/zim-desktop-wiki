# -*- coding: utf-8 -*-

# Copyright 2008-2015 Jaap Karssenberg <jaap.karssenberg@gmail.com>

'''Zim test suite'''

from __future__ import with_statement


import os
import sys
import tempfile
import shutil
import logging
import gettext
import xml.etree.cElementTree as etree
import types
import glob

try:
	import gtk
except ImportError:
	gtk = None


if sys.version_info < (2, 7, 0):
	try:
		import unittest2 as unittest
		from unittest2 import skip, skipIf, skipUnless, expectedFailure
	except ImportError:
		print >>sys.stderr, '''\
For python versions < 2.7 the 'unittest2' module is needed to run
the test suite. On Ubuntu or Debian install package 'python-unittest2'.
'''
		sys.exit(1)
else:
	import unittest
	from unittest import skip, skipIf, skipUnless, expectedFailure

__unittest = 1 # needed to get stack trace OK for class TestCase

gettext.install('zim', unicode=True, names=('_', 'gettext', 'ngettext'))

FAST_TEST = False #: determines whether we skip slow tests or not


# This list also determines the order in which tests will executed
__all__ = [
	'package', 'translations',
	'datetimetz', 'utils', 'errors', 'signals', 'actions',
	'environ', 'fs', 'newfs',
	'config', 'applications',
	'parsing', 'formats', 'templates', 'objectmanager',
	'index', 'notebook', 'history',
	'export', 'www', 'search',
	'widgets', 'pageindex', 'pageview', 'clipboard', 'gui',
	'main', 'plugins',
	'calendar', 'printtobrowser', 'versioncontrol', 'inlinecalculator',
	'tasklist', 'tags', 'imagegenerators', 'tableofcontents',
	'quicknote', 'attachmentbrowser', 'insertsymbol',
	'sourceview', 'tableeditor', 'bookmarksbar', 'spell',
]


mydir = os.path.dirname(__file__)


# when a test is missing from the list that should be detected
for file in glob.glob(mydir + '/*.py'):
	name = os.path.basename(file)[:-3]
	if name != '__init__' and not name in __all__:
		raise AssertionError, 'Test missing in __all__: %s' % name

# get our own data dir
DATADIR = os.path.abspath(os.path.join(mydir, 'data'))

# get our own tmpdir
TMPDIR = os.path.abspath(os.path.join(mydir, 'tmp'))
	# Wanted to use tempfile.get_tempdir here to put everything in
	# e.g. /tmp/zim but since /tmp is often mounted as special file
	# system this conflicts with thrash support. For writing in source
	# dir we have conflict with bazaar controls, this is worked around
	# by a config mode switch in the bazaar backend of the version
	# control plugin
if os.name == 'nt':
	TMPDIR = unicode(TMPDIR)
else:
	TMPDIR = TMPDIR.encode(sys.getfilesystemencoding())

# also get the default tmpdir and put a copy in the env
REAL_TMPDIR = tempfile.gettempdir()


from zim.newfs import LocalFolder


def load_tests(loader, tests, pattern):
	'''Load all test cases and return a unittest.TestSuite object.
	The parameters 'tests' and 'pattern' are ignored.
	'''
	suite = unittest.TestSuite()
	for name in ['tests.'+name for name in __all__ ]:
		test = loader.loadTestsFromName(name)
		suite.addTest(test)
	return suite


def _setUpEnvironment():
	'''Method to be run once before test suite starts'''
	# In fact to be loaded before loading some of the zim modules
	# like zim.config and any that export constants from it
	system_data_dirs = os.environ.get('XDG_DATA_DIRS')
	os.environ.update({
		'ZIM_TEST_RUNNING': 'True',
		'ZIM_TEST_ROOT': os.getcwd(),
		'TMP': TMPDIR,
		'REAL_TMP': REAL_TMPDIR,
		'XDG_DATA_HOME': os.path.join(TMPDIR, 'data_home'),
		'XDG_DATA_DIRS': os.path.join(TMPDIR, 'data_dir'),
		'XDG_CONFIG_HOME': os.path.join(TMPDIR, 'config_home'),
		'XDG_CONFIG_DIRS': os.path.join(TMPDIR, 'config_dir'),
		'XDG_CACHE_HOME': os.path.join(TMPDIR, 'cache_home')
	})

	if os.path.isdir(TMPDIR):
		shutil.rmtree(TMPDIR)
	os.makedirs(TMPDIR)

	hicolor = os.environ['XDG_DATA_DIRS'] + '/icons/hicolor'
	os.makedirs(hicolor)

	if system_data_dirs:
		# Need these since gtk pixbuf loaders are in /usr/share in
		# some setups, and this parameter is used to find them
		os.environ['XDG_DATA_DIRS'] = os.pathsep.join(
			(os.environ['XDG_DATA_DIRS'], system_data_dirs) )

if os.environ.get('ZIM_TEST_RUNNING') != 'True':
	# Do this when loaded, but not re-do in sub processes
	# (doing so will kill e.g. the ipc test...)
	_setUpEnvironment()


## Setup special logging for tests

class UncaughtWarningError(AssertionError):
	pass


class TestLoggingHandler(logging.Handler):
	'''Handler class that raises uncaught errors to ensure test don't fail silently'''

	def __init__(self, level=logging.WARNING):
		logging.Handler.__init__(self, level)
		fmt = logging.Formatter('%(levelname)s %(filename)s %(lineno)s: %(message)s')
		self.setFormatter(fmt)

	def emit(self, record):
		if record.levelno >= logging.WARNING:
			raise UncaughtWarningError, self.format(record)
		else:
			pass

logging.getLogger().addHandler(TestLoggingHandler())
	# Handle all errors that make it up to the root level

try:
	logging.getLogger('zim.test').warning('foo')
except UncaughtWarningError:
	pass
else:
	raise AssertionError, 'Raising errors on warning fails'

###


_zim_pyfiles = []

def zim_pyfiles():
	'''Returns a list with file paths for all the zim python files'''
	if not _zim_pyfiles:
		for d, dirs, files in os.walk('zim'):
			_zim_pyfiles.extend([d+'/'+f for f in files if f.endswith('.py')])
		_zim_pyfiles.sort()
	for file in _zim_pyfiles:
		yield file # shallow copy


def slowTest(obj):
	'''Decorator for slow tests

	Tests wrapped with this decorator are ignored when you run
	C{test.py --fast}. You can either wrap whole test classes::

		@tests.slowTest
		class MyTest(tests.TestCase):
			...

	or individual test functions::

		class MyTest(tests.TestCase):

			@tests.slowTest
			def testFoo(self):
				...

			def testBar(self):
				...
	'''
	if FAST_TEST:
		wrapper = skip('Slow test')
		return wrapper(obj)
	else:
		return obj


class TestCase(unittest.TestCase):
	'''Base class for test cases'''

	maxDiff = None

	SRC_DIR = LocalFolder(mydir + '/../')
	assert SRC_DIR.file('zim.py').exists(), 'Wrong working dir'

	@classmethod
	def tearDownClass(cls):
		if gtk is not None:
			gtk_process_events() # flush any pending events / warnings

	def assertEqual(self, first, second, msg=None):
		## HACK to work around "feature" in unittest - it does not consider
		## string and unicode to be of the same type and thus does not
		## show diffs if the textual content differs
		if type(first) in (str, unicode) \
		and type(second) in (str, unicode):
			self.assertMultiLineEqual(first, second, msg)
		else:
			unittest.TestCase.assertEqual(self, first, second, msg)

	@classmethod
	def create_tmp_dir(cls, name=None):
		'''Returns a path to a tmp dir where tests can write data.
		The dir is removed and recreated empty every time this function
		is called with the same name from the same class.
		'''
		cls.clear_tmp_dir(name)
		path = cls._get_tmp_name(name)
		os.makedirs(path)
		assert os.path.exists(path) # make real sure
		return path

	@classmethod
	def get_tmp_name(cls, name=None):
		'''Returns the same path as L{create_tmp_dir()} but without
		touching it. This method will raise an exception when a file
		or dir exists of the same name.
		'''
		path = cls._get_tmp_name(name)
		assert not os.path.exists(path), 'This path should not exist: %s' % path
		return path

	@classmethod
	def clear_tmp_dir(cls, name=None):
		'''Clears the tmp dir for this test'''
		path = cls._get_tmp_name(name)
		if os.path.exists(path):
			shutil.rmtree(path)
		assert not os.path.exists(path) # make real sure

	@classmethod
	def _get_tmp_name(cls, name):
		if name:
			assert not os.path.sep in name, 'Don\'t use this method to get sub folders or files'
			name = cls.__name__ + '_' + name
		else:
			name = cls.__name__

		if os.name == 'nt':
			name = unicode(name)
		else:
			name = name.encode(sys.getfilesystemencoding())

		return os.path.join(TMPDIR, name)


class LoggingFilter(logging.Filter):
	'''Convenience class to surpress zim errors and warnings in the
	test suite. Acts as a context manager and can be used with the
	'with' keyword.

	Alternatively you can call L{wrap_test()} from test C{setUp}.
	This will start the filter and make sure it is cleaned up again.
	'''

	# Due to how the "logging" module works, logging channels do inherit
	# handlers of parents but not filters. Therefore setting a filter
	# on the "zim" channel will not surpress messages from sub-channels.
	# Instead we need to set the filter both on the channel and on
	# top level handlers to get the desired effect.

	def __init__(self, logger, message=None):
		'''Constructor
		@param logger: the logging channel name
		@param message: can be a string, or a sequence of strings.
		Any messages that start with this string or any of these
		strings are surpressed.
		'''
		self.logger = logger
		self.message = message

	def __enter__(self):
		logging.getLogger(self.logger).addFilter(self)
		for handler in logging.getLogger().handlers:
			handler.addFilter(self)

	def __exit__(self, *a):
		logging.getLogger(self.logger).removeFilter(self)
		for handler in logging.getLogger().handlers:
			handler.removeFilter(self)

	def filter(self, record):
		if record.name.startswith(self.logger):
			msg = record.getMessage()
			if self.message is None:
				return False
			elif isinstance(self.message, tuple):
				return not any(msg.startswith(m) for m in self.message)
			else:
				return not msg.startswith(self.message)
		else:
			return True


	def wrap_test(self, test):
		self.__enter__()
		test.addCleanup(self.__exit__)


class DialogContext(object):
	'''Context manager to catch dialogs being opened

	Inteded to be used like this::

		def myCustomTest(dialog):
			self.assertTrue(isinstance(dialog, CustomDialogClass))
			# ...
			dialog.assert_response_ok()

		with DialogContext(
			myCustomTest,
			SomeOtherDialogClass
		):
			gui.show_dialogs()

	In this example the first dialog that is run by C{gui.show_dialogs()}
	is checked by the function C{myCustomTest()} while the second dialog
	just needs to be of class C{SomeOtherDialogClass} and will then
	be closed with C{assert_response_ok()} by the context manager.

	This context only works for dialogs derived from zim's Dialog class
	as it uses a special hook in L{zim.gui.widgets}.
	'''

	def __init__(self, *definitions):
		'''Constructor
		@param definitions: list of either classes or methods
		'''
		self.stack = list(definitions)
		self.old_test_mode = None

	def __enter__(self):
		import zim.gui.widgets
		self.old_test_mode = zim.gui.widgets.TEST_MODE
		self.old_callback = zim.gui.widgets.TEST_MODE_RUN_CB
		zim.gui.widgets.TEST_MODE = True
		zim.gui.widgets.TEST_MODE_RUN_CB = self._callback

	def _callback(self, dialog):
		#~ print '>>>', dialog
		if not self.stack:
			raise AssertionError, 'Unexpected dialog run: %s' % dialog

		handler = self.stack.pop(0)

		if isinstance(handler, (type, types.ClassType)): # is a class
			if not isinstance(dialog, handler):
				raise AssertionError, 'Expected dialog of class %s, but got %s instead' % (handler, dialog.__class__)
			dialog.assert_response_ok()
		else: # assume a function
			handler(dialog)

	def __exit__(self, *error):
		#~ print 'ERROR', error
		import zim.gui.widgets
		zim.gui.widgets.TEST_MODE = self.old_test_mode
		zim.gui.widgets.TEST_MODE_RUN_CB = self.old_callback

		has_error = bool([e for e in error if e is not None])
		if self.stack and not has_error:
			raise AssertionError, '%i expected dialog(s) not run' % len(self.stack)

		return False # Raise any errors again outside context


class TestData(object):
	'''Wrapper for a set of test data in tests/data'''

	def __init__(self, format):
		assert format == 'wiki', 'TODO: add other formats'
		root = os.environ['ZIM_TEST_ROOT']
		tree = etree.ElementTree(file=root+'/tests/data/notebook-wiki.xml')

		test_data = []
		for node in tree.getiterator(tag='page'):
			name = node.attrib['name']
			text = unicode(node.text.lstrip('\n'))
			test_data.append((name, text))

		self._test_data = tuple(test_data)

	def __iter__(self):
		'''Yield the test data as 2 tuple (pagename, text)'''
		for name, text in self._test_data:
			yield name, text # shallow copy

	def get(self, pagename):
		'''Return text for a specific pagename'''
		for n, text in self._test_data:
			if n == pagename:
				return text
		assert False, 'Could not find data for page: %s' % pagename


WikiTestData = TestData('wiki') #: singleton to be used by various tests


def _expand_manifest(names):
	'''Build a set of all pages names and all namespaces that need to
	exist to host those page names.
	'''
	manifest = set()
	for name in names:
		manifest.add(name)
		while name.rfind(':') > 0:
			i = name.rfind(':')
			name = name[:i]
			manifest.add(name)
	return manifest

def new_parsetree():
	'''Returns a new ParseTree object for testing

	Uses data from L{WikiTestData}, page C{roundtrip}
	'''
	import zim.formats.wiki
	parser = zim.formats.wiki.Parser()
	text = WikiTestData.get('roundtrip')
	tree = parser.parse(text)
	return tree

def new_parsetree_from_text(text, format='wiki'):
	import zim.formats
	parser = zim.formats.get_format(format).Parser()
	return parser.parse(text)


def new_parsetree_from_xml(xml):
	# For some reason this does not work with cElementTree.XMLBuilder ...
	from xml.etree.ElementTree import XMLTreeBuilder
	from zim.formats import ParseTree
	builder = XMLTreeBuilder()
	builder.feed(xml)
	root = builder.close()
	return ParseTree(root)


def new_page():
	from zim.notebook import Path, Page
	page = Page(Path('roundtrip'))
	page.set_parsetree(new_parsetree())
	return page


def new_page_from_text(text, format='wiki'):
	from zim.notebook import Path, Page
	page = Page(Path('Test'))
	page.set_parsetree(new_parsetree_from_text(text, format))
	return page



_notebook_data = None

def new_notebook(fakedir=None):
	'''Returns a new Notebook object with all data in memory

	Uses data from L{WikiTestData}

	@param fakedir: optional parameter to set the 'dir' attribute for
	the notebook which allows you to resolve file
	paths etc. It will not automatically touch the dir
	(hence it being 'fake').
	'''
	from zim.fs import Dir
	from zim.config import VirtualConfigBackend
	from zim.notebook import Notebook, Path
	from zim.notebook.notebook import NotebookConfig
	from zim.notebook.index import Index, MemoryDBConnection

	from zim.notebook.layout import FilesLayout
	from zim.newfs.mock import MockFolder, clone_mock_object

	global _notebook_data
	if not _notebook_data: # run this one time only
		templfolder = MockFolder('/mock/notebook')
		layout = FilesLayout(templfolder, endofline='unix')

		manifest = []
		for name, text in WikiTestData:
			manifest.append(name)
			file, x = layout.map_page(Path(name))
			file.write(text)

		manifest = frozenset(_expand_manifest(manifest))

		index = Index.new_from_memory(layout)
		index.update()
		with index.db_conn.db_context() as db:
			lines = list(db.iterdump())
		sql = '\n'.join(lines)

		_notebook_data = (templfolder, sql, manifest)

	if fakedir:
		fakedir = fakedir if isinstance(fakedir, basestring) else fakedir.path
	templfolder, sql, manifest = _notebook_data
	folder = MockFolder(fakedir or templfolder.path)
	clone_mock_object(templfolder, folder)

	#~ print ">>>>>>>>>>>>>"
	#~ for path in folder._fs.tree():
		#~ print path

	layout = FilesLayout(folder, endofline='unix')

	db_conn = MemoryDBConnection()
	with db_conn.db_change_context() as db:
		db.executescript(sql)
	index = Index(db_conn, layout)

	### XXX - Big HACK here - Get better classes for this - XXX ###
	dir = VirtualConfigBackend()
	file = dir.file('notebook.zim')
	file.dir = dir
	file.dir.basename = 'Unnamed Notebook'
	###
	config = NotebookConfig(file)

	if fakedir:
		dir = Dir(fakedir)
		cache_dir = dir.subdir('.zim')
	else:
		dir = None
		cache_dir = None

	notebook = Notebook(dir, cache_dir, config, folder, layout, index)
	notebook.testdata_manifest = manifest
	return notebook


def new_files_notebook(dir):
	'''Returns a new Notebook object

	Uses data from L{WikiTestData}

	@param path: a folder path, e.g. created by L{TestCase.create_tmp_dir()}
	'''
	from zim.fs import Dir
	from zim.notebook import init_notebook, Notebook, Path

	dir = Dir(dir)
	init_notebook(dir)
	notebook = Notebook.new_from_dir(dir)

	manifest = []
	for name, text in WikiTestData:
		manifest.append(name)
		page = notebook.get_page(Path(name))
		page.parse('wiki', text)
		notebook.store_page(page)

	notebook.testdata_manifest = _expand_manifest(manifest)
	notebook.index.update()

	return notebook


class Counter(object):
	'''Object that is callable as a function and keeps count how often
	it was called.
	'''

	def __init__(self, value=None):
		'''Constructor
		@param value: the value to return when called as a function
		'''
		self.value = value
		self.count = 0

	def __call__(self, *arg, **kwarg):
		self.count += 1
		return self.value


class MockObjectBase(object):
	'''Base class for mock objects.

	Mock methods can be installed with L{mock_method()}. All method
	calls to mock methods are logged, so they can be inspected.
	The attribute C{mock_calls} has a list of tuples with mock methods
	and arguments in order they have been called.
	'''

	def __init__(self):
		self.mock_calls = []

	def mock_method(self, name, return_value):
		'''Installs a mock method with a given name that returns
		a given value.
		'''
		def my_mock_method(*arg, **kwarg):
			call = [name] + list(arg)
			if kwarg:
				call.append(kwarg)
			self.mock_calls.append(tuple(call))
			return return_value

		setattr(self, name, my_mock_method)
		return my_mock_method


class MockObject(MockObjectBase):
	'''Simple subclass of L{MockObjectBase} that automatically mocks a
	method which returns C{None} for any non-existing attribute.
	Attributes that are not methods need to be initialized explicitly.
	'''

	def __getattr__(self, name):
		'''Automatically mock methods'''
		if name == '__zim_extension_objects__':
			raise AttributeError
		else:
			return self.mock_method(name, None)


def gtk_process_events(*a):
	'''Method to simulate a few iterations of the gtk main loop'''
	assert gtk is not None
	while gtk.events_pending():
		gtk.main_iteration(block=False)
	return True # continue


def gtk_get_menu_item(menu, id):
	'''Get a menu item from a C{gtk.Menu}
	@param menu: a C{gtk.Menu}
	@param id: either the menu item label or the stock id
	@returns: a C{gtk.MenuItem} or C{None}
	'''
	items = menu.get_children()
	ids = [i.get_property('label') for i in items]
		# gtk.ImageMenuItems that have a stock id happen to use the
		# 'label' property to store it...

	assert id in ids, \
		'Menu item "%s" not found, we got:\n' % id \
		+ ''.join('- %s \n' % i for i in ids)

	i = ids.index(id)
	return items[i]


def gtk_activate_menu_item(menu, id):
	'''Trigger the 'click' action an a menu item
	@param menu: a C{gtk.Menu}
	@param id: either the menu item label or the stock id
	'''
	item = gtk_get_menu_item(menu, id)
	item.activate()
