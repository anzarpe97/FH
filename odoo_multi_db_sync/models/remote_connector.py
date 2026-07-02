from odoo import models, fields, api, SUPERUSER_ID
import logging
import xmlrpc.client
import datetime
from odoo.exceptions import UserError
from urllib.parse import urlsplit, urlunsplit, parse_qs

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remote_url = fields.Char(string="Remote Odoo URL", config_parameter='odoo_multi_db_sync.remote_url')
    remote_db = fields.Char(string="Remote DB name", config_parameter='odoo_multi_db_sync.remote_db')
    remote_user = fields.Char(string="Remote user", config_parameter='odoo_multi_db_sync.remote_user')
    remote_password = fields.Char(string="Remote password", config_parameter='odoo_multi_db_sync.remote_password')
    enable_auto_sync = fields.Boolean(string="Enable automatic sync", config_parameter='odoo_multi_db_sync.enable_auto_sync')

    # Se usan ir.config_parameter automáticamente por config_parameter en los fields

    @api.model
    def get_values(self):
        """Cargar valores desde ir.config_parameter (y crear defaults si faltan)."""
        res = super().get_values()
        # Asegurar que existan los parámetros por defecto
        try:
            self.env['multi.db.sync']._ensure_default_remote_params()
        except Exception:
            # no bloquear la vista si falla la creación de defaults
            _logger.exception("odoo_multi_db_sync: fallo al asegurar parámetros por defecto")
        param = self.env['ir.config_parameter'].sudo()
        res.update({
            'remote_url': param.get_param('odoo_multi_db_sync.remote_url', default=''),
            'remote_db': param.get_param('odoo_multi_db_sync.remote_db', default=''),
            'remote_user': param.get_param('odoo_multi_db_sync.remote_user', default=''),
            'remote_password': param.get_param('odoo_multi_db_sync.remote_password', default=''),
            'enable_auto_sync': param.get_param('odoo_multi_db_sync.enable_auto_sync', default='False') in ('1','True','true','yes','Yes'),
        })
        return res

    def set_values(self):
        """Guardar los valores en ir.config_parameter cuando el usuario guarda el formulario."""
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('odoo_multi_db_sync.remote_url', self.remote_url or '')
        param.set_param('odoo_multi_db_sync.remote_db', self.remote_db or '')
        param.set_param('odoo_multi_db_sync.remote_user', self.remote_user or '')
        param.set_param('odoo_multi_db_sync.remote_password', self.remote_password or '')
        param.set_param('odoo_multi_db_sync.enable_auto_sync', 'True' if self.enable_auto_sync else 'False')

