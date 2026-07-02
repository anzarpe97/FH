from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    replace_standard_wizard = fields.Boolean(
        string='Print with the alternative wizard',
        config_parameter='garazd_product_label.replace_standard_wizard',
    )
