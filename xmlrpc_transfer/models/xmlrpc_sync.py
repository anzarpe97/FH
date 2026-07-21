import xmlrpc.client
import logging
from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN BDD RECEPTORA (ESCRITURA VÍA XML-RPC)
# ==========================================
URL_RECEPTORA = 'https://eudoleon-demofarru2.odoo.com/'
DB_RECEPTORA = 'eudoleon-demofarru2-p-34854774'
USER_RECEPTORA = 'admin'
PASS_RECEPTORA = '123'

class XmlrpcSyncBase(models.AbstractModel):
    _name = 'xmlrpc.sync.base'
    _description = 'Lógica base para sincronización XML-RPC'

    @api.model
    def _get_xmlrpc_connection(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{URL_RECEPTORA}/xmlrpc/2/common')
            uid = common.authenticate(DB_RECEPTORA, USER_RECEPTORA, PASS_RECEPTORA, {})
            if not uid:
                raise UserError("Fallo la autenticación XML-RPC con la base de datos receptora. Verifique las credenciales.")
            models_proxy = xmlrpc.client.ServerProxy(f'{URL_RECEPTORA}/xmlrpc/2/object')
            return uid, models_proxy
        except Exception as e:
            _logger.error("Error conectando vía XML-RPC: %s", e)
            raise UserError(f"Error conectando vía XML-RPC: {e}")

    @api.model
    def _find_remote_record(self, uid, models_proxy, model_name, search_domain, fields_to_read=['id']):
        res = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, model_name, 'search_read', [search_domain], {'fields': fields_to_read, 'limit': 1})
        if res:
            return res[0]['id']
        return False

    @api.model
    def _create_remote_partner(self, uid, models_proxy, partner):
        """ Crea el partner en la base receptora aplicando localización venezolana si aplica """
        company_type = partner.company_type or 'person'
        
        vals = {
            'name': partner.name,
            'company_type': company_type,
            'vat': partner.vat or '',
            'email': partner.email or '',
            'phone': partner.phone or '',
            'street': partner.street or '',
        }
        
        # Intentar inyectar campos específicos de localización
        if partner.vat:
            vals['rif'] = partner.vat
            vals['identification_id'] = partner.vat
            
        # Consultar dinámicamente cada campo por separado para evitar que falle toda la llamada si uno no existe
        if company_type == 'company':
            try:
                fields_info = models_proxy.execute_kw(
                    DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.partner', 'fields_get',
                    [['people_type_company']], {'attributes': ['selection']}
                )
                if 'people_type_company' in fields_info:
                    sel = fields_info['people_type_company'].get('selection') or []
                    pjnd_key = next((item[0] for item in sel if str(item[0]).lower() == 'pjnd'), False)
                    if pjnd_key:
                        vals['people_type_company'] = pjnd_key
                    elif sel:
                        vals['people_type_company'] = sel[0][0]
            except Exception as es:
                _logger.warning("Fallo al obtener people_type_company via XML-RPC: %s", es)
        else:
            try:
                fields_info = models_proxy.execute_kw(
                    DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.partner', 'fields_get',
                    [['people_type_individual']], {'attributes': ['selection']}
                )
                if 'people_type_individual' in fields_info:
                    sel = fields_info['people_type_individual'].get('selection') or []
                    pnrn_key = next((item[0] for item in sel if str(item[0]).lower() == 'pnrn'), False)
                    if pnrn_key:
                        vals['people_type_individual'] = pnrn_key
                    elif sel:
                        vals['people_type_individual'] = sel[0][0]
            except Exception as es:
                _logger.warning("Fallo al obtener people_type_individual via XML-RPC: %s", es)
            
        try:
            # Intentamos la creación con todos los campos (incluyendo los de localización)
            remote_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.partner', 'create', [vals])
            return remote_id
        except Exception as e:
            _logger.warning("Fallo la creación detallada del cliente %s, reintentando con campos básicos. Error: %s", partner.name, e)
            # Si falla (por ejemplo, si algún campo personalizado no existe en destino), reintentamos con lo básico estándar de Odoo
            basic_vals = {
                'name': partner.name,
                'company_type': company_type,
                'vat': partner.vat or '',
            }
            return models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.partner', 'create', [basic_vals])

    @api.model
    def _create_currency_rate_if_not_exists(self, uid, models_proxy, currency_name, date_str, rate_value):
        """ Busca la tasa en destino y si no existe la crea usando rate e inverse_company_rate """
        if not rate_value or rate_value <= 1.0:
            return

        try:
            # 1. Buscar la moneda en destino
            currency_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.currency', 'search', [[('name', '=', currency_name)]])
            if not currency_ids:
                _logger.warning("Moneda %s no encontrada en destino. No se puede crear tasa.", currency_name)
                return
            currency_id = currency_ids[0]

            # 2. Buscar si ya existe tasa para esa fecha en destino
            rate_domain = [
                ('currency_id', '=', currency_id),
                ('name', '=', date_str)
            ]
            existing_rates = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.currency.rate', 'search', [rate_domain])
            
            if not existing_rates:
                # 3. Crear tasa en destino
                rate_vals = {
                    'currency_id': currency_id,
                    'name': date_str,
                    'rate': 1.0 / rate_value,
                    'inverse_company_rate': rate_value,
                }
                try:
                    rate_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.currency.rate', 'create', [rate_vals])
                    _logger.info("Tasa creada en destino para %s el %s con valor %s (ID %s)", currency_name, date_str, rate_value, rate_id)
                except Exception as ec:
                    _logger.warning("Fallo creación de tasa con inverse_company_rate, reintentando solo con rate. Error: %s", ec)
                    fallback_vals = {
                        'currency_id': currency_id,
                        'name': date_str,
                        'rate': 1.0 / rate_value,
                    }
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'res.currency.rate', 'create', [fallback_vals])
        except Exception as e:
            _logger.error("Error al gestionar la tasa de cambio en destino para %s el %s: %s", currency_name, date_str, e)

    @api.model
    def _find_remote_tax(self, uid, models_proxy, local_tax):
        """ Busca un impuesto equivalente en la base receptora por nombre o por porcentaje """
        # Buscar por nombre exacto y tipo de impuesto (ventas/compras)
        remote_tax_id = self._find_remote_record(uid, models_proxy, 'account.tax', [
            ('name', '=', local_tax.name),
            ('type_tax_use', '=', local_tax.type_tax_use)
        ])
        if not remote_tax_id:
            # Fallback por porcentaje/monto exacto y tipo de impuesto
            remote_tax_id = self._find_remote_record(uid, models_proxy, 'account.tax', [
                ('amount', '=', local_tax.amount),
                ('type_tax_use', '=', local_tax.type_tax_use)
            ])
        return remote_tax_id


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_transfer_via_xmlrpc(self):
        """ Método llamado desde la acción de servidor para enviar facturas. """
        if not self:
            return

        sync_model = self.env['xmlrpc.sync.base']
        messages = []
        try:
            uid, models_proxy = sync_model._get_xmlrpc_connection()
        except Exception as e:
            raise UserError(f"Error de conexión inicial:\n{e}")

        for order in self:
            try:
                # 1. Calcular tasa de cambio
                rate = 1.0
                if 'tax_today' in order._fields and order.tax_today and order.tax_today > 1.0:
                    rate = order.tax_today
                elif 'tax_day' in order._fields and order.tax_day and order.tax_day > 1.0:
                    rate = order.tax_day
                else:
                    # Buscar en las tasas locales de la base de datos emisora
                    date_val = order.date_order or fields.Datetime.now()
                    rate_records = self.env['res.currency.rate'].search([
                        ('currency_id', '=', order.currency_id.id),
                        ('name', '=', date_val.date())
                    ], limit=1)
                    if rate_records:
                        if hasattr(rate_records, 'inverse_company_rate') and rate_records.inverse_company_rate > 1.0:
                            rate = rate_records.inverse_company_rate
                        elif rate_records.rate:
                            rate = 1.0 / rate_records.rate

                # 2. Gestionar tasa en destino
                currency_name = order.currency_id.name or 'USD'
                date_str = order.date_order.strftime('%Y-%m-%d') if order.date_order else fields.Date.today().strftime('%Y-%m-%d')
                sync_model._create_currency_rate_if_not_exists(uid, models_proxy, currency_name, date_str, rate)

                # 3. Partner (Búsqueda secuencial)
                remote_partner_id = False
                if order.partner_id.vat:
                    remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('vat', '=', order.partner_id.vat)])
                if not remote_partner_id and order.partner_id.name:
                    remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('name', '=', order.partner_id.name)])
                
                # Si no se encuentra de ninguna forma, lo creamos
                if not remote_partner_id:
                    try:
                        remote_partner_id = sync_model._create_remote_partner(uid, models_proxy, order.partner_id)
                        msg_p = f"Cliente {order.partner_id.name} no existía. Creado en destino con ID {remote_partner_id}."
                        _logger.info(msg_p)
                        messages.append(msg_p)
                    except Exception as ep:
                        msg_pe = f"SO {order.name}: No se pudo crear el cliente {order.partner_id.name}: {ep}. Omitiendo orden."
                        _logger.error(msg_pe)
                        messages.append(msg_pe)
                        continue

                # 4. Líneas
                order_lines = []
                skip_order = False
                for line in order.order_line:
                    # Líneas de sección/nota
                    if line.display_type in ('line_section', 'line_note'):
                        order_lines.append((0, 0, {
                            'display_type': line.display_type,
                            'name': line.name,
                        }))
                        continue

                    if not line.product_id:
                        continue

                    # Buscar producto (fallbacks secuenciales)
                    remote_product_id = False
                    if line.product_id.default_code:
                        remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('default_code', '=', line.product_id.default_code)])
                    if not remote_product_id and line.product_id.barcode:
                        remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('barcode', '=', line.product_id.barcode)])
                    if not remote_product_id and line.product_id.name:
                        remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('name', '=', line.product_id.name)])

                    if not remote_product_id:
                        msg = f"SO {order.name}: Producto {line.product_id.name} no encontrado en destino. Omitiendo la orden completa."
                        _logger.warning(msg)
                        messages.append(msg)
                        skip_order = True
                        break
                    
                    # Buscar e mapear impuestos de la línea
                    remote_tax_ids = []
                    for tax in line.tax_id:
                        r_tax_id = sync_model._find_remote_tax(uid, models_proxy, tax)
                        if r_tax_id:
                            remote_tax_ids.append(r_tax_id)

                    order_lines.append((0, 0, {
                        'product_id': remote_product_id,
                        'name': line.name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': line.price_unit * rate,
                        'discount': line.discount,
                        'tax_id': [(6, 0, remote_tax_ids)],
                    }))

                if skip_order:
                    continue

                # 5. Cabecera
                vals = {
                    'partner_id': remote_partner_id,
                    'client_order_ref': order.client_order_ref or '',
                    'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else False,
                    'validity_date': order.validity_date.strftime('%Y-%m-%d') if order.validity_date else False,
                    'note': order.note or '',
                    'order_line': order_lines,
                    'tax_today': rate,
                }
                
                # 6. Crear orden
                remote_order_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'create', [vals])
                msg = f"SO {order.name} creada exitosamente en destino con ID {remote_order_id}."
                _logger.info(msg)
                messages.append(msg)
                
                # 7. Confirmar en destino
                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'action_confirm', [[remote_order_id]])
                
                # Escribir la fecha original después de confirmar, ya que action_confirm la sobreescribe por defecto
                if order.date_order:
                    models_proxy.execute_kw(
                        DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'write',
                        [[remote_order_id], {'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S')}]
                    )
                
                msg_conf = f"SO {order.name} confirmada en destino y fecha original restaurada."
                _logger.info(msg_conf)
                messages.append(msg_conf)

                # 8. Validar recepciones/entregas (stock.picking)
                picking_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'search', [[('sale_id', '=', remote_order_id), ('state', 'not in', ['done', 'cancel'])]])
                if picking_ids:
                    for picking_id in picking_ids:
                        try:
                            models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'action_assign', [[picking_id]])
                            
                            # Forzar las cantidades entregadas en las líneas (stock.move) para evitar el error de reserva
                            move_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.move', 'search_read', [[('picking_id', '=', picking_id)]], {'fields': ['id', 'product_uom_qty']})
                            for move_st in move_ids:
                                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.move', 'write', [[move_st['id']], {'quantity_done': move_st['product_uom_qty']}])
                                
                            res = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'button_validate', [[picking_id]])
                            if isinstance(res, dict) and res.get('res_model') == 'stock.immediate.transfer':
                                ctx = res.get('context', {})
                                wiz_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.immediate.transfer', 'create', [{}], {'context': ctx})
                                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.immediate.transfer', 'process', [[wiz_id]], {'context': ctx})
                            msg_pick = f"Entrega del pedido {order.name} validada en destino."
                            _logger.info(msg_pick)
                            messages.append(msg_pick)
                        except Exception as ep:
                            msg_pe = f"No se pudo validar automaticamente la entrega para {order.name}: {ep}"
                            _logger.warning(msg_pe)
                            messages.append(msg_pe)

                # 9. Crear Facturas en destino usando el wizard publico
                ctx = {'active_model': 'sale.order', 'active_ids': [remote_order_id], 'active_id': remote_order_id}
                wiz_vals = {'advance_payment_method': 'delivered'}
                wiz_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.advance.payment.inv', 'create', [wiz_vals], {'context': ctx})
                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.advance.payment.inv', 'create_invoices', [[wiz_id]], {'context': ctx})
                
                # Obtener las facturas generadas leyendo el campo invoice_ids del pedido remoto
                remote_order_data = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'read', [[remote_order_id]], {'fields': ['invoice_ids']})
                remote_invoice_ids = remote_order_data[0].get('invoice_ids', []) if remote_order_data else []
                
                if remote_invoice_ids:
                    msg_inv = f"Factura(s) creada(s) en destino para {order.name}: {remote_invoice_ids}."
                    _logger.info(msg_inv)
                    messages.append(msg_inv)
                    
                    # 1. Asignar tax_today e invoice_date a las facturas generadas
                    inv_vals = {'tax_today': rate}
                    if order.date_order:
                        inv_vals['invoice_date'] = order.date_order.strftime('%Y-%m-%d')
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'write', [remote_invoice_ids, inv_vals])
                    
                    # 2. Confirmar (Publicar) las facturas de una vez
                    try:
                        models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'action_post', [remote_invoice_ids])
                        
                        # Escribir de nuevo invoice_date e invoice_date_due/date por si acaso tras publicar
                        if order.date_order:
                            models_proxy.execute_kw(
                                DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'write',
                                [remote_invoice_ids, {'invoice_date': order.date_order.strftime('%Y-%m-%d'), 'date': order.date_order.strftime('%Y-%m-%d')}]
                            )
                        
                        msg_post = f"Factura(s) confirmada(s)/publicada(s) en destino."
                        _logger.info(msg_post)
                        messages.append(msg_post)
                    except Exception as epost:
                        msg_post = f"Factura(s) no se pudo publicar automáticamente en destino: {epost}"
                        _logger.warning(msg_post)
                        messages.append(msg_post)
                    
            except Exception as e:
                msg = f"Error transfiriendo la SO {order.name}: {e}"
                _logger.error(msg)
                messages.append(msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resultados de Sincronización XML-RPC',
                'message': '\n'.join(messages),
                'sticky': True,
                'type': 'warning' if any("Error" in m for m in messages) else 'success',
            }
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_transfer_via_xmlrpc(self):
        """ Método llamado desde la acción de servidor para enviar facturas. """
        if not self:
            return

        sync_model = self.env['xmlrpc.sync.base']
        messages = []
        try:
            uid, models_proxy = sync_model._get_xmlrpc_connection()
        except Exception as e:
            raise UserError(f"Error de conexión inicial:\n{e}")

        for move in self:
            try:
                # 1. Calcular tasa de cambio
                rate = 1.0
                if 'tax_today' in move._fields and move.tax_today and move.tax_today > 1.0:
                    rate = move.tax_today
                elif 'tax_day' in move._fields and move.tax_day and move.tax_day > 1.0:
                    rate = move.tax_day
                else:
                    # Buscar en las tasas locales de la base de datos emisora
                    date_val = move.invoice_date or move.date or fields.Date.today()
                    rate_records = self.env['res.currency.rate'].search([
                        ('currency_id', '=', move.currency_id.id),
                        ('name', '=', date_val)
                    ], limit=1)
                    if rate_records:
                        if hasattr(rate_records, 'inverse_company_rate') and rate_records.inverse_company_rate > 1.0:
                            rate = rate_records.inverse_company_rate
                        elif rate_records.rate:
                            rate = 1.0 / rate_records.rate

                # 2. Gestionar tasa en destino
                currency_name = move.currency_id.name or 'USD'
                date_str = move.invoice_date.strftime('%Y-%m-%d') if move.invoice_date else (move.date.strftime('%Y-%m-%d') if move.date else fields.Date.today().strftime('%Y-%m-%d'))
                sync_model._create_currency_rate_if_not_exists(uid, models_proxy, currency_name, date_str, rate)

                # 3. Partner (Búsqueda secuencial)
                remote_partner_id = False
                if move.partner_id:
                    if move.partner_id.vat:
                        remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('vat', '=', move.partner_id.vat)])
                    if not remote_partner_id and move.partner_id.name:
                        remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('name', '=', move.partner_id.name)])
                    
                    # Si no se encuentra de ninguna forma, lo creamos
                    if not remote_partner_id:
                        try:
                            remote_partner_id = sync_model._create_remote_partner(uid, models_proxy, move.partner_id)
                            msg_p = f"Cliente {move.partner_id.name} no existía. Creado en destino con ID {remote_partner_id}."
                            _logger.info(msg_p)
                            messages.append(msg_p)
                        except Exception as ep:
                            msg_pe = f"Factura {move.name}: No se pudo crear el cliente {move.partner_id.name}: {ep}. Omitiendo factura."
                            _logger.error(msg_pe)
                            messages.append(msg_pe)
                            continue

                # 4. Líneas
                invoice_lines = []
                skip_move = False
                for line in move.invoice_line_ids:
                    # Secciones/Notas
                    if line.display_type in ('line_section', 'line_note'):
                        invoice_lines.append((0, 0, {
                            'display_type': line.display_type,
                            'name': line.name,
                        }))
                        continue

                    # Buscar producto si la línea tiene uno (fallbacks secuenciales)
                    remote_product_id = False
                    if line.product_id:
                        if line.product_id.default_code:
                            remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('default_code', '=', line.product_id.default_code)])
                        if not remote_product_id and line.product_id.barcode:
                            remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('barcode', '=', line.product_id.barcode)])
                        if not remote_product_id and line.product_id.name:
                            remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('name', '=', line.product_id.name)])

                        if not remote_product_id:
                            msg = f"Factura {move.name}: Producto {line.product_id.name} no encontrado en destino. Omitiendo factura completa."
                            _logger.warning(msg)
                            messages.append(msg)
                            skip_move = True
                            break

                    # Buscar y mapear impuestos de la línea
                    remote_tax_ids = []
                    for tax in line.tax_ids:
                        r_tax_id = sync_model._find_remote_tax(uid, models_proxy, tax)
                        if r_tax_id:
                            remote_tax_ids.append(r_tax_id)

                    line_vals = {
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit * rate,
                        'discount': line.discount,
                        'tax_ids': [(6, 0, remote_tax_ids)],
                    }
                    if remote_product_id:
                        line_vals['product_id'] = remote_product_id
                        
                    invoice_lines.append((0, 0, line_vals))

                if skip_move:
                    continue

                # 5. Cabecera
                vals = {
                    'move_type': move.move_type,
                    'invoice_date': move.invoice_date.strftime('%Y-%m-%d') if move.invoice_date else False,
                    'date': move.date.strftime('%Y-%m-%d') if move.date else False,
                    'ref': move.ref or '',
                    'invoice_line_ids': invoice_lines,
                    'tax_today': rate,
                }
                
                if remote_partner_id:
                    vals['partner_id'] = remote_partner_id
                
                # 6. Crear factura
                remote_move_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'create', [vals])
                msg = f"Factura {move.name} creada exitosamente en destino con ID {remote_move_id}."
                _logger.info(msg)
                messages.append(msg)
                
                # 7. Confirmar/Publicar de una vez
                try:
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'action_post', [[remote_move_id]])
                    
                    # Escribir de nuevo invoice_date e invoice_date_due/date por si acaso tras publicar
                    write_vals = {}
                    if move.invoice_date:
                        write_vals['invoice_date'] = move.invoice_date.strftime('%Y-%m-%d')
                    if move.date:
                        write_vals['date'] = move.date.strftime('%Y-%m-%d')
                    if write_vals:
                        models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'write', [[remote_move_id], write_vals])
                        
                    msg_conf = f"Factura {move.name} confirmada/publicada en destino y fechas originales restauradas."
                    _logger.info(msg_conf)
                    messages.append(msg_conf)
                except Exception as epost:
                    msg_conf = f"Factura {move.name} creada en borrador pero no se pudo publicar automáticamente: {epost}"
                    _logger.warning(msg_conf)
                    messages.append(msg_conf)

            except Exception as e:
                msg = f"Error transfiriendo la factura {move.name}: {e}"
                _logger.error(msg)
                messages.append(msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resultados de Sincronización XML-RPC',
                'message': '\n'.join(messages),
                'sticky': True,
                'type': 'warning' if any("Error" in m for m in messages) else 'success',
            }
        }


