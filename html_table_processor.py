import urllib2
import json
from bs4 import BeautifulSoup


def find_string(data):
	""" Recursively examine data structure to find a dictionary
	containing an entry 'string', returning its value.
	Idempotent for strings.
	"""
	if isinstance(data, str):
		return data
	elif isinstance(data, dict):
		if 'string' in data:
			return data['string']
		else:
			for key in data:
				val = find_string(data[key])
				if val != None:
					return val
	elif isinstance(data, list):
		for item in data:
			return find_string(item)

def jsave(data, filename, pretty=False):
	""" Converts Python data structure into JSON and writes it to a
	file, optionally pretty printed.
	"""
	if pretty:
		kwargs = {'indent': 4, 'separators': (',', ': ')}
	else:
		kwargs = {}
	with open(filename, 'w') as file:
		json.dump(data, file, sort_keys=True, **kwargs)


class HtmlProcessor():
	""" An instance of HtmlProcessor() can be used for a few very generic
	HTML tasks.
	"""
	def __init__(self, index_url=None, start_page=None):
		""" Impose manual attribute initialization for generic case, but
		allow it to occur after instantiation (ie. default to None).
		"""
		self.index_url = index_url
		self.start_page = start_page
	
	def minify(self, html):
		""" Remove whitespace from HTML to improve output data quality.
		"""
		minified = ''
		need_space = False
		for char in html:
			if char == '\t' or char == '\n' or char == ' ':
				minified += ' ' * need_space
				need_space = False
			else:
				minified += char
				need_space = char is not '>'
		return minified
	
	def get_page(self, path):
		""" This method converts a path into a URL, downloads the HTML,
		minifies it, and returns a parsed version of it.
		"""
		url = urllib2.quote(self.index_url + path, safe="%/:=&?~#+!$,;'@()*[]")
		nice_html = self.minify(urllib2.urlopen(url).read())
		return BeautifulSoup(nice_html, 'html.parser')

	def next_page(self, soup):
		""" Accepts parsed page as an argument. Returns the next page by
		looking for a list item called "next" that contains a hyperlink.
		Soup in, soup out. Idempotent for None.
		"""
		for li in soup('li'):
			if li.get('class') == [u'next']:
				return self.get_page(li.a['href'])

