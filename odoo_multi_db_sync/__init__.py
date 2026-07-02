# Importar paquete de modelos para que Odoo cargue los módulos bajo models/
from . import models

# Exponer post_init_hook en el namespace del paquete si existe en models.remote_connector
try:
    from .models import remote_connector as _remote_connector
    post_init_hook = getattr(_remote_connector, 'post_init_hook', None)
except Exception:
    post_init_hook = None