class PosSession(models.Model):
    _inherit = 'pos.session'

    x_xmlrpc_synced = fields.Boolean(string="Sincronizado vía XML-RPC", default=False, copy=False)

    @api.model
    def _cron_sync_pos_sessions(self):
        """ Acción planificada para sincronizar automáticamente sesiones POS cerradas. """
        sessions = self.search([('state', '=', 'closed'), ('x_xmlrpc_synced', '=', False)])
        if sessions:
            _logger.info("Cron XML-RPC: Sincronizando %s sesiones de punto de venta.", len(sessions))
            sessions.action_transfer_via_xmlrpc()

    def action_transfer_via_xmlrpc(self):
        """ Método llamado desde la acción de servidor para enviar sesiones POS. """
        if not self:
            return

        sync_model = self.env['xmlrpc.sync.base']
        messages = []
        try:
            uid, models_proxy = sync_model._get_xmlrpc_connection()
        except Exception as e:
            raise UserError(f"Error de conexión inicial:\n{e}")

        # Cachés para evitar cientos de llamadas XML-RPC redundantes
        partner_cache = {}
        product_cache = {}
        tax_cache = {}
        payment_method_cache = {}
        rate_cache = set()

        for session in self:
            remote_session_id = False
            try:
                # 1. Validar si el pos.config existe en destino
                config_name = session.config_id.name
                remote_config_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.config', 'search', [[('name', '=', config_name)]])
                if not remote_config_ids:
                    # Crear el pos.config en destino
                    local_config = session.config_id
                    _logger.info("Creando pos.config '%s' en destino ya que no existe...", config_name)
                    
                    # 1.1 Mapear Journal
                    remote_journal_id = False
                    if local_config.journal_id:
                        remote_journal_id = sync_model._find_remote_record(uid, models_proxy, 'account.journal', [
                            ('code', '=', local_config.journal_id.code)
                        ])
                        if not remote_journal_id:
                            remote_journal_id = sync_model._find_remote_record(uid, models_proxy, 'account.journal', [
                                ('name', '=', local_config.journal_id.name)
                            ])

                    # 1.2 Mapear Invoice Journal
                    remote_invoice_journal_id = False
                    if local_config.invoice_journal_id:
                        remote_invoice_journal_id = sync_model._find_remote_record(uid, models_proxy, 'account.journal', [
                            ('code', '=', local_config.invoice_journal_id.code)
                        ])
                        if not remote_invoice_journal_id:
                            remote_invoice_journal_id = sync_model._find_remote_record(uid, models_proxy, 'account.journal', [
                                ('name', '=', local_config.invoice_journal_id.name)
                            ])

                    # 1.3 Mapear Picking Type
                    remote_picking_type_id = False
                    if local_config.picking_type_id:
                        remote_picking_type_id = sync_model._find_remote_record(uid, models_proxy, 'stock.picking.type', [
                            ('name', '=', local_config.picking_type_id.name)
                        ])
                        if not remote_picking_type_id and hasattr(local_config.picking_type_id, 'sequence_code'):
                            remote_picking_type_id = sync_model._find_remote_record(uid, models_proxy, 'stock.picking.type', [
                                ('sequence_code', '=', local_config.picking_type_id.sequence_code)
                            ])

                    # 1.4 Mapear Currency
                    remote_currency_id = False
                    if local_config.currency_id:
                        remote_currency_id = sync_model._find_remote_record(uid, models_proxy, 'res.currency', [
                            ('name', '=', local_config.currency_id.name)
                        ])

                    # 1.5 Mapear Métodos de Pago
                    remote_payment_method_ids = []
                    for pm in local_config.payment_method_ids:
                        r_pm = sync_model._find_remote_record(uid, models_proxy, 'pos.payment.method', [
                            ('name', '=', pm.name)
                        ])
                        if not r_pm:
                            # Intentamos crear el método de pago remoto
                            pm_vals = {
                                'name': pm.name,
                                'split_transactions': pm.split_transactions or False,
                            }
                            # Mapear cuenta cobrable
                            if pm.receivable_account_id:
                                r_rec_acc = sync_model._find_remote_record(uid, models_proxy, 'account.account', [
                                    ('code', '=', pm.receivable_account_id.code)
                                ])
                                if r_rec_acc:
                                    pm_vals['receivable_account_id'] = r_rec_acc
                            
                            # Mapear diario si es efectivo
                            if pm.is_cash_count and pm.journal_id:
                                r_pm_journal = sync_model._find_remote_record(uid, models_proxy, 'account.journal', [
                                    ('code', '=', pm.journal_id.code)
                                ])
                                if r_pm_journal:
                                    pm_vals['journal_id'] = r_pm_journal
                                    pm_vals['is_cash_count'] = True

                            try:
                                r_pm = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.payment.method', 'create', [pm_vals])
                                _logger.info("Método de pago %s creado en destino con ID %s", pm.name, r_pm)
                            except Exception as e_pm:
                                _logger.error("No se pudo crear el método de pago %s en destino: %s", pm.name, e_pm)
                        
                        if r_pm:
                            remote_payment_method_ids.append(r_pm)

                    # Crear el pos.config en destino
                    config_vals = {
                        'name': local_config.name,
                    }
                    if remote_journal_id:
                        config_vals['journal_id'] = remote_journal_id
                    if remote_invoice_journal_id:
                        config_vals['invoice_journal_id'] = remote_invoice_journal_id
                    if remote_picking_type_id:
                        config_vals['picking_type_id'] = remote_picking_type_id
                    if remote_currency_id:
                        config_vals['currency_id'] = remote_currency_id
                    if remote_payment_method_ids:
                        config_vals['payment_method_ids'] = [(6, 0, remote_payment_method_ids)]

                    try:
                        remote_config_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.config', 'create', [config_vals])
                        msg_create = f"Punto de venta '{config_name}' creado en el destino con ID {remote_config_id}."
                        _logger.info(msg_create)
                        messages.append(msg_create)
                    except Exception as e_cfg:
                        msg = f"Sesión {session.name}: No se pudo crear el punto de venta '{config_name}' en destino: {e_cfg}. Omitiendo."
                        _logger.error(msg)
                        messages.append(msg)
                        continue
                else:
                    remote_config_id = remote_config_ids[0]

                # 2. Crear la sesión remota en estado abierto
                session_vals = {
                    'config_id': remote_config_id,
                    'user_id': uid, # asignamos al usuario que autentica
                }
                
                # Odoo asume estado 'new_session' o 'opening_control' al crear. Intentamos abrirla si es necesario
                remote_session_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.session', 'create', [session_vals])
                try:
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.session', 'action_pos_session_open', [[remote_session_id]])
                except Exception as e_open:
                    _logger.info("La sesión %s pudo abrirse sola o falló action_pos_session_open: %s", session.name, e_open)
                
                msg_sess = f"Sesión {session.name} creada en destino con ID {remote_session_id} (Config: {config_name})."
                _logger.info(msg_sess)
                messages.append(msg_sess)

                # 3. Iterar sobre las órdenes (pedidos) de la sesión
                for order in session.order_ids:
                    # 3.1 Calcular tasa de cambio
                    rate = 1.0
                    # Buscar en x_studio_tasa_del_dia dentro de los pagos
                    tasa_pago = next((p.x_studio_tasa_del_dia for p in order.payment_ids if 'x_studio_tasa_del_dia' in p._fields and p.x_studio_tasa_del_dia > 1.0), 1.0)
                    if tasa_pago > 1.0:
                        rate = tasa_pago
                    elif 'rate_order' in order._fields and order.rate_order and order.rate_order > 1.0:
                        rate = order.rate_order
                    elif 'x_studio_related_field_ItNgY' in order._fields and order.x_studio_related_field_ItNgY and order.x_studio_related_field_ItNgY > 1.0:
                        rate = order.x_studio_related_field_ItNgY
                    else:
                        date_val = order.date_order or session.start_at or fields.Datetime.now()
                        rate_records = self.env['res.currency.rate'].search([
                            ('currency_id', '=', order.currency_id.id),
                            ('name', '=', date_val.date())
                        ], limit=1)
                        if rate_records:
                            if hasattr(rate_records, 'inverse_company_rate') and rate_records.inverse_company_rate > 1.0:
                                rate = rate_records.inverse_company_rate
                            elif rate_records.rate:
                                rate = 1.0 / rate_records.rate

                    # Gestionar tasa en destino
                    currency_name = order.currency_id.name or 'USD'
                    date_str = order.date_order.strftime('%Y-%m-%d') if order.date_order else (session.start_at.strftime('%Y-%m-%d') if session.start_at else fields.Date.today().strftime('%Y-%m-%d'))
                    rate_key = (currency_name, date_str)
                    if rate_key not in rate_cache:
                        sync_model._create_currency_rate_if_not_exists(uid, models_proxy, currency_name, date_str, rate)
                        rate_cache.add(rate_key)

                    # 3.2 Buscar/Crear Partner (Uso de caché)
                    remote_partner_id = False
                    if order.partner_id:
                        partner_id_local = order.partner_id.id
                        if partner_id_local in partner_cache:
                            remote_partner_id = partner_cache[partner_id_local]
                        else:
                            if order.partner_id.vat:
                                remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('vat', '=', order.partner_id.vat)])
                            if not remote_partner_id and order.partner_id.name:
                                remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('name', '=', order.partner_id.name)])
                            
                            if not remote_partner_id:
                                try:
                                    remote_partner_id = sync_model._create_remote_partner(uid, models_proxy, order.partner_id)
                                    msg_p = f"Cliente {order.partner_id.name} no existía. Creado en destino con ID {remote_partner_id}."
                                    _logger.info(msg_p)
                                    messages.append(msg_p)
                                except Exception as ep:
                                    msg_pe = f"Sesión {session.name} - Pedido {order.name}: No se pudo crear el cliente {order.partner_id.name}: {ep}. Omitiendo pedido."
                                    _logger.error(msg_pe)
                                    messages.append(msg_pe)
                                    continue
                            partner_cache[partner_id_local] = remote_partner_id

                    # 3.3 Procesar Líneas del Pedido (Uso de caché)
                    order_lines = []
                    skip_order = False
                    for line in order.lines:
                        if not line.product_id:
                            continue

                        remote_product_id = False
                        prod_id_local = line.product_id.id
                        if prod_id_local in product_cache:
                            remote_product_id = product_cache[prod_id_local]
                        else:
                            if line.product_id.default_code:
                                remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('default_code', '=', line.product_id.default_code)])
                            if not remote_product_id and line.product_id.barcode:
                                remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('barcode', '=', line.product_id.barcode)])
                            if not remote_product_id and line.product_id.name:
                                remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', [('name', '=', line.product_id.name)])
                            
                            if remote_product_id:
                                product_cache[prod_id_local] = remote_product_id

                        if not remote_product_id:
                            msg_pl = f"Sesión {session.name} - Pedido {order.name}: Producto {line.product_id.name} no encontrado en destino. Omitiendo pedido."
                            _logger.warning(msg_pl)
                            messages.append(msg_pl)
                            skip_order = True
                            break

                        remote_tax_ids = []
                        for tax in line.tax_ids:
                            tax_id_local = tax.id
                            r_tax_id = False
                            if tax_id_local in tax_cache:
                                r_tax_id = tax_cache[tax_id_local]
                            else:
                                r_tax_id = sync_model._find_remote_tax(uid, models_proxy, tax)
                                if r_tax_id:
                                    tax_cache[tax_id_local] = r_tax_id
                            
                            if r_tax_id:
                                remote_tax_ids.append(r_tax_id)
                                
                        order_lines.append((0, 0, {
                            'product_id': remote_product_id,
                            'full_product_name': line.full_product_name or line.product_id.name,
                            'qty': line.qty,
                            'price_unit': line.price_unit * rate,  # Ajustado por tasa
                            'price_subtotal': line.price_subtotal,
                            'price_subtotal_incl': line.price_subtotal_incl,
                            'discount': line.discount,
                            'tax_ids': [(6, 0, remote_tax_ids)],
                        }))

                    if skip_order:
                        continue

                    # 3.4 Crear el Pedido en destino
                    order_vals = {
                        'session_id': remote_session_id,
                        'name': order.name,
                        'pos_reference': order.pos_reference or order.name,
                        'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else False,
                        'amount_tax': order.amount_tax,
                        'amount_total': order.amount_total,
                        'amount_paid': order.amount_paid,
                        'amount_return': order.amount_return,
                        'lines': order_lines,
                        'company_id': session.company_id.id,
                    }
                    if remote_partner_id:
                        order_vals['partner_id'] = remote_partner_id
                    
                    remote_order_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.order', 'create', [order_vals])

                    # 3.5 Crear Pagos (pos.payment) (Uso de caché)
                    for payment in order.payment_ids:
                        remote_payment_method_id = False
                        pm_id_local = payment.payment_method_id.id
                        if pm_id_local in payment_method_cache:
                            remote_payment_method_id = payment_method_cache[pm_id_local]
                        else:
                            if payment.payment_method_id.name:
                                r_pm = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.payment.method', 'search', [[('name', '=', payment.payment_method_id.name)]])
                                if r_pm:
                                    remote_payment_method_id = r_pm[0]
                            
                            if not remote_payment_method_id:
                                r_pm_fallback = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.payment.method', 'search', [], {'limit': 1})
                                remote_payment_method_id = r_pm_fallback[0] if r_pm_fallback else False
                            
                            if remote_payment_method_id:
                                payment_method_cache[pm_id_local] = remote_payment_method_id

                        if remote_payment_method_id:
                            payment_vals = {
                                'pos_order_id': remote_order_id,
                                'amount': payment.amount,
                                'payment_method_id': remote_payment_method_id,
                                'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else False,
                                'session_id': remote_session_id,
                            }
                            models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.payment', 'create', [payment_vals])

                    # 3.6 Marcar pedido como pagado
                    try:
                        models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.order', 'action_pos_order_paid', [[remote_order_id]])
                    except Exception as eo:
                        _logger.warning("Fallo post-procesamiento de pedido %s: %s", order.name, eo)

                # 3.7 Validar entregas (stock.picking) de la sesión de manera agrupada
                try:
                    picking_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'search', [[('pos_session_id', '=', remote_session_id), ('state', 'not in', ['done', 'cancel'])]])
                    if picking_ids:
                        _logger.info("Validando %s albaranes para la sesión remota %s", len(picking_ids), remote_session_id)
                        for picking_id in picking_ids:
                            models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'action_assign', [[picking_id]])
                            move_ids = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.move', 'search_read', [[('picking_id', '=', picking_id)]], {'fields': ['id', 'product_uom_qty']})
                            for move_st in move_ids:
                                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.move', 'write', [[move_st['id']], {'quantity_done': move_st['product_uom_qty']}])
                            
                            res_pick = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.picking', 'button_validate', [[picking_id]])
                            if isinstance(res_pick, dict) and res_pick.get('res_model') == 'stock.immediate.transfer':
                                ctx = res_pick.get('context', {})
                                wiz_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.immediate.transfer', 'create', [{}], {'context': ctx})
                                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'stock.immediate.transfer', 'process', [[wiz_id]], {'context': ctx})
                except Exception as ep:
                    _logger.warning("Fallo al validar albaranes de la sesión %s: %s", session.name, ep)

                # Marcar como sincronizado localmente tras el traspaso exitoso de pedidos y pagos
                session.write({'x_xmlrpc_synced': True})

                # 4. Cerrar la sesión
                try:
                    # En v16, las sesiones se cierran llamando a action_pos_session_closing_control
                    res_close = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.session', 'action_pos_session_closing_control', [[remote_session_id]])
                    msg_close = f"Sesión {session.name} (Destino ID {remote_session_id}) cerrada exitosamente y asiento contable generado."
                    _logger.info(msg_close)
                    messages.append(msg_close)
                except Exception as ec:
                    msg_close_err = f"Sesión {session.name} transferida, pero falló el cierre automático (Asiento): {ec}"
                    _logger.error(msg_close_err)
                    messages.append(msg_close_err)

            except Exception as e:
                msg = f"Error transfiriendo la Sesión {session.name}: {e}"
                _logger.error(msg)
                messages.append(msg)
                if remote_session_id:
                    try:
                        # Comprobar el estado de la sesión remota antes de intentar cerrarla
                        remote_session = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.session', 'read', [[remote_session_id]], {'fields': ['state']})
                        if remote_session and remote_session[0].get('state') not in ('closed', 'closing_control'):
                            _logger.info("Forzando el cierre de la sesión remota %s tras falla de proceso para evitar inconsistencias...", remote_session_id)
                            models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'pos.session', 'action_pos_session_closing_control', [[remote_session_id]])
                            messages.append(f"Sesión remota {session.name} (ID {remote_session_id}) fue cerrada de forma forzada tras un error del proceso para evitar inconsistencias.")
                    except Exception as e_close:
                        _logger.error("No se pudo cerrar forzadamente la sesión remota %s: %s", remote_session_id, e_close)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resultados de Sincronización de Sesiones POS',
                'message': '\n'.join(messages),
                'sticky': True,
                'type': 'warning' if any("Error" in m for m in messages) else 'success',
            }
        }

