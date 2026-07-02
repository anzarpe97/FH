# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sub_product_line_ids = fields.One2many('product.combo', 'product_template_id', string='Sub Products', copy=False)
    is_combo = fields.Boolean('Use as Combo', copy=False)

    @api.constrains('sub_product_line_ids')
    def check_category_lines(self):
        req_categ_list = []
        unreq_categ_list = []
        for line in self.sub_product_line_ids.filtered(lambda l: l.category_id):
            if len(line.product_ids) < line.no_of_items:
                raise UserError(_("No of items Value cannot be more than products length."))
            if line.is_required_product:
                req_categ_list.append(line.category_id.id)
            else:
                unreq_categ_list.append(line.category_id.id)
            if len(list(set([categ_id for categ_id in req_categ_list if req_categ_list.count(categ_id) > 1]))) > 0:
                raise UserError(_("You can't create duplicated required product category line."))
            if len(list(set([categ_id for categ_id in unreq_categ_list if unreq_categ_list.count(categ_id) > 1]))) > 0:
                raise UserError(_("You can't create duplicated un-required product category line."))


class SubProductCombo(models.Model):
    _name = "product.combo"
    _description = "Product Combo"

    product_template_id = fields.Many2one('product.template', string='Item')
    is_required_product = fields.Boolean('Required Products', copy=False, help="Set boolean for manage required product")
    category_id = fields.Many2one('pos.category', string='Category', required=True,
        help="Select Category for combo product")
    product_ids = fields.Many2many('product.product', required=True,
        string='Product', copy=False, help="Select many product to add in combo")
    no_of_items = fields.Integer('Maximum Number of Items to Select', required=True, default=1, copy=False,
        help="Set how many product select in unrequire products")
    include_all = fields.Boolean('Include all Products', copy=False)
    is_include_in_main_product_price = fields.Boolean('Include in Main Product Price', default=False, copy=False)

    @api.onchange('category_id')
    def onchange_category(self):
        if self.category_id or not self.category_id:
            self.product_ids = [(6, 0, [])]

    @api.onchange('is_required_product')
    def onchange_include_all_products(self):
        self.is_include_in_main_product_price = False
        if self.is_required_product:
            self.is_include_in_main_product_price = True

    @api.onchange('include_all')
    def onchange_include_all_products(self):
        if self.include_all:
            if not self.category_id:
                raise UserError(_('Please select category to include all product in combo.'))
            if self.product_template_id:
                current_id = str(self.product_template_id.id)
                product_tmpl_id = ''.join(x for x in current_id if x.isdigit())
                self.product_ids = [(6, 0, self.env['product.product'].search([('pos_categ_id', '=', self.category_id.id), ('available_in_pos', '=', True), ('is_combo', '=', False), ('type', '!=', 'service'),('product_tmpl_id.id','!=',product_tmpl_id)]).ids)]
            else:
                self.product_ids = [(6, 0, self.env['product.product'].search([('pos_categ_id', '=', self.category_id.id), ('available_in_pos', '=', True),('is_combo', '=', False), ('type', '!=', 'service')]).ids)]
        if not self.include_all:
            self.product_ids = [(6, 0, [])]

    @api.model
    def create(self, vals):
        if vals.get('is_required_product'):
            vals.update({'is_include_in_main_product_price' : True})
        return super(SubProductCombo, self).create(vals)

    def write(self, vals):
        vals.update({'is_include_in_main_product_price' : False})
        if vals.get('is_required_product'):
            vals.update({'is_include_in_main_product_price' : True})
        return super(SubProductCombo, self).write(vals)

    @api.constrains('no_of_items')
    def _check_no_of_items(self):
        for rec in self:
            if rec.no_of_items <= 0:
                raise ValidationError(_('No of items Value cannot be <= 0.'))