class MultiDbSync(models.Model):
    _name = 'multi.db.sync'
    _description = 'Sync partners desde DB remota'

    _DEFAULT_PARAMS = {
        'odoo_multi_db_sync.remote_url': 'https://farruggio-prueba18-24780452.dev.odoo.com',
        'odoo_multi_db_sync.remote_db': 'farruggio-prueba18-24780452',  # base B (remota)
        'odoo_multi_db_sync.remote_user': 'soporteodoo@contablesag.com',
        'odoo_multi_db_sync.remote_password': '123',
        'odoo_multi_db_sync.enable_auto_sync': 'False',  # desactivar sync automático por defecto
    }

    @api.model
    def _ensure_default_remote_params(self):
        """Crear parámetros del sistema con los valores por defecto si no existen o están vacíos."""
        param_obj = self.env['ir.config_parameter'].sudo()
        for key, val in self._DEFAULT_PARAMS.items():
            existing = param_obj.get_param(key)
            # si no existe o es vacío, crear/actualizar
            if not existing:
                try:
                    param_obj.set_param(key, val)
                    _logger.info("odoo_multi_db_sync: parámetro creado/actualizado %s", key)
                except Exception as e:
                    _logger.exception("odoo_multi_db_sync: fallo creando parámetro %s: %s", key, e)

    @api.model
    def _get_remote_params(self):
        # Asegurar que los parámetros existan con valores por defecto (si no fueron creados aún)
        self._ensure_default_remote_params()
        param = self.env['ir.config_parameter'].sudo()
        raw_url = param.get_param('odoo_multi_db_sync.remote_url') or ''
        db_param = param.get_param('odoo_multi_db_sync.remote_db') or ''
        # Normalizar URL: si el usuario pegó el link de /web#... o similar, quedarse con scheme://netloc
        normalized_url = raw_url
        try:
            if raw_url:
                parsed = urlsplit(raw_url)
                # extraer db desde query o fragment si existe
                q = parse_qs(parsed.query or '')
                f = parse_qs(parsed.fragment or '')
                db_from_link = (q.get('db') or f.get('db') or [None])[0]
                # reconstruir base URL (scheme + netloc)
                normalized_url = urlunsplit((parsed.scheme or 'https', parsed.netloc or parsed.path, '', '', ''))
                if db_from_link:
                    db_param = db_from_link
                    _logger.info("odoo_multi_db_sync: db extraída de la URL remota: %s", db_param)
                if normalized_url != raw_url:
                    _logger.debug("odoo_multi_db_sync: URL remota normalizada de '%s' a '%s'", raw_url, normalized_url)
        except Exception:
            _logger.exception("odoo_multi_db_sync: fallo al normalizar la URL remota '%s'", raw_url)

        return {
            'url': normalized_url,
            'db': db_param,
            'user': param.get_param('odoo_multi_db_sync.remote_user'),
            'password': param.get_param('odoo_multi_db_sync.remote_password'),
            'enable_auto': param.get_param('odoo_multi_db_sync.enable_auto_sync'),
        }

    @api.model
    def _connect_remote(self):
        params = self._get_remote_params()
        if not params['url'] or not params['db'] or not params['user'] or not params['password']:
            _logger.warning("odoo_multi_db_sync: faltan parámetros de conexión remota")
            return None
        try:
            common = xmlrpc.client.ServerProxy('%s/xmlrpc/2/common' % params['url'])
            uid = common.authenticate(params['db'], params['user'], params['password'], {})
            if not uid:
                _logger.error("odoo_multi_db_sync: autenticación remota fallida")
                return None
            models_rpc = xmlrpc.client.ServerProxy('%s/xmlrpc/2/object' % params['url'])
            return {
                'uid': uid,
                'models': models_rpc,
                'db': params['db'],
                'password': params['password'],
                'url': params['url'],  # añadido: url para fallback legacy
            }
        except Exception as e:
            _logger.exception("odoo_multi_db_sync: error conectando al remoto: %s", e)
            return None

    @api.model
    def cron_sync_partners(self):
        """Método invocado por cron para sincronizar res.partner desde la DB remota."""
        params = self._get_remote_params()
        if not params.get('enable_auto') or params.get('enable_auto').lower() not in ('1','true','yes'):
            _logger.info("odoo_multi_db_sync: sincronización automática deshabilitada, saliendo.")
            return False

        conn = self._connect_remote()
        if not conn:
            return False
        try:
            fields = ['name', 'email', 'phone', 'street', 'zip', 'city', 'company_type']
            domain = []  # ajustar si desea filtrar
            remote_partners = conn['models'].execute_kw(conn['db'], conn['uid'], conn['password'],
                                                       'res.partner', 'search_read',
                                                       [domain], {'fields': fields, 'limit': 0})
            for rp in remote_partners:
                email = rp.get('email')
                vals = {
                    'name': rp.get('name') or '---',
                    'phone': rp.get('phone'),
                    'street': rp.get('street'),
                    'zip': rp.get('zip'),
                    'city': rp.get('city'),
                    'company_type': rp.get('company_type'),
                    'email': email,
                    'identification_id': rp.get('identification_id') or rp.get('vat') or False,
                }
                if email:
                    local = self.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                else:
                    # si no hay email, intentar buscar por name - opcional
                    local = self.env['res.partner'].sudo().search([('name', '=', vals['name'])], limit=1)
                if local:
                    try:
                        local.sudo().write(vals)
                    except Exception as e:
                        _logger.exception("odoo_multi_db_sync: error al actualizar partner %s: %s", local.id, e)
                else:
                    try:
                        self.env['res.partner'].sudo().create(vals)
                    except Exception as e:
                        _logger.exception("odoo_multi_db_sync: error al crear partner %s: %s", vals.get('name'), e)
            _logger.info("odoo_multi_db_sync: sincronización completada (%d partners)", len(remote_partners))
            return True
        except Exception as e:
            _logger.exception("odoo_multi_db_sync: error durante sincronización: %s", e)
            return False

