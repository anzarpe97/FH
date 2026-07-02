# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_iface_view_image_combo = fields.Boolean(string='View Combo Product Image',
                                                compute='_compute_pos_set_image_combo', store=True, readonly=False
                                                , help="Manage view product image in combo popup.")

    @api.depends('pos_config_id')
    def _compute_pos_set_image_combo(self):
        for res_config in self:
            res_config.pos_iface_view_image_combo = res_config.pos_config_id.iface_view_image_combo