class HtmlTableProcessor(HtmlProcessor):
	""" Compared to its parent class, an HtmlTableProcessor() object is
	heavily oriented toward table processing. This is created as a
	subclass rather than integrating it into its parent class because
	some of what it accomplishes is best left only to table processing.
	For example, this class's process_element() function might have
	unexpected results when used with a generic HtmlProcessor() object
	which is not focused primarily on table processing.
	"""
	def find_tables(self, soup):
		""" This method accepts parsed HTML as an argument, and returns a
		list of all tables within that HTML converted into a Python data
		structure of nested lists and dictionaries.
		"""
		all_tables = []
		for unproc_table in soup("table"):
			all_tables.append({})
			for section, tag, name in (unproc_table.thead, 'th', 'head'), \
									  (unproc_table.tbody, 'td', 'body'):
				all_tables[-1][name] = self.process_table(section, tag)
		return all_tables
		#return [{name: self.process_table(section, tag)} for t in soup('table') for section, tag, name in (t.thead, 'th', 'head'), (t.tbody, 'td', 'body')]

	def process_table(self, section, t):
		""" Create a structure from a table header (t = 'th') or body (t =
		'td'). Return a list of rows called row_list[i][j]. Each row i is a
		list of cells j. Each cell is processed and structured according to
		process_element().
		"""
		if section('tr') == [] and len(section('th')) == 1:
			# For simple headers, simplify output data.
			return [{'name': section.th.name, 'string': find_string(
					self.process_element(section))}]
		# Nested list comprehensions: list of cells within list of rows.
		return [[self.process_element(cell) for cell in row(t)]
				for row in section('tr')]
	
	def process_element(self, element):
		""" For every HTML element we create a list, 'contents'. The first
		item in that list (contents[0]) is a dictionary including information
		about that element. The tag name is saved in 'name', and the string,
		if it exists, is saved under 'string'. Any attributes are saved in a
		similar manner. All non-string children are appended to 'contents' as
		lists returned via recursive interpretation by this function.
	
		Special attention is given to children with the tag name 'a'. These
		are paths leading to other pages that possibly contain tables. After
		fully interpreting the child as described above, we append to its list
		any table data we can extract from its page by recursively jumping back
		to the original get_page() method.
		"""
		contents = {}
		# Get the elements name, string, and attributes (if any).
		contents['name'] = element.name
		if element.string is not None:
			contents['string'] = element.string
		try:
			for attr in element.attrs:
				contents[attr] = element[attr]
		except AttributeError:
			pass
		try:	# Look for links
			for a_child in element.children:
				child = self.process_element(a_child)
				if child['name'] == 'a':
					# Add tables from linked page
					child['tables'] = (self.find_tables(self.get_page(
						child['href'])))
				if child['name'] not in (None, 'b', 'u', 'i'):
					contents.setdefault('children', []).append(child)
		except AttributeError as e:
			# Recursive sections like this calling other functions are 
			# extremely vulnerable to a wide variety of errors. Let's be
			# careful about which ones we are willing to catch and ignore.
			if str(e) != "'NavigableString' object has no attribute 'children'":
				raise
		return contents
	
	def find_all_tables(self, start_page=None, save=True):
		""" Go through every page and identify and process every table
		within that page. Consolidate tables from different pages if they
		share the same header. Creates a list of all tables.
		Warning: Sets tables attribute as side effect unless save param
		is set to False, in which case it returns the data instead.
		"""
		if start_page == None:
			start_page = self.start_page
		tables = []
		page = self.get_page(start_page)
		more_pages = True
		# Each page:
		while more_pages:
			# Each table in page:
			for p_table in self.find_tables(page):
				found = False
				# Each table in consolidated tables list:
				for big_table in tables:
					# If page table shares header with a consolidated table,
					if p_table['head'] == big_table['head']:
						# Append rows from page table to consolidated table.
						for row in p_table['body']:
							big_table['body'].append(row)
						found = True
						break   # Found the one, stop searching.
				if not found:   # New header, must be new table.
					tables.append(p_table)
			page = self.next_page(page)
			more_pages = page != None
		if save:
			self.tables = tables
		else:
			return tables


class HtmlFormatter(HtmlTableProcessor):
	""" An HtmlFormatter() object is a highly specialized variant of
	its parent class. It is meant to deal specifically with the tables
	found at the redacted.org web page. This class
    exists as an example to demonstrate how its parent class could be
    taken advantage of.
	"""
	def __init__(self, index_url='http://redacted.org',
				 start_page='/companies'):
		self.index_url = index_url
		self.start_page = start_page

	def format(self, raw_table=None, save=True):
		""" For our specific use, we only care about the tables found on
		the children pages. Accept the raw_table outputted from
		find_all_tables() and extract company list. Creates list of dicts
		for each company and a dict with the same data keyed by name.
		Warning: Sets dict and list attributes as side effect unless save
		param is set to False, in which case it returns the data instead.
		"""
		if raw_table == None:
			raw_table = self.tables
		t, d = [], {}
		# raw_table[first table][body]
		for company in raw_table[0]['body']:
			t.append({})
			# company[col2][cell child 1 = link)][data from page][first
			# table on that page][body of that table]
			for row in company[1]['children'][0]['tables'][0]['body']:
				# row[col2][cell info]
				t[-1][row[1]['id']] = row[1]['string']
			name = t[-1]['name']
			new_id = len(t) - 1
			d[name] = t[new_id]
			d[name]['id'] = new_id
		if save:
			self.company_list, self.company_dict = t, d
		else:
			return t, d


if __name__ == '__main__':
    """ If run as its own program rather than used as a module, demonstrate
    functionality using example subclass.
    """
	hf = HtmlFormatter()
	hf.find_all_tables()   # Sets tables attribute as side effect.
	hf.format() # Sets dict and list attributes as side effect.

	# Output list and dict for company data (single line).
	jsave(hf.company_list, 'solution-list.json')
	jsave(hf.company_dict, 'solution-dict.json')

	# Full data structure can be printed (single line).
	#jsave(hf.tables, 'tables.json')
	
	# Pretty print to visually examine output:
	jsave(hf.company_dict, 'pretty_dict.json', pretty=True)
	jsave(hf.company_list, 'pretty_list.json', pretty=True)
	jsave(hf.tables, 'pretty_tables.json', pretty=True)
