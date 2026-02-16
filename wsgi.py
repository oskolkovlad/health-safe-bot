# -*- coding: utf-8 -*-
import sys
import os

# Путь к твоей папке проекта
project_home = '/home/oskolkovlad/health_safe_bot'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Активируем virtualenv, если используешь (очень важно!)
activate_this = '/home/oskolkovlad/.virtualenvs/botenv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Импортируем твой wsgi.py (или напрямую application из main.py)
from wsgi import app as application