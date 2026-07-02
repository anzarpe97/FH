# -*- coding: utf-8 -*-
from odoo import models, fields, osv , api
from odoo.exceptions import UserError, ValidationError,Warning
import logging
import requests
from decimal import Decimal, ROUND_DOWN, InvalidOperation, ROUND_UP


_logger = logging.getLogger(__name__)

"""
    in this code We validate the available quantities and send it to the API.
"""


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    

    validate_Check_orderline  = fields.Boolean(string='Validar si tiene lineas',compute='_compute_validate_order_line')
    
    amount_untaxed_bs = fields.Float(string="Base Imponible Bs.", store=True, compute='_compute_amounts_bs', tracking=5, digits=(16, 4))
    amount_tax_bs = fields.Float(string="Impuesto Bs", store=True, compute='_compute_amounts_bs',digits=(16, 4))
    amount_total_bs = fields.Float(string="Total BS", store=True, compute='_compute_amounts_bs', tracking=4,digits=(16, 4))
    currency_ref_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.ref('base.VEF'),digits=(16, 4))
    amount_residual_bs = fields.Monetary(
        string='Bs. Monto Deudor',
        compute='_compute_amounts_bs', 
        store=True,
        digits=(16, 4)
    )

    @api.model
    def getRate(self):
        res_currency_id = self.env['res.currency'].sudo().search([('name','=','VEF'),('active','=',True)], limit=1)
        if res_currency_id and res_currency_id.rate_ids:
            rate_day = res_currency_id.rate_ids.sorted('name', reverse=True)[:1]
            return round(rate_day.company_rate , 2) 
        else :
            return   1.00
        
    tax_day  = fields.Float(
        string='Tasa del día',
        default = getRate,
        states = {'sale': [('readonly', True)]},
        digits='Product Price',
    )

    def calcular_totales_por_impuesto(self):
        impuestos_totales = {}
        baseImponible = 0.00
        
        for order in self:
            for line in order.order_line:
                subtoal_amount_bs = Decimal(str(line.subtoal_amount_bs))
                baseImponible+= line.subtoal_amount_bs
                for impuesto in line.taxes_id:
                    if impuesto.amount !=0:#vamos hacer los calculos a distinto Excento
                        impuestod = Decimal(str(impuesto.amount))
                        impuesto_nombre = impuesto.name
                        impuesto_valor = subtoal_amount_bs * impuestod / 100
                        impuesto_valor = impuesto_valor.quantize(Decimal('1.0000'))
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor
                            
        baseImponible =  Decimal(str(baseImponible)).quantize(Decimal('1.0000'))
        logging.info(baseImponible)
        return impuestos_totales


    @api.depends('order_line')
    def _compute_validate_order_line(self):
        for rec in self:
            if rec.order_line:
                rec.validate_Check_orderline = False
            else:rec.validate_Check_orderline = True #Si no tiene Valor las lineas del pedido habilita para editar la tasa
    

    
    def calcular_totales_por_impuesto_USD(self):
        impuestos_totales = {}
        totalBaseImponible = 0.00
        for order in self:
            for line in order.order_line:
                for impuesto in line.taxes_id:
                    if impuesto.amount !=0:#vamos hacer los calculos a distinto Excento
                        # logging.info(line.price_subtotal)
                        # logging.info(impuesto.amount)
                        impuesto_nombre = impuesto.name
                        impuesto_valor = (line.price_subtotal * impuesto.amount) / 100
            
                        if impuesto_nombre in impuestos_totales:
                            impuestos_totales[impuesto_nombre] += impuesto_valor
                        else:
                            impuestos_totales[impuesto_nombre] = impuesto_valor

        return impuestos_totales


    @api.depends('order_line')
    def _compute_amounts_bs(self):
        for order in self:
            if order.tax_day > 0:
                # ya viene convertido
                base_imponible_bs = sum([line.subtoal_amount_bs for line in order.order_line])
                base_imponible_bs = Decimal(str(base_imponible_bs)).quantize(Decimal('1.0000'))

                total_impuesto_bs = sum([
                    round(valor, 6)
                    for _, valor in order.calcular_totales_por_impuesto().items()
                ])
                total_impuesto_bs = Decimal(str(total_impuesto_bs)).quantize(Decimal('1.0000'))

                total_bs = base_imponible_bs + total_impuesto_bs

                order.amount_untaxed_bs = float(base_imponible_bs)
                order.amount_tax_bs = float(total_impuesto_bs)
                order.amount_total_bs = float(total_bs)
            else:
                order.amount_untaxed_bs = 0.0000
                order.amount_tax_bs = 0.0000
                order.amount_total_bs = 0.0000

    def _compute_amounts_line_bs(self):
        for line in self.order_line:
            line._compute_price_unit_bs()
            
            
        
    def updateRateDate(self):
        self._compute_amounts_bs()
        self._compute_amounts_line_bs()
        

class InheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    currency_ref_id = fields.Many2one(
        'res.currency', 
        string='Moneda Bolivar', 
        default=lambda self: self.env.ref('base.VEF')
    )
    price_unit_bs = fields.Monetary(
        string="Precio Bs.", 
        currency_field='currency_ref_id',
        compute='_compute_price_unit_bs',
        inverse='_inverse_price_unit_bs',
        digits='Product Price',
        store=True, 
        readonly=False, 
        precompute=True
    )
    subtoal_amount_bs = fields.Monetary(
        string="Subtotal Bs.",
        currency_field='currency_ref_id' ,
        store=True, 
        compute='_compute_amounts_bs', 
        tracking=4)    
    
                
    @api.depends('product_id', 'price_unit',)
    def _compute_price_unit_bs(self):
        for line in self:
            price_subtotal = Decimal(str(line.price_unit))
            tax_day = Decimal(str(line.order_id.tax_day))
            
            if line.price_unit and  line.order_id.tax_day:
                price_unit_bs = price_subtotal * tax_day
                price_unit_bs = price_unit_bs.quantize(Decimal('1.0000'))
                line.price_unit_bs = price_unit_bs
            elif line.product_id:
                line.price_unit_bs = line.product_id.price_bs
            else :
                line.price_unit_bs = 0.00    

    def _inverse_price_unit_bs(self):
        for line in self:
            if line.price_unit_bs and line.order_id.tax_day:
                try:
                    price_unit_bs = Decimal(str(line.price_unit_bs))
                    tax_day = Decimal(str(line.order_id.tax_day))
                    
                    if tax_day == 0:
                        raise ValidationError("La tasa 'tax_day' no puede ser cero para el cálculo.")
                    
                    price_unit = (price_unit_bs / tax_day).quantize(Decimal('1.0000'))
                    line.price_unit = float(price_unit)
                except (InvalidOperation, ZeroDivisionError):
                    raise ValidationError("Error en el cálculo del precio. Verifique los valores de 'tax_day' y 'price_unit_bs'.")
            else:
                line.price_unit = 0.00

    @api.depends('price_unit_bs', 'product_qty', 'discount')
    def _compute_amounts_bs(self):
        for line in self:
            if line.price_unit_bs and line.product_qty:
                discount_factor = Decimal('1.0') - (Decimal(str(line.discount)) / Decimal('100.0'))
                subtotal = Decimal(str(line.price_unit_bs)) * Decimal(str(line.product_qty)) * discount_factor
                line.subtoal_amount_bs = float(subtotal.quantize(Decimal('1.0000')))
            else:
                line.subtoal_amount_bs = 0.00