class ResPartnerSend(models.Model):
    _inherit = 'res.partner'

    # identification_id es un campo computado no almacenado que refleja 'vat'
    identification_id = fields.Char(
        string='Identification ID',
        compute='_compute_identification_id',
        inverse='_inverse_identification_id',
        store=False,
    )

    def _compute_identification_id(self):
        for rec in self:
            rec.identification_id = rec.vat or ''

    def _inverse_identification_id(self):
        for rec in self:
            # Escribir lo introducido en identification_id dentro de vat (persistencia en DB existente)
            rec.vat = rec.identification_id or False

    def send_to_remote(self):
        """Enviar uno o varios partners a la base remota y notificar el resultado al usuario."""
        sync = self.env['multi.db.sync']
        conn = sync._connect_remote()
        if not conn:
            raise UserError("Conexión remota no disponible o parámetros incompletos.")
        sent = 0
        errors = []
        for partner in self:
            try:
                vals = {
                    'name': partner.name or '---',
                    'email': partner.email,
                    'phone': partner.phone,
                    'street': partner.street,
                    'zip': partner.zip,
                    'city': partner.city,
                    'company_type': partner.company_type,
                    'identification_id': partner.identification_id,  # enviar también el campo nuevo
                }
                # Buscar por email si existe, si no usar nombre
                if partner.email:
                    remote_ids = conn['models'].execute_kw(conn['db'], conn['uid'], conn['password'],
                                                          'res.partner', 'search',
                                                          [[['email', '=', partner.email]]], {'limit': 1})
                else:
                    remote_ids = conn['models'].execute_kw(conn['db'], conn['uid'], conn['password'],
                                                          'res.partner', 'search',
                                                          [[['name', '=', partner.name]]], {'limit': 1})
                if remote_ids:
                    conn['models'].execute_kw(conn['db'], conn['uid'], conn['password'],
                                              'res.partner', 'write', [remote_ids, vals])
                    sent += 1
                else:
                    conn['models'].execute_kw(conn['db'], conn['uid'], conn['password'],
                                              'res.partner', 'create', [vals])
                    sent += 1
            except Exception as e:
                _logger.exception("odoo_multi_db_sync: error al enviar partner %s al remoto: %s", partner.id, e)
                errors.append("%s: %s" % (partner.display_name, e))
        # Preparar notificación para el cliente
        if errors:
            message = "Enviados: %d. Errores: %d.\n%s" % (sent, len(errors), "\n".join(errors))
            # Mostrar notificación de error al usuario
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Resultado envío contactos',
                    'message': message,
                    'type': 'danger',
                    'sticky': True,
                }
            }
        else:
            message = "Contacto(s) enviados correctamente: %d" % sent
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Envío correcto',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

# Hook de post-instalación para asegurar parámetros desde la instalación del módulo
def post_init_hook(cr, registry):
    """Post install hook: asegurar parámetros por defecto."""
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['multi.db.sync']._ensure_default_remote_params()
    except Exception:
        _logger.exception("odoo_multi_db_sync: fallo en post_init_hook al crear parámetros por defecto")