# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('price_unit')
    def onchange_custom_price(self):
        if self.product_id and not 'pricelist' in self.env.context and not self.env.user.has_group("sotto_restrict_price_change.group_allow_price_change"):
            raise UserError(_('You are not allowed to change price'))
