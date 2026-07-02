from odoo import tools
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ResCompany(models.Model):
	_inherit = 'res.company'

	is_igtf = fields.Boolean(string='Retencion de IGTF Divisa')
	igtf_percentage = fields.Float(string='% IGTF Divisa')
	receivable_account_id = fields.Many2one('account.account', string='Cuenta Recibos IGTF', 
		domain=[('reconcile', '=', True), ('account_type', '=', 'asset_receivable')], ondelete='restrict')
	payable_account_id = fields.Many2one('account.account', string='Cuenta Pagos IGTF', 
		domain=[('reconcile', '=', True), ('account_type', '=', 'liability_payable')], ondelete='restrict')
	


class AccountPaymentRegister(models.TransientModel):
	_inherit = 'account.payment.register'

	@api.depends('amount','is_igtf','igtf_percentage','currency_id')
	def _compute_igtf_amount(self):
		for payment in self:
			igtf_amount = 0.0
			total_payment = 0.0
			if payment.amount and payment.is_igtf:
				igtf_percentage = payment.igtf_percentage / 100
				igtf_amount = round(igtf_percentage * payment.amount, 2)
			payment.update({
				'igtf_amount' : igtf_amount,
				'total_payment' : payment.amount + igtf_amount
			})

	@api.onchange('company_id','company_currency_id','currency_id')
	def onchange_currency(self):
		for payment in self:
			is_igtf = igtf_wizard = False

			if payment.currency_id and payment.currency_id.name != 'VEF':
				is_igtf = igtf_wizard = True

			payment.update({
                'igtf_wizard' : igtf_wizard,
                'is_igtf' : is_igtf
            })

	igtf_wizard = fields.Boolean(string='Show IGTF')
	is_igtf = fields.Boolean(string='Retencion de IGTF Divisa')
	igtf_percentage = fields.Float(string='% IGTF Divisa', related="company_id.igtf_percentage", store=True)
	igtf_journal_id = fields.Many2one('account.journal', string='Diario IGTF',
		domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
        default=lambda self: self.env['account.journal'].search([('name', '=', 'IGTF Ventas')], limit=1)
    )
	receivable_account_id = fields.Many2one('account.account', string='Cuenta Recibos IGTF', 
		related="company_id.receivable_account_id", store=True)
	payable_account_id = fields.Many2one('account.account', string='Cuenta Pagos IGTF',
		related="company_id.payable_account_id", store=True)
	igtf_amount = fields.Monetary(string='Importe IGTF', store=True, readonly=True, tracking=True,
		compute='_compute_igtf_amount')
	total_payment = fields.Monetary(string='Total Pagari (Amount + IGTF)', store=True, readonly=True, tracking=True,
		compute='_compute_igtf_amount')

	def _create_payment_vals_from_wizard(self, batch_result):
		vals = super()._create_payment_vals_from_wizard(batch_result)
		vals.update({
			'igtf_wizard': self.igtf_wizard,
			'is_igtf': self.is_igtf,
			'igtf_percentage': self.igtf_percentage,
			'igtf_journal_id': self.igtf_journal_id.id or self.env['account.journal'].search([('code', '=', 'IGTF1')], limit=1).id,
			'igtf_amount': self.igtf_amount,
			'total_payment' : self.total_payment
		})
		return vals


	def _create_payments(self):
		payments = super(AccountPaymentRegister, self)._create_payments()
		if self.is_igtf:
			for i, pay in enumerate(payments):
				move_vals = {
					# 'payment_id': pay.id,
					'move_type': 'entry',
					'date': pay.date,
					'ref': pay.ref,
					'journal_id': pay.igtf_journal_id.id or self.env['account.journal'].search([('code', '=', 'IGTF1')], limit=1).id,
					'currency_id' : pay.currency_id.id
				}
				move_vals['line_ids'] = [(0, 0, line_vals) for line_vals in pay._prepare_move_line_default_vals_igft(write_off_line_vals=None)]
				igtf_move_id = self.env['account.move'].create(move_vals)
				pay.write({
					'igtf_move_id' : igtf_move_id.id
				})
				pay.igtf_move_id._post(soft=False)


