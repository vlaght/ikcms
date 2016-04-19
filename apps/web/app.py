from ikcms.components.templates.jinja2 import Jinja2Component
import ikcms.apps.composite

class App(ikcms.apps.composite.App):

   components = [
       Jinja2Component(paths=['{SITE_DIR}/templates']),
   ]
