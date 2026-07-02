# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools
from collections import defaultdict
from odoo.tools import float_is_zero
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError



class PosSession(models.Model):
    _inherit = 'pos.session'

    igtf_move_ids = fields.Many2many("account.move",string="IGTF Moves")

    def _loader_params_res_company(self):
        result = super(PosSession, self)._loader_params_res_company()
        result['search_params']['fields'].extend(['is_igtf','igtf_percentage'])
        return result

    def _loader_params_pos_payment_method(self):
        result = super(PosSession, self)._loader_params_pos_payment_method()
        result['search_params']['fields'].extend(['is_igtf'])
        return result

    def _accumulate_amounts(self, data):
        result = super(PosSession, self)._accumulate_amounts(data)
        for order in self.order_ids:
            if not order.is_invoiced:
                if order.igtf_amount > 0:
                    income_acnt = order.company_id.receivable_account_id
                    if not income_acnt:
                      raise UserError(_('Please define income account for IGTF under company '))
                    sale_key1 = (
                      # account
                      income_acnt.id,
                      # sign
                      1,
                      # for taxes
                      tuple(),
                      tuple(),
                    )   
                    result['sales'][sale_key1] = self._update_amounts(result['sales'][sale_key1], {'amount': order.igtf_amount}, order.date_order)
                    result['sales'][sale_key1].setdefault('tax_amount', 0.0)
        return result

    def _prepare_balancing_line_vals(self, imbalance_amount, move, balancing_account):
        account = self._get_balancing_account()
        account = self.company_id.payable_account_id
        if not account:
            raise UserError(_(
                "Please Configure Account Details First in Company Go TO Company ==> Select Account 'Cuenta Pagos IGTF' ."))
        partial_vals = {
            'name': _('Difference at closing PoS session'),
            'account_id': account.id,
            'move_id': move.id,
            'partner_id': False,
        }
        # `imbalance_amount` is already in terms of company currency so it is the amount_converted
        # param when calling `_credit_amounts`. amount param will be the converted value of
        # `imbalance_amount` from company currency to the session currency.
        imbalance_amount_session = 0
        if (not self.is_in_company_currency):
            imbalance_amount_session = self.company_id.currency_id._convert(imbalance_amount, self.currency_id, self.company_id, fields.Date.context_today(self))
        return self._credit_amounts(partial_vals, imbalance_amount_session, imbalance_amount)
