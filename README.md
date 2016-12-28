# HTML Table Processor
Data wrangling Python module. Extract tables from HTML into Python data structures. To do: setup.py and other requirements.

## Summary
Parses with BeautifulSoup and identifies all tables. It then recursively visits any pages that are linked within those pages and identifies all tables within those pages. It fills the entire data structures into lists before writing anything to files, sacrificing memory usage for versatility. First, a large list is created containing all data. Then, relevant elements are selected out of the data and written to the output file.

## Class Structure
There are two general functions that can see a wide variety of uses not exclusive to any of the additional functionality, so they are kept as isolated functions. ```HtmlProcessor()``` objects can be used for some general HTML processing, and ```HtmlTableProcessor()``` can be used for HTML processing specific to tables. ```HtmlFormatter()``` implements ```HtmlTableProcessor()``` for this problem's specific case by siphoning only the relevant data into a new data structure.

## Internal Data Structure
The data structure follows the general pattern: a list of tables where every table is a dictionary with keys ```'head'``` and ```'body'```. The head and body values are each a list of rows, each containing a list of cells (1 row x 1 column). In our case there are two cells per row, and the cell we are most interested in is the second cell, or ```row[1]```. Each cell is a td element (or th for head), so ```cell['name'] = 'td'```. All attributes and the string are similarly saved as entries in the dictionary. Nested children are added recursively under ```cell["children"]```. Special attention is given to ```'a'``` children, which are links to other pages. For these ```'a'``` children, we recursively process each entire new page and place this entire data structure nested under ```cell['children']``` starting with a list of tables. Here is an outline of the data structure:
```
[ list of tables
    { table: dictionary with values 'head' and
        'body': [ list of rows
            [ list of 1x1 cells
                { td cell: dictionary with 'string' and attribute values, plus
                    'contents': [ list of nested elements
                        { dictionary for each element (similar to dict for cell)
                            'tables': [ key used in 'a' element dictionary, contains nested list of tables ]
                        }
                    ]
                }
            ]
        ]
    }
]
```

This data structure is created for every page. If the tables on a given page have headers that match those of previous pages' tables, the tables are merged. In our specific case, this means everything is merged into a single dictionary representing one large table.
