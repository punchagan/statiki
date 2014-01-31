from os.path import abspath, dirname
import sys

#active the python virtualenv for this application
activate_this = '/home/punchagan/.virtualenvs/statiki/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

# Add the source directory to the path
HERE = dirname(abspath(__file__))
sys.path.insert(0, HERE)

from statiki import app as application
