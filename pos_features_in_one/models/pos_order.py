from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    pos_allow_salesperson = fields.Boolean(related='session_id.config_id.pos_allow_salesperson')
    order_note = fields.Char(string="Nota de la Orden")

    # Campo relacionado con el primer Salesperson de la primera línea
    first_salesperson = fields.Many2one(
        'hr.employee',
        string='Vendedor',
        compute='_compute_first_salesperson',
        store=True
    )

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res['order_note'] = ui_order.get('order_note', False)
        return res

    @api.depends('lines')
    def _compute_first_salesperson(self):
        for order in self:
            if order.lines:
                order.first_salesperson = order.lines[0].salesperson_id
            else:
                order.first_salesperson = False


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    salesperson_id = fields.Many2one('hr.employee', string='Vendedor',
                                     help='Vendedor seleccionado en la línea de la orden')
