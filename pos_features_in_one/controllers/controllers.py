# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import werkzeug
from odoo.addons.web.controllers.main import home


class PosScreen(home.Home):
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        """Override to add direct login to POS"""
        res = super().web_login(redirect=redirect, **kw)
        if request.env.user.pos_conf_id:
            if not request.env.user.pos_conf_id.current_session_id:
                request.env['pos.session'].sudo().create({
                    'user_id': request.env.uid,
                    'config_id': request.env.user.pos_conf_id.id
                })
            return werkzeug.utils.redirect('/pos/ui')
        return res
