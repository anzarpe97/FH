from odoo import models, fields

class Product(models.Model):
    _inherit = 'product.product'

    total_price = fields.Float(compute='_compute_total_price', string='Total Price')

    def _compute_total_price(self):
        for record in self:
            record.total_price = record.price_unit * (1 + record.taxes_id.amount)