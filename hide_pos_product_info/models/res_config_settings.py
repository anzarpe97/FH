# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_hide_product_info = fields.Boolean(related='pos_config_id.hide_product_info', readonly=False)