class AccountPayment(models.Model):
	_inherit = 'account.payment'

	igtf_wizard = fields.Boolean(string='Show IGTF')
	is_igtf = fields.Boolean(string='Retencion de IGTF Divisa')
	igtf_percentage = fields.Float(string='% IGTF Divisa', related="company_id.igtf_percentage", store=True)
	igtf_journal_id = fields.Many2one('account.journal', string='Diario IGTF',
		domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
        default=lambda self: self.env['account.journal'].search([('name', '=', 'IGTF Ventas')], limit=1)
    )
	receivable_account_id = fields.Many2one('account.account', string='Cuenta Recibos IGTF', 
		related="company_id.receivable_account_id", store=True)
	payable_account_id = fields.Many2one('account.account', string='Cuenta Pagos IGTF',
		related="company_id.payable_account_id", store=True)
	igtf_amount = fields.Monetary(string='Importe IGTF', store=True, readonly=True, tracking=True,
		compute='_compute_igtf_amount')
	total_payment = fields.Monetary(string='Total Pagar (Amount + IGTF)', store=True, readonly=True, tracking=True,
		compute='_compute_igtf_amount')
	igtf_move_id = fields.Many2one('account.move', string='Asiento IGTF Divisa')


	@api.depends('amount','is_igtf','igtf_percentage','currency_id')
	def _compute_igtf_amount(self):
		for payment in self:
			igtf_amount = 0.0
			total_payment = 0.0
			if payment.amount and payment.is_igtf:
				igtf_percentage = payment.igtf_percentage / 100
				igtf_amount = round(igtf_percentage * payment.amount, 2)
			payment.update({
				'igtf_amount' : igtf_amount,
				'total_payment' : payment.amount + igtf_amount
			})

	@api.onchange('company_id','company_currency_id','currency_id')
	def onchange_currency(self):
		for payment in self:
			igtf_wizard = False
			is_igtf = False
			if payment.currency_id and payment.currency_id.name != 'VEF':
				igtf_wizard = True
				is_igtf = True
			payment.update({
                'igtf_wizard' : igtf_wizard,
                'is_igtf' : is_igtf
            })

	def action_post(self):
		default_partner_type = self._context.get('default_partner_type')
		if not default_partner_type:
			return super(AccountPayment, self).action_post() 
		payment = super(AccountPayment, self).action_post()
		for pay in self:
			move_vals = {
				# 'payment_id': pay.id,
				'move_type': 'entry',
				'date': pay.date,
				'ref': pay.ref,
				'journal_id': pay.igtf_journal_id.id or self.env['account.journal'].search([('code', '=', 'IGTF1')], limit=1).id,
				'currency_id' : pay.currency_id.id
			}
			move_vals['line_ids'] = [(0, 0, line_vals) for line_vals in pay._prepare_move_line_default_vals_igft(write_off_line_vals=None)]
			igtf_move_id = self.env['account.move'].create(move_vals)
			pay.write({
				'igtf_move_id' : igtf_move_id.id
			})
			pay.igtf_move_id._post(soft=False)
		return payment

	def _prepare_move_line_default_vals_igft(self, write_off_line_vals=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
			* amount:       The amount to be added to the counterpart amount.
			* name:         The label to set on the line.
			* account_id:   The account on which create the write-off.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		self.ensure_one()
		write_off_line_vals = write_off_line_vals or {}

		counterpart_account_id = self.igtf_journal_id.suspense_account_id.id

		if not self.company_id.receivable_account_id or not self.company_id.payable_account_id :
			raise UserError(_(
				"You can't create a new statement line without setting accounts on company %s."
			) % self.company_id.name)

		# Compute amounts.
		write_off_amount_currency = 0.0

		if self.payment_type == 'inbound':
			# Receive money.
			liquidity_amount_currency = self.igtf_amount
		elif self.payment_type == 'outbound':
			# Send money.
			liquidity_amount_currency = -self.igtf_amount
			write_off_amount_currency *= -1
		else:
			liquidity_amount_currency = write_off_amount_currency = 0.0

		write_off_balance = self.currency_id._convert(
			write_off_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		liquidity_balance = self.currency_id._convert(
			liquidity_amount_currency,
			self.company_id.currency_id,
			self.company_id,
			self.date,
		)
		counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
		counterpart_balance = -liquidity_balance - write_off_balance
		currency_id = self.currency_id.id

		if self.is_internal_transfer:
			if self.payment_type == 'inbound':
				liquidity_line_name = _('Transfer to %s', self.journal_id.name)
			else: # payment.payment_type == 'outbound':
				liquidity_line_name = _('Transfer from %s', self.journal_id.name)
		else:
			liquidity_line_name = self.payment_reference

		# Compute a default label to set on the journal items.

		# payment_display_name = self._prepare_payment_display_name()

		# default_line_name = self.env['account.move.line']._get_default_line_name(
		# 	_("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
		# 	self.amount,
		# 	self.currency_id,
		# 	self.date,
		# 	partner=self.partner_id,
		# )

		line_vals_list = [
			# Liquidity line.
			{
				'name': 'Comision IGTF Divisa',
				'date_maturity': self.date,
				'amount_currency': liquidity_amount_currency,
				'currency_id': currency_id,
				'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
				'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.igtf_journal_id.default_account_id.id,
			},
			# Receivable / Payable.
			{
				'name': 'Comision IGTF Divisa',
				'date_maturity': self.date,
				'amount_currency': counterpart_amount_currency,
				'currency_id': currency_id,
				'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
				'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.company_id.receivable_account_id.id if liquidity_balance < 0.0 else self.company_id.payable_account_id.id,
			},
		]
		return line_vals_list

	def action_cancel(self):
		''' draft -> cancelled '''
		payment = super(AccountPayment, self).action_cancel()
		if self.is_igtf:
			self.igtf_move_id.button_cancel()
		return payment

	def action_draft(self):
		''' posted -> draft '''
		payment = super(AccountPayment, self).action_draft()
		if self.is_igtf:
			self.igtf_move_id.button_draft()
		return payment