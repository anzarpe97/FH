from odoo import models, fields, api


class PoSConfig(models.Model):
    _inherit = 'pos.config'

    customer_required = fields.Boolean(string="Customer Required?")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_required = fields.Boolean(string="Customer Required?",
                                    config_parameter='ob_pos_customer_required.customer_required')

    @api.onchange('customer_required', 'pos_config_id')
    def _onchange_customer_required(self):
        self.pos_config_id.write({
            'customer_required': self.customer_required
        })


