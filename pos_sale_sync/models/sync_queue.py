import xmlrpc.client
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PosSaleSyncQueue(models.Model):
    _name = 'pos.sale.sync.queue'
    _description = 'Cola de sincronización POS -> Sale (remota)'

    pos_order_id = fields.Many2one('pos.order', string='POS Order', required=True, ondelete='cascade')
    state = fields.Selection([('draft','Draft'), ('done','Done'), ('failed','Failed')], default='draft', string='State')
    attempts = fields.Integer(default=0)
    last_error = fields.Text()
    create_date = fields.Datetime(readonly=True)

    def process_queue(self, limit=20):
        pending = self.search([('state','=','draft')], limit=limit)
        for rec in pending:
            try:
                rec._do_send()
            except Exception:
                _logger.exception('Error processing sync queue record %s', rec.id)

    def _read_params(self):
        cfg = self.env['ir.config_parameter'].sudo()
        def _p(key):
            return cfg.get_param('pos_sale_sync.' + key) or cfg.get_param('odoo_pos_remote_sync.' + key) or cfg.get_param('odoo_multi_db_sync.' + key)
        return {'url': _p('remote_url'), 'db': _p('remote_db'), 'user': _p('remote_user'), 'pwd': _p('remote_password')}

    def _connect(self, params):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(params['url']))
        uid = common.authenticate(params['db'], params['user'], params['pwd'], {})
        if not uid:
            raise UserError('Autenticación remota fallida')
        models_rpc = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(params['url']))
        return models_rpc, params['db'], uid, params['pwd']

    def _ensure_partner_remote(self, models_rpc, db, uid, pwd, local_partner):
        """Crear/actualizar partner remoto de forma segura (dominio validado y fallbacks de creación)."""
        try:
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

            domain = []
            if email:
                domain.append(('email', '=', email))
            elif name:
                domain.append(('name', '=', name))

            remote_id = False
            try:
                if domain:
                    remote_ids = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'search', [domain], {'limit': 1})
                    if remote_ids:
                        remote_id = remote_ids[0]
            except xmlrpc.client.Fault as f:
                _logger.exception("pos_sale_sync: Fault remoto buscando partner (domain=%s): %s", domain, getattr(f, 'faultString', str(f)))
            except Exception:
                _logger.exception("pos_sale_sync: error RPC buscando partner remoto (domain=%s)", domain)

            if remote_id:
                try:
                    models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'write', [[remote_id], vals_full])
                except Exception:
                    safe_vals = {k: v for k, v in vals_full.items() if v}
                    try:
                        if safe_vals:
                            models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'write', [[remote_id], safe_vals])
                    except Exception:
                        _logger.exception("pos_sale_sync: fallo actualizando partner remoto %s", remote_id)
                return remote_id
            else:
                # crear con varios niveles de detalle
                try:
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [vals_full])
                    return pid
                except xmlrpc.client.Fault as f:
                    _logger.exception("pos_sale_sync: Fault remoto creando partner con vals_full %s: %s", vals_full, getattr(f, 'faultString', str(f)))
                except Exception:
                    _logger.exception("pos_sale_sync: fallo creando partner remoto con vals_full %s", vals_full)
                # name+email
                try:
                    vals_email = {'name': vals_full['name']}
                    if vals_full.get('email'):
                        vals_email['email'] = vals_full['email']
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [vals_email])
                    return pid
                except Exception:
                    _logger.warning("pos_sale_sync: fallback crear partner name+email falló", exc_info=True)
                # solo name
                try:
                    pid = models_rpc.execute_kw(db, uid, pwd, 'res.partner', 'create', [{'name': vals_full['name']}])
                    return pid
                except Exception:
                    _logger.exception("pos_sale_sync: fallback crear partner solo name falló para '%s'", vals_full['name'])
                    return False
        except Exception:
            _logger.exception("pos_sale_sync: error asegurando partner remoto (outer)")
            return False

    def _get_rate(self):
        """Leer tasa de conversión desde parámetros (fallback 1.0)."""
        cfg = self.env['ir.config_parameter'].sudo()
        val = cfg.get_param('pos_sale_sync.remote_rate') or cfg.get_param('odoo_pos_remote_sync.remote_rate') or cfg.get_param('odoo_multi_db_sync.remote_rate') or '1.0'
        try:
            return float(val)
        except Exception:
            return 1.0

    def _ensure_product_remote(self, models_rpc, db, uid, pwd, local_prod, price=0.0):
        """Buscar producto remoto por default_code/barcode/name (name usa ilike);
        antes de crear, volver a buscar por name para evitar duplicados.
        Devuelve (product_id, product_uom_id) o (False, False) si falla."""
        try:
            name = (getattr(local_prod, 'name', None) or '').strip() if local_prod else ''
            barcode = getattr(local_prod, 'barcode', None) if local_prod else None
            default_code = getattr(local_prod, 'default_code', None) if local_prod else None

            # Prioridad de búsqueda: barcode > default_code > name (ilike)
            domains_to_try = []
            if barcode:
                domains_to_try.append([('barcode','=', barcode)])
            if default_code:
                domains_to_try.append([('default_code','=', default_code)])
            if name:
                domains_to_try.append([('name','ilike', name)])

            # Intentar product.product primero
            for domain in domains_to_try:
                try:
                    found = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'search', [domain], {'limit':1})
                    if found:
                        pid = found[0]
                        try:
                            pr = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'read', [[pid], ['uom_id']], {})
                            uom = pr[0].get('uom_id') and pr[0]['uom_id'][0] or False
                        except Exception:
                            uom = False
                        return pid, uom
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda product.product falló para domain %s", domain, exc_info=True)

            # Intentar product.template (si no se encontró variant)
            for domain in domains_to_try:
                try:
                    found_t = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'search', [domain], {'limit':1})
                    if found_t:
                        tid = found_t[0]
                        tread = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'read', [[tid], ['product_variant_ids', 'uom_id']], {})
                        if tread and tread[0].get('product_variant_ids'):
                            try:
                                return tread[0]['product_variant_ids'][0], (tread[0].get('uom_id') and tread[0]['uom_id'][0]) or False
                            except Exception:
                                return tread[0]['product_variant_ids'][0], False
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda product.template falló para domain %s", domain, exc_info=True)

            # Antes de crear: reintento amplio por nombre (ilike) para evitar duplicados
            if name:
                try:
                    # buscar en product.product por name ilike
                    found_by_name = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'search', [[('name','ilike', name)]], {'limit':1})
                    if found_by_name:
                        pid = found_by_name[0]
                        try:
                            pr = models_rpc.execute_kw(db, uid, pwd, 'product.product', 'read', [[pid], ['uom_id']], {})
                            uom = pr[0].get('uom_id') and pr[0]['uom_id'][0] or False
                        except Exception:
                            uom = False
                        _logger.info("pos_sale_sync: product encontrado por nombre antes de crear, usando id %s", pid)
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
                            _logger.info("pos_sale_sync: product.template encontrado por nombre antes de crear, usando variant %s", var)
                            return var, uom
                except Exception:
                    _logger.debug("pos_sale_sync: búsqueda preventiva template por nombre falló", exc_info=True)

            # Preparar vals mínimos para crear template (fallback)
            vals_template = {
                'name': name or (default_code or 'Producto POS'),
                'list_price': float(price or 0.0),
                'default_code': default_code or False,
                'barcode': barcode or False,
                'type': 'product',
            }
            # intentar resolver uom remoto por factor 1 o nombre 'unit'
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

            # crear template remoto
            try:
                tid = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'create', [vals_template])
                # leer variantes
                tread2 = models_rpc.execute_kw(db, uid, pwd, 'product.template', 'read', [[tid], ['product_variant_ids', 'uom_id']], {})
                if tread2 and tread2[0].get('product_variant_ids'):
                    var_id = tread2[0]['product_variant_ids'][0]
                    uom_from_template = (tread2[0].get('uom_id') and tread2[0]['uom_id'][0]) or uom_id or False
                    return var_id, uom_from_template
            except Exception:
                _logger.exception("pos_sale_sync: fallo creando product.template remoto para %s", vals_template)
                # fallback: intentar crear product.product mínimo
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

    def _parse_rate(self, v):
        if v is None:
            return None
        if isinstance(v, (float, int)):
            return float(v)
        try:
            s = str(v).strip()
            if not s:
                return None
            s = s.replace(' ', '')
            if '.' in s and ',' in s:
                if s.rfind(',') > s.rfind('.'):
                    s = s.replace('.', '')
                    s = s.replace(',', '.')
                else:
                    s = s.replace(',', '')
            else:
                if ',' in s and '.' not in s:
                    s = s.replace(',', '.')
                if s.count('.') > 1 and ',' not in s:
                    s = s.replace('.', '')
            return float(s)
        except Exception:
            try:
                return float(s.replace(',', '').replace('.', ''))
            except Exception:
                return None

    def _do_send(self):
        self.ensure_one()
        self.attempts = self.attempts + 1
        params = self._read_params()
        if not all([params.get('url'), params.get('db'), params.get('user'), params.get('pwd')]):
            self.state = 'failed'
            self.last_error = 'Faltan parámetros de configuración (remote_url/db/user/password)'
            return

        pos_order = self.pos_order_id
        try:
            models_rpc, db, uid, pwd = self._connect(params)

            # Evitar duplicados: buscar sale.order con origin = pos_order.name
            existing = models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'search', [[('origin','=', pos_order.name)]], {'limit':1})
            if existing:
                self.state = 'done'
                self.last_error = 'Ya existe sale.order remoto con origin {}'.format(pos_order.name)
                return

            # partner: buscar/crear/actualizar con campos completos
            partner_id = False
            if pos_order.partner_id:
                partner_id = self._ensure_partner_remote(models_rpc, db, uid, pwd, pos_order.partner_id)
            else:
                fake = type('P', (), {'name': pos_order.partner_name or 'Cliente POS', 'email': False, 'phone': False, 'street': False, 'zip': False, 'city': False, 'vat': False})()
                partner_id = self._ensure_partner_remote(models_rpc, db, uid, pwd, fake)

            if not partner_id:
                self.state = 'failed'
                self.last_error = 'No se pudo crear/actualizar el cliente remoto'
                return

            # obtener tasa desde el pedido si existe (PRIORIDAD: ir.config_parameter por pedido -> campos explícitos -> parámetro global)
            order_rate = None
            try:
                param = self.env['ir.config_parameter'].sudo()
                key = 'pos_sale_sync.remote_rate_order_%s' % (pos_order.id)
                v_param = param.get_param(key)
                parsed = self._parse_rate(v_param)
                if parsed is not None and parsed > 0:
                    order_rate = parsed
                    _logger.info('pos_sale_sync: usando tasa desde ir.config_parameter para pedido %s -> %s', pos_order.id, order_rate)
                else:
                    # campos explícitos en orden de prioridad
                    for fld in ('rate_order', 'currency_rate', 'currency_rate', 'exchange_rate', 'tasa', 'tasa_usd', 'tipo_cambio', 'rate'):
                        try:
                            v = getattr(pos_order, fld, False)
                            parsed = self._parse_rate(v)
                            if parsed is not None and parsed > 0:
                                order_rate = parsed
                                _logger.info('pos_sale_sync: usando tasa desde campo %s para pedido %s -> %s', fld, pos_order.id, order_rate)
                                break
                        except Exception:
                            continue
            except Exception:
                order_rate = None
            rate = order_rate or self._get_rate() or 1.0
            _logger.debug('pos_sale_sync: tasa final usada para conversión pedido %s = %s', pos_order.id, rate)

            # construir líneas (igual que antes pero usando ensure_product_remote y conversión)
            order_lines = []
            for line in pos_order.lines:
                qty = float(line.qty) if line.qty else 0.0
                price = float(line.price_unit) if line.price_unit else 0.0
                prod = line.product_id
                product_id = False
                product_uom = False

                # intentar asegurar producto remoto (buscar/crear)
                product_id, product_uom = self._ensure_product_remote(models_rpc, db, uid, pwd, prod, price)

                # convertir precio a moneda remota (Bs)
                price_bs = round(price * float(rate), 6)

                line_vals = {
                    'name': (prod.name if prod else (line.product_name or 'Línea POS')),
                    'product_uom_qty': qty,
                    'price_unit': price_bs,
                }
                if product_id:
                    line_vals['product_id'] = product_id
                # siempre intentar asignar UoM si la conocemos (requerida por constraint)
                if product_uom:
                    line_vals['product_uom'] = product_uom
                order_lines.append((0, 0, line_vals))

            order_vals = {
                'partner_id': partner_id,
                'order_line': order_lines,
                'origin': pos_order.name,
                'client_order_ref': pos_order.pos_reference or pos_order.name,
            }

            try:
                order_id = models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'create', [order_vals])
                # intentar confirmar el presupuesto remoto inmediatamente
                try:
                    models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'action_confirm', [[order_id]])
                    _logger.info('pos_sale_sync: sale.order remoto %s confirmado tras creación', order_id)
                except Exception:
                    _logger.exception('pos_sale_sync: no se pudo confirmar sale.order remoto %s tras creación', order_id)
                # publicar tasa en la venta remota
                try:
                    models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'message_post', [[order_id], {'body': 'Tasa usada para conversión: %s' % (rate)}])
                except Exception:
                    _logger.exception('pos_sale_sync: no se pudo publicar message_post en sale.order remoto %s', order_id)
                # guardar tasa en parámetros del sistema por pedido (evita requerir columna en pos.order)
                try:
                    param = self.env['ir.config_parameter'].sudo()
                    param.set_param('pos_sale_sync.remote_rate_order_%s' % (pos_order.id), str(rate))
                except Exception:
                    _logger.exception('pos_sale_sync: no se pudo guardar remote rate en parámetros para pos.order %s', pos_order.id)
                self.state = 'done'
                self.last_error = 'OK: {}'.format(order_id)
            except Exception as e:
                _logger.exception('Error creando sale.order remoto para pos_order %s', pos_order.id)
                # Comprobar si, a pesar de la excepción, la venta fue creada en remoto
                try:
                    existing_after = models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'search', [[('origin', '=', pos_order.name)]], {'limit': 1})
                    if existing_after:
                        order_id = existing_after[0]
                        # intentar confirmar la orden encontrada
                        try:
                            models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'action_confirm', [[order_id]])
                            _logger.info('pos_sale_sync: sale.order remoto %s confirmado tras detectarse existente', order_id)
                        except Exception:
                            _logger.exception('pos_sale_sync: no se pudo confirmar sale.order remoto %s tras detectarse existente', order_id)
                        # publicar tasa y guardar tasa local en parámetros si se detectó la orden remota
                        try:
                            models_rpc.execute_kw(db, uid, pwd, 'sale.order', 'message_post', [[order_id], {'body': 'Tasa usada para conversión: %s' % (rate)}])
                        except Exception:
                            _logger.exception('pos_sale_sync: no se pudo publicar message_post tras fallo para sale.order %s', order_id)
                        try:
                            param = self.env['ir.config_parameter'].sudo()
                            param.set_param('pos_sale_sync.remote_rate_order_%s' % (pos_order.id), str(rate))
                        except Exception:
                            _logger.exception('pos_sale_sync: no se pudo guardar remote rate en parámetros para pos.order %s', pos_order.id)
                        self.state = 'done'
                        self.last_error = 'OK (detectado tras fallo): {}'.format(order_id)
                        _logger.info('pos_sale_sync: sale.order remoto detectado tras fallo, id=%s', order_id)
                        return
                except Exception:
                    _logger.exception('pos_sale_sync: error comprobando existencia de sale.order tras fallo', exc_info=True)
                # Si no existe, mantener lógica de reintentos/errores
                self.last_error = str(e)
                if self.attempts >= 5:
                    self.state = 'failed'
                else:
                    self.state = 'draft'
        except Exception as e:
            _logger.exception('Error sync POS -> Sale remoto for pos_order %s', pos_order.id)
            self.last_error = str(e)
            if self.attempts >= 5:
                self.state = 'failed'
            else:
                self.state = 'draft'
