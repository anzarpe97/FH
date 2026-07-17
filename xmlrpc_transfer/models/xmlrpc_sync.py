import xmlrpc.client
import logging
from odoo import models, api
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
                # Calcular tasa de cambio
                rate = 1.0
                if order.amount_total:
                    rate = order.amount_total_bs / order.amount_total

                # 1. Partner
                remote_partner_id = False
                if order.partner_id.vat:
                    remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('vat', '=', order.partner_id.vat)])
                if not remote_partner_id and order.partner_id.name:
                    remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('name', '=', order.partner_id.name)])
                
                if not remote_partner_id:
                    msg = f"SO {order.name}: Cliente {order.partner_id.name} no encontrado en destino (vat: {order.partner_id.vat}). Omitiendo."
                    _logger.warning(msg)
                    messages.append(msg)
                    continue

                # 2. Líneas
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
                    
                    order_lines.append((0, 0, {
                        'product_id': remote_product_id,
                        'name': line.name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': line.price_unit * rate,
                        'discount': line.discount,
                    }))

                if skip_order:
                    continue

                # 3. Cabecera
                vals = {
                    'partner_id': remote_partner_id,
                    'client_order_ref': order.client_order_ref or '',
                    'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else False,
                    'validity_date': order.validity_date.strftime('%Y-%m-%d') if order.validity_date else False,
                    'note': order.note or '',
                    'order_line': order_lines,
                }
                
                # 4. Crear orden
                remote_order_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'create', [vals])
                msg = f"SO {order.name} creada exitosamente en destino con ID {remote_order_id}."
                _logger.info(msg)
                messages.append(msg)
                
                # 5. Confirmar en destino
                models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'action_confirm', [[remote_order_id]])
                msg_conf = f"SO {order.name} confirmada en destino."
                _logger.info(msg_conf)
                messages.append(msg_conf)

                # 6. Crear Facturas en destino
                remote_invoice_ids = models_proxy.execute_kw(
                    DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', '_create_invoices', [[remote_order_id]]
                )
                if remote_invoice_ids:
                    msg_inv = f"Factura(s) creada(s) en destino para {order.name}: {remote_invoice_ids}."
                    _logger.info(msg_inv)
                    messages.append(msg_inv)
                    
                    # Opcional: Publicar las facturas creadas
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'action_post', [remote_invoice_ids])
                    msg_post = f"Factura(s) publicada(s) en destino."
                    _logger.info(msg_post)
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
                # Calcular tasa de cambio
                rate = 1.0
                if move.amount_total:
                    rate = move.amount_total_bs / move.amount_total

                # 1. Partner
                remote_partner_id = False
                if move.partner_id:
                    if move.partner_id.vat:
                        remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('vat', '=', move.partner_id.vat)])
                    if not remote_partner_id and move.partner_id.name:
                        remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', [('name', '=', move.partner_id.name)])
                    
                    if not remote_partner_id:
                        msg = f"Factura {move.name}: Cliente {move.partner_id.name} no encontrado en destino (vat: {move.partner_id.vat}). Omitiendo."
                        _logger.warning(msg)
                        messages.append(msg)
                        continue

                # 2. Líneas
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

                    line_vals = {
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit * rate,
                        'discount': line.discount,
                    }
                    if remote_product_id:
                        line_vals['product_id'] = remote_product_id
                        
                    invoice_lines.append((0, 0, line_vals))

                if skip_move:
                    continue

                # 3. Cabecera
                vals = {
                    'move_type': move.move_type,
                    'invoice_date': move.invoice_date.strftime('%Y-%m-%d') if move.invoice_date else False,
                    'date': move.date.strftime('%Y-%m-%d') if move.date else False,
                    'ref': move.ref or '',
                    'invoice_line_ids': invoice_lines,
                }
                
                if remote_partner_id:
                    vals['partner_id'] = remote_partner_id
                
                # 4. Crear factura
                remote_move_id = models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'create', [vals])
                msg = f"Factura {move.name} creada exitosamente en destino con ID {remote_move_id}."
                _logger.info(msg)
                messages.append(msg)
                
                # 5. Confirmar (opcional)
                if move.state == 'posted':
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'action_post', [[remote_move_id]])
                    msg_conf = f"Factura {move.name} publicada en destino."
                    _logger.info(msg_conf)
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
