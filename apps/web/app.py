from ikcms.components.render.jinja2 import jinja2_component
from ikcms.components.db.sqla import sqla_component
import ikcms.apps.composite

class App(ikcms.apps.composite.App):

   components = [
       jinja2_component(paths=['{SITE_DIR}/templates']),
       sqla_component(),
   ]
