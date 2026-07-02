# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_view_image_combo = fields.Boolean(string='View Combo Product Image', default=True,
        help="Manage view product image in combo popup.")
