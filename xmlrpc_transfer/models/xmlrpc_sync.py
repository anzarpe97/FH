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
        uid, models_proxy = sync_model._get_xmlrpc_connection()

        for order in self:
            try:
                # 1. Partner
                partner_domain = []
                if order.partner_id.vat:
                    partner_domain = [('vat', '=', order.partner_id.vat)]
                elif order.partner_id.name:
                    partner_domain = [('name', '=', order.partner_id.name)]
                
                remote_partner_id = False
                if partner_domain:
                    remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', partner_domain)
                
                if not remote_partner_id:
                    _logger.warning("SO %s: Cliente %s no encontrado en destino (vat: %s). Omitiendo.", order.name, order.partner_id.name, order.partner_id.vat)
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

                    # Buscar producto (fallbacks a name)
                    product_domain = []
                    if line.product_id.default_code:
                        product_domain = [('default_code', '=', line.product_id.default_code)]
                    elif line.product_id.barcode:
                        product_domain = [('barcode', '=', line.product_id.barcode)]
                    elif line.product_id.name:
                        product_domain = [('name', '=', line.product_id.name)]

                    remote_product_id = False
                    if product_domain:
                        remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', product_domain)

                    if not remote_product_id:
                        _logger.warning("SO %s: Producto %s no encontrado en destino. Omitiendo la orden completa.", order.name, line.product_id.name)
                        skip_order = True
                        break
                    
                    order_lines.append((0, 0, {
                        'product_id': remote_product_id,
                        'name': line.name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': line.price_unit,
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
                _logger.info("SO %s creada exitosamente en destino con ID %s.", order.name, remote_order_id)
                
                # 5. Confirmar (opcional, si en origen está confirmada)
                if order.state in ('sale', 'done'):
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'sale.order', 'action_confirm', [[remote_order_id]])
                    _logger.info("SO %s confirmada en destino.", order.name)

            except Exception as e:
                _logger.error("Error transfiriendo la SO %s: %s", order.name, e)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_transfer_via_xmlrpc(self):
        """ Método llamado desde la acción de servidor para enviar facturas. """
        if not self:
            return

        sync_model = self.env['xmlrpc.sync.base']
        uid, models_proxy = sync_model._get_xmlrpc_connection()

        for move in self:
            try:
                # 1. Partner
                remote_partner_id = False
                if move.partner_id:
                    partner_domain = []
                    if move.partner_id.vat:
                        partner_domain = [('vat', '=', move.partner_id.vat)]
                    elif move.partner_id.name:
                        partner_domain = [('name', '=', move.partner_id.name)]
                    
                    if partner_domain:
                        remote_partner_id = sync_model._find_remote_record(uid, models_proxy, 'res.partner', partner_domain)
                    
                    if not remote_partner_id:
                        _logger.warning("Factura %s: Cliente %s no encontrado en destino (vat: %s). Omitiendo.", move.name, move.partner_id.name, move.partner_id.vat)
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

                    # Buscar producto si la línea tiene uno
                    remote_product_id = False
                    if line.product_id:
                        product_domain = []
                        if line.product_id.default_code:
                            product_domain = [('default_code', '=', line.product_id.default_code)]
                        elif line.product_id.barcode:
                            product_domain = [('barcode', '=', line.product_id.barcode)]
                        elif line.product_id.name:
                            product_domain = [('name', '=', line.product_id.name)]

                        if product_domain:
                            remote_product_id = sync_model._find_remote_record(uid, models_proxy, 'product.product', product_domain)

                        if not remote_product_id:
                            _logger.warning("Factura %s: Producto %s no encontrado en destino. Omitiendo factura completa.", move.name, line.product_id.name)
                            skip_move = True
                            break

                    line_vals = {
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
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
                _logger.info("Factura %s creada exitosamente en destino con ID %s.", move.name, remote_move_id)
                
                # 5. Confirmar (opcional)
                if move.state == 'posted':
                    models_proxy.execute_kw(DB_RECEPTORA, uid, PASS_RECEPTORA, 'account.move', 'action_post', [[remote_move_id]])
                    _logger.info("Factura %s publicada en destino.", move.name)

            except Exception as e:
                _logger.error("Error transfiriendo la factura %s: %s", move.name, e)
