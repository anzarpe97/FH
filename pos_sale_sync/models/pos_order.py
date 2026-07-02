from odoo import models, api, fields
from odoo.exceptions import UserError
import xmlrpc.client
import logging
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    sync_queue_id = fields.Many2one('pos.sale.sync.queue', string='Sync queue')
    # Eliminar la declaración del campo remote_sent_rate (se guardará en ir.config_parameter)

    # Valores por defecto (tomados de tu indicación)
    _DEFAULT_REMOTE_URL = 'https://bddfarruggio.odoo.com'
    _DEFAULT_REMOTE_USER = 'soporteodoo@contablesag.com'
    _DEFAULT_REMOTE_PASSWORD = '123'

    def _ensure_default_remote_params(self, cfg):
        """Escribe parámetros por defecto en ir.config_parameter si no existen.
        Registra ambos prefijos para compatibilidad: pos_sale_sync.* y odoo_pos_remote_sync.*.
        """
        changed = False
        # prefijos a cubrir
        keys = [
            ('pos_sale_sync.remote_url', 'odoo_pos_remote_sync.remote_url', self._DEFAULT_REMOTE_URL),
            ('pos_sale_sync.remote_user', 'odoo_pos_remote_sync.remote_user', self._DEFAULT_REMOTE_USER),
            ('pos_sale_sync.remote_password', 'odoo_pos_remote_sync.remote_password', self._DEFAULT_REMOTE_PASSWORD),
        ]
        for k1, k2, val in keys:
            if not cfg.get_param(k1) and not cfg.get_param(k2):
                cfg.set_param(k1, val)
                cfg.set_param(k2, val)
                changed = True

        # intentar inferir remote_db y escribir en ambos prefijos si faltan
        if not cfg.get_param('pos_sale_sync.remote_db') and not cfg.get_param('odoo_pos_remote_sync.remote_db'):
            try:
                parsed = urlparse(self._DEFAULT_REMOTE_URL)
                host = parsed.netloc.split(':')[0]
                db_guess = host.split('.')[0] if host else ''
                if db_guess:
                    cfg.set_param('pos_sale_sync.remote_db', db_guess)
                    cfg.set_param('odoo_pos_remote_sync.remote_db', db_guess)
                    changed = True
            except Exception:
                pass
        return changed

    @api.model
    def create(self, vals):
        order = super(PosOrder, self).create(vals)
        try:
            # Encolar cuando el pedido esté pagado/publicado; ajusta según tu flujo POS.
            state = vals.get('state') or order.state
            if state in ('paid', 'done', 'invoiced'):
                self.env['pos.sale.sync.queue'].create({
                    'pos_order_id': order.id,
                })
        except Exception:
            # No bloquear la creación de pedidos por errores de cola
            pass
        return order

    def _try_fix_remote_partner_fiscal(self, models_rpc, db, uid, pwd, remote_partner_id):
        """Intentar escribir campos fiscales en el partner remoto a partir del partner local.
        Devuelve True si se escribió algo, False si no se pudo o no había datos.
        """
        try:
            local_p = self.partner_id
            if not local_p or not remote_partner_id:
                return False
            vals = {}
            # VAT / NIT
            if getattr(local_p, 'vat', False):
                vals['vat'] = getattr(local_p, 'vat')
            # l10n_latam identification type (si existe en el local)
            local_idtype = getattr(local_p, 'l10n_latam_identification_type_id', False)
            if local_idtype and getattr(local_idtype, 'name', False):
                # intentar buscar el mismo tipo en remoto por name o l10n_code
                try:
                    # buscar por nombre primero
                    rem = models_rpc.execute_kw(db, uid, pwd, 'l10n_latam.identification.type', 'search', [[['name', '=', local_idtype.name]]], {'limit': 1})
                    if not rem and getattr(local_idtype, 'l10n_code', False):
                        rem = models_rpc.execute_kw(db, uid, pwd, 'l10n_latam.identification.type', 'search', [[['l10n_code', '=', local_idtype.l10n_code]]], {'limit': 1})
                    if rem:
                        vals['l10n_latam_identification_type_id'] = rem[0]
                except Exception:
                    # modelo no existe o búsqueda falló; ignorar
                    _logger.debug("pos_sale_sync: no se pudo mapear l10n_latam_identification_type en remoto", exc_info=True)
            # otros campos posibles (nombres comunes en addons venezuela/localizaciones)
            # 'document_number' o 'registro_fiscal' si local los tiene
            for fld in ('document_number', 'registro_fiscal', 'rif',):
                if getattr(local_p, fld, False) and fld not in vals:
                    vals[fld] = getattr(local_p, fld)
            if not vals:
                return False
            # escribir en partner remoto
            models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'write', [[remote_partner_id], vals])
            _logger.info("pos_sale_sync: partner remoto %s actualizado con vals %s", remote_partner_id, vals)
            return True
        except Exception:
            _logger.exception("pos_sale_sync: fallo intentando actualizar partner remoto %s", remote_partner_id)
            return False

    def _read_remote_params(self):
        """Leer parámetros remotos soportando varios prefijos."""
        cfg = self.env['ir.config_parameter'].sudo()
        def _p(key):
            return cfg.get_param('pos_sale_sync.' + key) or cfg.get_param('odoo_pos_remote_sync.' + key) or cfg.get_param('odoo_multi_db_sync.' + key)
        return {
            'url': _p('remote_url'),
            'db': _p('remote_db'),
            'user': _p('remote_user'),
            'pwd': _p('remote_password'),
        }

    def _connect_remote(self, params):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(params['url']))
        uid = common.authenticate(params['db'], params['user'], params['pwd'], {})
        if not uid:
            raise UserError('Autenticación remota fallida')
        models_rpc = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(params['url']))
        return models_rpc, params['db'], uid, params['pwd']

    def _ensure_partner_remote(self, models_rpc, db, uid, pwd, local_partner):
        """Buscar/crear/actualizar partner remoto. Construye dominio seguro y evita pasar tuplas inválidas."""
        try:
            # preparar valores a enviar
            name = getattr(local_partner, 'name', None) or getattr(local_partner, 'display_name', None) or False
            email = getattr(local_partner, 'email', None) or False
            vals_full = {
                'name': name or 'Cliente POS',
                'email': email or False,
                'phone': getattr(local_partner, 'phone', False) or False,
                'street': getattr(local_partner, 'street', False) or False,
                'zip': getattr(local_partner, 'zip', False) or False,
                'city': getattr(local_partner, 'city', False) or False,
            }
            if getattr(local_partner, 'vat', False):
                vals_full['vat'] = local_partner.vat
            for fld in ('identification_id','document_number','rif'):
                if getattr(local_partner, fld, False):
                    vals_full[fld] = getattr(local_partner, fld)

            # construir dominio seguro (solo tuplas con valor válido)
            domain = []
            if email:
                domain.append(('email', '=', email))
            elif name:
                domain.append(('name', '=', name))

            # si no hay criterio seguro, no llamar a search (crear directamente)
            remote_id = False
            try:
                if domain:
                    remote_ids = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'search', [domain], {'limit': 1})
                    if remote_ids:
                        remote_id = remote_ids[0]
                # si no hay resultados y domain vacío o no encontró, crear
            except xmlrpc.client.Fault as f:
                _logger.exception("pos_sale_sync: Fault remoto buscando partner (domain=%s): %s", domain, getattr(f, 'faultString', str(f)))
                # No detener: intentaremos crear si es posible
            except Exception:
                _logger.exception("pos_sale_sync: error RPC buscando partner remoto (domain=%s)", domain)

            if remote_id:
                # intentar actualizar
                try:
                    models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'write', [[remote_id], vals_full])
                except Exception:
                    # intentar escribir solo campos no vacíos
                    safe_vals = {k: v for k, v in vals_full.items() if v}
                    try:
                        if safe_vals:
                            models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'write', [[remote_id], safe_vals])
                    except Exception:
                        _logger.exception("pos_sale_sync: fallo actualizando partner remoto %s", remote_id)
                return remote_id
            else:
                # intentar crear con varios fallbacks
                try:
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [vals_full])
                    return pid
                except xmlrpc.client.Fault as f:
                    _logger.exception("pos_sale_sync: Fault remoto creando partner con vals_full %s: %s", vals_full, getattr(f, 'faultString', str(f)))
                except Exception:
                    _logger.exception("pos_sale_sync: fallo creando partner remoto con vals_full %s", vals_full)

                # fallback name+email
                try:
                    vals_email = {'name': vals_full['name']}
                    if vals_full.get('email'):
                        vals_email['email'] = vals_full['email']
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [vals_email])
                    return pid
                except Exception:
                    _logger.warning("pos_sale_sync: fallback crear partner name+email falló para %s", vals_full['name'], exc_info=True)

                # fallback solo name
                try:
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [{'name': vals_full['name']}])
                    return pid
                except Exception:
                    _logger.exception("pos_sale_sync: fallback crear partner solo name falló para %s", vals_full['name'])
                    return False
        except Exception:
            _logger.exception("pos_sale_sync: error asegurando partner remoto (outer)")
            return False

    def _get_rate(self, cfg):
        val = cfg.get_param('pos_sale_sync.remote_rate') or cfg.get_param('odoo_pos_remote_sync.remote_rate') or cfg.get_param('odoo_multi_db_sync.remote_rate') or '1.0'
        try:
            return float(val)
        except Exception:
            return 1.0

    def _ensure_product_remote(self, models_rpc, db, uid, pwd, local_prod, price=0.0):
        """Buscar producto remoto por default_code/barcode/name (name usa ilike).
        Antes de crear, buscar por nombre para evitar duplicados; si no existe, crear template/variant.
        Devuelve (product_id, product_uom_id) o (False, False) si falla."""
        try:
            name = (getattr(local_prod, 'name', None) or '').strip() if local_prod else ''
            barcode = getattr(local_prod, 'barcode', None) if local_prod else None
            default_code = getattr(local_prod, 'default_code', None) if local_prod else None

            domains = []
            if barcode:
                domains.append([('barcode','=', barcode)])
            if default_code:
                domains.append([('default_code','=', default_code)])
            if name:
                domains.append([('name','ilike', name)])

            # buscar product.product por dominios
            for d in domains:
                try:
                    found = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'search', [d], {'limit':1})
                    if found:
                        pid = found[0]
                        try:
                            pr = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'read', [[pid], ['uom_id']], {})
                            uom = pr[0].get('uom_id') and pr[0]['uom_id'][0] or False
                        except Exception:
                            uom = False
                        return pid, uom
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda product.product falló para domain %s", d, exc_info=True)

            # buscar product.template por dominios
            for d in domains:
                try:
                    found_t = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'search', [d], {'limit':1})
                    if found_t:
                        tid = found_t[0]
                        tread = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'read', [[tid], ['product_variant_ids', 'uom_id']], {})
                        if tread and tread[0].get('product_variant_ids'):
                            return tread[0]['product_variant_ids'][0], (tread[0].get('uom_id') and tread[0]['uom_id'][0]) or False
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda product.template falló para domain %s", d, exc_info=True)

            # búsqueda preventiva por nombre antes de crear
            if name:
                try:
                    found_by_name = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'search', [[('name','ilike', name)]], {'limit':1})
                    if found_by_name:
                        pid = found_by_name[0]
                        try:
                            pr = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'read', [[pid], ['uom_id']], {})
                            uom = pr[0].get('uom_id') and pr[0]['uom_id'][0] or False
                        except Exception:
                            uom = False
                        _logger.info("pos_sale_sync: producto encontrado por nombre antes de crear: %s", pid)
                        return pid, uom
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda preventiva por nombre falló", exc_info=True)

                try:
                    found_t_by_name = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'search', [[('name','ilike', name)]], {'limit':1})
                    if found_t_by_name:
                        tid = found_t_by_name[0]
                        tread = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'read', [[tid], ['product_variant_ids', 'uom_id']], {})
                        if tread and tread[0].get('product_variant_ids'):
                            var = tread[0]['product_variant_ids'][0]
                            uom = (tread[0].get('uom_id') and tread[0]['uom_id'][0]) or False
                            _logger.info("pos_sale_sync: product.template encontrado por nombre antes de crear, variant %s", var)
                            return var, uom
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda preventiva template por nombre falló", exc_info=True)

            # preparar vals y crear template/product como fallback (igual que antes)
            vals_template = {
                'name': name or (default_code or 'Producto POS'),
                'list_price': float(price or 0.0),
                'default_code': default_code or False,
                'barcode': barcode or False,
                'type': 'product',
            }
            uom_id = False
            try:
                uom_search = models_rpc.execute_kw(db, uid, pwd, 'uom.uom', 'search', [[('factor', '=', 1.0)]], {'limit':1})
                if not uom_search:
                    uom_search = models_rpc.execute_kw(db, uid, pwd, 'uom.uom', 'search', [[('name', 'ilike', 'unit')]], {'limit':1})
                if uom_search:
                    uom_id = uom_search[0]
                    vals_template['uom_id'] = uom_id
                    vals_template['uom_po_id'] = uom_id
            except Exception:
                _logger.debug("pos_sale_sync: no se pudo resolver UoM remoto por defecto", exc_info=True)

            # crear template remoto y devolver primera variante
            try:
                tid = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'create', [vals_template])
                tread2 = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'read', [[tid], ['product_variant_ids', 'uom_id']], {})
                if tread2 and tread2[0].get('product_variant_ids'):
                    var_id = tread2[0]['product_variant_ids'][0]
                    uom_from_template = (tread2[0].get('uom_id') and tread2[0]['uom_id'][0]) or uom_id or False
                    return var_id, uom_from_template
            except Exception:
                _logger.exception("pos_sale_sync: fallo creando product.template remoto para %s", vals_template)
                # fallback: crear product.product mínimo
                try:
                    pid = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'create', [{'name': vals_template['name'], 'list_price': vals_template['list_price']}])
                    try:
                        prr = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'read', [[pid], ['uom_id']], {})
                        uom_try = prr[0].get('uom_id') and prr[0]['uom_id'][0] or uom_id or False
                    except Exception:
                        uom_try = uom_id or False
                    return pid, uom_try
                except Exception:
                    _logger.exception("pos_sale_sync: fallback crear product.product falló para %s", vals_template['name'])
                    return False, False

        except Exception:
            _logger.exception("pos_sale_sync: error en ensure_product_remote")
            return False, False

    # helper para parsear tasas con formatos como "205,6754" o "1.234,56" o "1234.56"
    def _parse_rate(self, v):
        if v is None:
            return None
        if isinstance(v, (float, int)):
            return float(v)
        try:
            s = str(v).strip()
            if not s:
                return None
            # eliminar espacios
            s = s.replace(' ', '')
            # si contiene ambos separadores, asumir que el punto es miles y la coma decimal
            if '.' in s and ',' in s:
                if s.rfind(',') > s.rfind('.'):
                    s = s.replace('.', '')
                    s = s.replace(',', '.')
                else:
                    # caso ambigüo: preferir eliminar comas
                    s = s.replace(',', '')
            else:
                # solo coma -> coma decimal
                if ',' in s and '.' not in s:
                    s = s.replace(',', '.')
                # varios puntos posibles de miles -> eliminar
                if s.count('.') > 1 and ',' not in s:
                    s = s.replace('.', '')
            return float(s)
        except Exception:
            try:
                # último recurso: quitar comas y puntos
                return float(s.replace(',', '').replace('.', ''))
            except Exception:
                return None

    def action_send_sale_remote(self):
        """Enviar este pedido POS a la base remota como presupuesto (sale.order)."""
        self.ensure_one()
        cfg = self.env['ir.config_parameter'].sudo()
        params = self._read_remote_params()
        if not all([params.get('url'), params.get('db'), params.get('user'), params.get('pwd')]):
            # si faltan parámetros usar el helper anterior para escribir defaults si quieres;
            raise UserError('Faltan parámetros de configuración remota. Configure en Parámetros del sistema.')

        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(params['url']))
            uid = common.authenticate(params['db'], params['user'], params['pwd'], {})
            if not uid:
                raise UserError('Autenticación remota fallida')
            models_rpc = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(params['url']))

            # Evitar duplicados por origin
            existing = models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'search', [[('origin','=', self.name)]], {'limit':1})
            if existing:
                msg = 'Ya existe sale.order remoto con origin {}'.format(self.name)
                self.message_post(body=msg)
                return True

            # Asegurar partner remoto (buscar/crear/actualizar con campos importantes)
            partner_id = False
            if self.partner_id:
                partner_id = self._ensure_partner_remote(models_rpc, params['db'], uid, params['pwd'], self.partner_id)
            else:
                # usar partner_name si no hay partner_id
                fake = type('P', (), {'name': self.partner_name or 'Cliente POS', 'email': False, 'phone': False, 'street': False, 'zip': False, 'city': False, 'vat': False})()
                partner_id = self._ensure_partner_remote(models_rpc, params['db'], uid, params['pwd'], fake)

            if not partner_id:
                raise UserError('No se pudo crear/actualizar el cliente en la base remota.')

            # obtener tasa: PRIORIDAD -> tasa guardada en ir.config_parameter por pedido -> campos del pedido -> parámetro global
            order_rate = None
            try:
                param = self.env['ir.config_parameter'].sudo()
                key = 'pos_sale_sync.remote_rate_order_%s' % (self.id)
                v_param = param.get_param(key)
                parsed = self._parse_rate(v_param)
                if parsed is not None and parsed > 0:
                    order_rate = parsed
                    _logger.info('pos_sale_sync: usando tasa desde ir.config_parameter para pedido %s -> %s', self.id, order_rate)
                else:
                    for fld in ('rate_order', 'currency_rate', 'exchange_rate', 'tasa', 'tasa_usd', 'tipo_cambio', 'rate'):
                        try:
                            v = getattr(self, fld, False)
                            parsed = self._parse_rate(v)
                            if parsed is not None and parsed > 0:
                                order_rate = parsed
                                _logger.info('pos_sale_sync: usando tasa desde campo %s para pedido %s -> %s', fld, self.id, order_rate)
                                break
                        except Exception:
                            continue
            except Exception:
                order_rate = None
            rate = order_rate or self._get_rate(cfg) or 1.0
            _logger.debug('pos_sale_sync: tasa final usada para conversión pedido %s = %s', self.id, rate)

            # Construir líneas (usando _ensure_product_remote y conversión a Bs con la tasa del pedido)
            order_lines = []
            for line in self.lines:
                qty = float(line.qty) if line.qty else 0.0
                price = float(line.price_unit) if line.price_unit else 0.0
                prod = line.product_id
                product_id = False
                product_uom = False

                product_id, product_uom = self._ensure_product_remote(models_rpc, params['db'], uid, params['pwd'], prod, price)

                # convertir precio con la tasa del pedido
                price_bs = round(price * float(rate), 6)

                line_vals = {
                    'name': prod.name if prod else (line.product_name or 'Línea POS'),
                    'product_uom_qty': qty,
                    'price_unit': price_bs,
                }
                if product_id:
                    line_vals['product_id'] = int(product_id)
                if product_uom:
                    line_vals['product_uom'] = int(product_uom)
                order_lines.append((0, 0, line_vals))

            order_vals = {
                'partner_id': partner_id,
                'order_line': order_lines,
                'origin': self.name,
                'client_order_ref': self.pos_reference or self.name,
            }

            # Intentar crear sale.order remoto
            order_id = False
            try:
                order_id = models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'create', [order_vals])
                # intentar confirmar el presupuesto remoto inmediatamente
                try:
                    models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'action_confirm', [[order_id]])
                    _logger.info('pos_sale_sync: sale.order remoto %s confirmado tras creación (manual send)', order_id)
                except Exception:
                    _logger.exception('pos_sale_sync: no se pudo confirmar sale.order remoto %s tras creación (manual send)', order_id)
            except Exception as e:
                _logger.exception("pos_sale_sync: fallo creando sale.order remoto, order_vals=%s", order_vals)
                # comprobar si fue creado pese al fallo
                try:
                    existing_after = models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'search', [[('origin','=', self.name)]], {'limit':1})
                    if existing_after:
                        order_id = existing_after[0]
                        # intentar confirmar la orden encontrada
                        try:
                            models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'action_confirm', [[order_id]])
                            _logger.info('pos_sale_sync: sale.order remoto %s confirmado tras detectarse existente (manual send)', order_id)
                        except Exception:
                            _logger.exception('pos_sale_sync: no se pudo confirmar sale.order remoto %s tras detectarse existente (manual send)', order_id)
                    else:
                        raise
                except Exception:
                    raise UserError("Error remoto creando presupuesto: %s. Ver logs del servidor para detalles." % e)

            # publicar tasa usada en la venta remota (chatter) y guardar en parametros del sistema por pedido
            try:
                models_rpc.execute_kw(params['db'], uid, params['pwd'], 'sale.order', 'message_post', [[order_id], {'body': 'Tasa usada para conversión: %s' % (rate)}])
            except Exception:
                _logger.exception("pos_sale_sync: no se pudo publicar message_post en sale.order remoto %s", order_id)
            # guardar tasa en ir.config_parameter con key por pedido (no se crea columna en pos.order)
            try:
                param = self.env['ir.config_parameter'].sudo()
                param.set_param('pos_sale_sync.remote_rate_order_%s' % (self.id), str(rate))
            except Exception:
                _logger.exception("pos_sale_sync: no se pudo guardar remote rate en parámetros para pos.order %s", self.id)

            msg = 'Presupuesto creado en remoto (sale.order id: %s) usando tasa %s' % (order_id, rate)
            self.message_post(body=msg)
            return True

        except UserError:
            raise
        except Exception as e:
            _logger.exception('Error enviando POS order %s al remoto', self.id)
            raise UserError('Error enviando al remoto: %s' % e)
