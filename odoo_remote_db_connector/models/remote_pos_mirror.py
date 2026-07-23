from odoo import fields, models


class OdooRemotePosSession(models.Model):
    _name = "odoo.remote.pos.session"
    _description = "Remote POS Session Mirror"
    _order = "id desc"

    name = fields.Char(string="Sesión", required=True)
    source_database = fields.Char(string="Base Origen", required=True, index=True)
    source_session_id = fields.Integer(string="ID Sesión Origen", required=True, index=True)
    state = fields.Char(string="Estado")
    config_name = fields.Char(string="Punto de Venta")
    user_name = fields.Char(string="Usuario")
    start_at = fields.Datetime(string="Inicio")
    stop_at = fields.Datetime(string="Cierre")
    total_orders = fields.Integer(string="Total Pedidos")
    total_amount = fields.Float(string="Monto Total")
    order_ids = fields.One2many("odoo.remote.pos.order", "remote_session_id", string="Pedidos")


class OdooRemotePosOrder(models.Model):
    _name = "odoo.remote.pos.order"
    _description = "Remote POS Order Mirror"
    _order = "id desc"

    remote_session_id = fields.Many2one("odoo.remote.pos.session", string="Sesión Remota", ondelete="cascade", required=True)
    source_database = fields.Char(string="Base Origen", required=True, index=True)
    source_order_id = fields.Integer(string="ID Pedido Origen", required=True, index=True)
    name = fields.Char(string="Pedido")
    pos_reference = fields.Char(string="Referencia")
    date_order = fields.Datetime(string="Fecha Pedido")
    state = fields.Char(string="Estado")
    partner_name = fields.Char(string="Cliente")
    user_name = fields.Char(string="Vendedor")
    lines_count = fields.Integer(string="Líneas")
    amount_total = fields.Float(string="Total")
    line_ids = fields.One2many("odoo.remote.pos.order.line", "remote_order_id", string="Líneas")
    payment_ids = fields.One2many("odoo.remote.pos.payment", "remote_order_id", string="Pagos")
    stock_move_ids = fields.One2many("odoo.remote.stock.move", "remote_order_id", string="Recogidas")


class OdooRemotePosOrderLine(models.Model):
    _name = "odoo.remote.pos.order.line"
    _description = "Remote POS Order Line Mirror"
    _order = "id desc"

    remote_order_id = fields.Many2one("odoo.remote.pos.order", string="Pedido Remoto", ondelete="cascade", required=True)
    source_database = fields.Char(string="Base Origen", required=True, index=True)
    source_order_line_id = fields.Integer(string="ID Línea Pedido Origen", required=True, index=True)
    order_name = fields.Char(string="Pedido")
    product_name = fields.Char(string="Producto")
    product_default_code = fields.Char(string="Referencia Interna", index=True)
    qty = fields.Float(string="Cantidad")
    price_unit = fields.Float(string="Precio Unitario")
    discount = fields.Float(string="Descuento")
    price_subtotal = fields.Float(string="Subtotal")
    price_subtotal_incl = fields.Float(string="Subtotal con Impuestos")


class OdooRemotePosPayment(models.Model):
    _name = "odoo.remote.pos.payment"
    _description = "Remote POS Payment Mirror"
    _order = "id desc"

    remote_session_id = fields.Many2one("odoo.remote.pos.session", string="Sesión Remota", ondelete="cascade", required=True)
    remote_order_id = fields.Many2one("odoo.remote.pos.order", string="Pedido Remoto", ondelete="cascade")
    source_database = fields.Char(string="Base Origen", required=True, index=True)
    source_payment_id = fields.Integer(string="ID Pago Origen", required=True, index=True)
    session_name = fields.Char(string="Sesión")
    order_name = fields.Char(string="Pedido")
    payment_method_name = fields.Char(string="Método de Pago")
    amount = fields.Float(string="Monto")
    payment_date = fields.Datetime(string="Fecha de Pago")


class OdooRemoteStockMove(models.Model):
    _name = "odoo.remote.stock.move"
    _description = "Remote Stock Move Mirror"
    _order = "id desc"

    remote_session_id = fields.Many2one("odoo.remote.pos.session", string="Sesión Remota", ondelete="cascade", required=True)
    remote_order_id = fields.Many2one("odoo.remote.pos.order", string="Pedido Remoto", ondelete="cascade")
    source_database = fields.Char(string="Base Origen", required=True, index=True)
    source_stock_move_id = fields.Integer(string="ID Movimiento Origen", required=True, index=True)
    session_name = fields.Char(string="Sesión")
    order_name = fields.Char(string="Pedido")
    picking_name = fields.Char(string="Recogida")
    name = fields.Char(string="Movimiento")
    reference = fields.Char(string="Referencia")
    product_name = fields.Char(string="Producto")
    product_default_code = fields.Char(string="Referencia Interna", index=True)
    product_uom_qty = fields.Float(string="Demanda")
    quantity_done = fields.Float(string="Hecho")
    state = fields.Char(string="Estado")
    date = fields.Datetime(string="Fecha")
    location_name = fields.Char(string="Ubicación Origen")
    location_dest_name = fields.Char(string="Ubicación Destino")
