# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortalIn(CustomerPortal):

    @http.route(['/my/orders/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None):
        if not request.env.user.has_group("so_confirm_unlock_group.group_allow_confirm_unlock_so") and request.env.user.has_group('base.group_user'):
            raise AccessError(_("You are not allowed to confirm orders, please contact your system administrator."))
        return super(CustomerPortalIn, self).portal_quote_accept(order_id, access_token, name, signature)
