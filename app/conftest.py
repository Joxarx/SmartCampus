# conftest.py - Configuración global de pytest
# Asegura que `from main import app` funcione independientemente del CWD
# desde donde se invoque pytest (raíz del proyecto, app/, tests/, etc.).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
