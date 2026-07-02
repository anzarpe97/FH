# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for rec in self:
            if not rec.env.user.has_group("so_confirm_unlock_group.group_allow_confirm_unlock_so"):
                raise AccessError(_("You are not allowed to confirm orders, please contact your system administrator."))
        return super(SaleOrder, self).action_confirm()
