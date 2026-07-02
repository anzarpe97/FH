from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.tools import float_is_zero


class POSPM(models.Model):
    _inherit = 'pos.payment.method'

    # Agrega el campo currency_id
    currency_id = fields.Many2one(related="journal_id.currency_id", string="Currency")

class POSSession(models.Model):
    _inherit = 'pos.session'

    # Agrega los campos personalizados correspondientes a la vista XML
    street = fields.Char(string="Street")
    city = fields.Char(string="City")
    zip = fields.Char(string="ZIP")
    state_id = fields.Many2one('res.country.state', string="State")
    country_id = fields.Many2one('res.country', string="Country")
    lang = fields.Char(string="Language")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    barcode = fields.Char(string="Barcode")
    vat = fields.Char(string="Tax ID")
    property_product_pricelist = fields.Many2one('product.pricelist', string="Pricelist")

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].extend(['currency_id'])
        return result

    def load_pos_data(self):
        loaded_data = super(POSSession, self).load_pos_data()

        allcurrency = self.env['res.currency'].search_read(
            domain=[('id', '=', self.env.company.currency_id.id)],
            fields=['name', 'symbol', 'position'],
        )
        loaded_data['allcurrency'] = allcurrency
        return loaded_data