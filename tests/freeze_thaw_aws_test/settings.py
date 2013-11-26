# Get all other defaults directly from freezr.settings, but override
# some custom ones.
from freezr.settings import *

# testserver runs at 9000, put broker at 9001
BROKER_URL = 'amqp://guest@localhost:9001'
