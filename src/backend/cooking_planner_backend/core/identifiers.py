"""ID pattern shared by recipe and ingredient validation."""

import re

ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
