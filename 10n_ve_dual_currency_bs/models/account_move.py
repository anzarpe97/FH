# -*- coding: utf-8 -*-
from odoo import models, fields, api
from decimal import Decimal, ROUND_UP, ROUND_HALF_UP, InvalidOperation
from odoo.exceptions import ValidationError
import logging


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    amount_untaxed_bs = fields.Float(
        string="Base Imponible Bs.",
        store=True,
        compute='_compute_amounts_bs',
        tracking=5,
        digits=(16, 4)
    )

    
    type_report_currency  = fields.Selection(
            [
                ('usd', 'Dolares.'), 
                ('bs',  'Bolívares'),
                ('usd_bs', 'Dual'),
            ] ,
            default = "usd", 
            string = "Totales en factura (PDF)"
    )
    
    amount_tax_bs = fields.Float(
        string="Impuesto Bs",
        store=True,
        compute='_compute_amounts_bs',
        digits=(16, 4)
    )
    
    amount_total_bs = fields.Float(
        string="Total Bs",
        store=True,
        compute='_compute_amounts_bs',
        tracking=4,
        digits=(16, 4)
    )
    
    currency_ref_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.ref('base.VEF'),
        digits=(16, 4)
    )
       
    display_tax_currency = fields.Boolean(string='Mostrar Tasa del día (PDF)', default = True, )

    amount_residual_bs = fields.Monetary(
        string='Bs. Monto Deudor',
        compute='_compute_amounts_bs',
        store=True,
        digits=(16, 2)
    )

    type_report_currency = fields.Selection(
        [
            ('usd', 'Dólares'),
            ('bs', 'Bolívares'),
            ('usd_bs', 'Dual')
        ],
        default='usd',
        string="Totales en factura (PDF)"
    )
    
    display_tax_currency = fields.Boolean(
        string='Mostrar Tasa del día (PDF)',
        default=True,
    )

    @api.model
    def getRate(self):
        res_currency_id = self.env['res.currency'].sudo().search([
            ('name', '=', 'VEF'),
            ('active', '=', True)
        ], limit=1)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            tx = Decimal(str(rate_day.company_rate))
            tx_amount = tx.quantize(Decimal('1.0000'))
            return tx_amount
        else:
            return 1.00

    tax_day = fields.Float(
        string='Tasa del día',
        default=getRate,
        states={'sale': [('readonly', True)]},
        digits='Product Price'
    )

    @api.model
    def create(self, vals):
        if vals.get('invoice_origin', False):
            order_id = self.env['sale.order'].search([
                ('name', '=', vals.get('invoice_origin')),
                ('company_id', '=', self.env.user.company_id.id)
            ])
            if not order_id:
                order_id = self.env['purchase.order'].search([
                    ('name', '=', vals.get('invoice_origin')),
                    ('company_id', '=', self.env.user.company_id.id)
                ])
            if order_id:
                vals.update({'tax_day': order_id.tax_day})
        return super(AccountMove, self).create(vals)

    def calcular_totales_por_impuesto(self):
        impuestos_totales = {}
        for move in self:
            for line in move.invoice_line_ids:
                subtotal_bs = Decimal(str(line.subtoal_amount_bs))
                for impuesto in line.tax_ids:
                    if impuesto.amount != 0:
                        impuestod = Decimal(str(impuesto.amount))
                        impuesto_nombre = impuesto.name
                        impuesto_valor = (subtotal_bs * impuestod / 100).quantize(Decimal('1.00'))
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor
        return impuestos_totales

    def calcular_totales_por_impuesto_USD(self):
        impuestos_totales = {}
        for move in self:
            for line in move.invoice_line_ids:
                for impuesto in line.tax_ids:
                    if impuesto.amount != 0:
                        impuesto_nombre = impuesto.name
                        impuesto_valor = (line.price_subtotal * impuesto.amount) / 100
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor
        return impuestos_totales

    @api.depends(
        'invoice_line_ids.price_unit_bs',
        'invoice_line_ids.subtoal_amount_bs',
        'invoice_line_ids.price_subtotal',
        'tax_day'
    )
    def _compute_amounts_bs(self):
        for move in self:
            if move.tax_day > 0:
                base_imponible_bs = sum(line.subtoal_amount_bs for line in move.invoice_line_ids)
                base_imponible_bs = Decimal(str(base_imponible_bs)).quantize(Decimal('1.0000'))

                total_impuesto_bs = sum([
                    round(valor, 6)
                    for _, valor in move.calcular_totales_por_impuesto().items()
                ])
                total_impuesto_bs = Decimal(str(total_impuesto_bs)).quantize(Decimal('1.00'))

                total_bs = base_imponible_bs + total_impuesto_bs

                amount_residual = Decimal(str(move.amount_residual or 0.00))
                amount_residual_bs = (amount_residual * Decimal(str(move.tax_day))).quantize(Decimal('1.00'))

                move.amount_untaxed_bs = float(base_imponible_bs)
                move.amount_tax_bs = float(total_impuesto_bs)
                move.amount_total_bs = float(total_bs)
                move.amount_residual_bs = float(amount_residual_bs) if move.amount_residual else 0.00
            else:
                move.amount_untaxed_bs = 0.00
                move.amount_tax_bs = 0.00
                move.amount_total_bs = 0.00
                move.amount_residual_bs = 0.00

    def _compute_amounts_line_bs(self):
        for line in self.invoice_line_ids:
            line._compute_price_unit_bs()

    def updateRateDate(self):
        self._compute_amounts_bs()
        self._compute_amounts_line_bs()

    #FIN AQUI

class InheritMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    currency_ref_id = fields.Many2one(
        'res.currency',
        string='Moneda Referencial',
        default=lambda self: self.env.ref('base.VEF')
    )

    price_unit_bs = fields.Monetary(
        string="Bs. Precio",
        currency_field='currency_ref_id',
        compute='_compute_price_unit_bs',
        inverse='_inverse_price_unit_bs',
        digits='Product Price',
        store=True,
        readonly=False,
        precompute=True
    )

    subtoal_amount_bs = fields.Monetary(
        string="Bs. Subtotal",
        currency_field='currency_ref_id',
        compute='_compute_amounts_bs',
        store=True,
        tracking=4
    )

    related_tax_day = fields.Float(
        string='Tasa del día',
        related='move_id.tax_day',
        readonly=True,
        store=True,
        precompute=True,
        digits=(16, 3)
    )

    @api.depends('product_id', 'price_unit', 'move_id.tax_day')
    def _compute_price_unit_bs(self):
        for line in self:
            if line.price_unit and line.move_id.tax_day:
                try:
                    price_unit = Decimal(str(line.price_unit))
                    tax_day = Decimal(str(line.move_id.tax_day))
                    price_unit_bs = (price_unit * tax_day).quantize(Decimal('1.0000'))
                    line.price_unit_bs = float(price_unit_bs)
                except (InvalidOperation, ZeroDivisionError):
                    line.price_unit_bs = 0.00
            elif line.product_id:
                line.price_unit_bs = line.product_id.price_bs or 0.00
            else:
                line.price_unit_bs = 0.00

    def _inverse_price_unit_bs(self):
        for line in self:
            if line.price_unit_bs and line.move_id.tax_day:
                try:
                    price_unit_bs = Decimal(str(line.price_unit_bs))
                    tax_day = Decimal(str(line.move_id.tax_day))
                    
                    if tax_day == 0:
                        raise ValidationError("La tasa 'tax_day' no puede ser cero para el cálculo.")
                    
                    price_unit = (price_unit_bs / tax_day).quantize(Decimal('1.0000'))
                    line.price_unit = float(price_unit)
                except (InvalidOperation, ZeroDivisionError):
                    raise ValidationError("Error en el cálculo del precio. Verifique los valores de 'tax_day' y 'price_unit_bs'.")
            else:
                line.price_unit = 0.00

    @api.depends('price_unit_bs', 'quantity', 'discount')
    def _compute_amounts_bs(self):
        for line in self:
            if line.price_unit_bs and line.quantity:
                discount_factor = Decimal('1.0') - (Decimal(str(line.discount)) / Decimal('100.0'))
                subtotal = Decimal(str(line.price_unit_bs)) * Decimal(str(line.quantity)) * discount_factor
                line.subtoal_amount_bs = float(subtotal.quantize(Decimal('1.0000')))
            else:
                line.subtoal_amount_bs = 0.00
