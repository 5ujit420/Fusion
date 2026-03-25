import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Fusion.settings')
import django
try:
    django.setup()
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()

import sys
for mod_name, mod in sys.modules.items():
    if mod and hasattr(mod, '__file__') and mod.__file__ is None:
        if 'applications' in mod_name:
            print(f"NoneType __file__ found in: {mod_name}")
