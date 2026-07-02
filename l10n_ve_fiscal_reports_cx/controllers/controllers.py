# -*- coding: utf-8 -*-
# from odoo import http


# class L10nVeFiscalReportsCx(http.Controller):
#     @http.route('/l10n_ve_fiscal_reports_cx/l10n_ve_fiscal_reports_cx/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_ve_fiscal_reports_cx/l10n_ve_fiscal_reports_cx/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_ve_fiscal_reports_cx.listing', {
#             'root': '/l10n_ve_fiscal_reports_cx/l10n_ve_fiscal_reports_cx',
#             'objects': http.request.env['l10n_ve_fiscal_reports_cx.l10n_ve_fiscal_reports_cx'].search([]),
#         })

#     @http.route('/l10n_ve_fiscal_reports_cx/l10n_ve_fiscal_reports_cx/objects/<model("l10n_ve_fiscal_reports_cx.l10n_ve_fiscal_reports_cx"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_ve_fiscal_reports_cx.object', {
#             'object': obj
#         })
