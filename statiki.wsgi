import os
from os.path import abspath, dirname
import sys

#active the python virtualenv for this application
HOME = os.environ['HOME']
activate_this = '%s/.virtualenvs/statiki/bin/activate_this.py' % HOME
execfile(activate_this, dict(__file__=activate_this))

# Add the source directory to the path
HERE = dirname(abspath(__file__))
sys.path.insert(0, HERE)

from statiki import db, app as application
db.create_all()
