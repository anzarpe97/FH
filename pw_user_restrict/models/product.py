# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        res = super(ProductProduct, self).check_access_rights(operation, raise_exception=False)
        if operation == 'create' and self._name == 'product.product' and self.env.user.has_group('pw_user_restrict.group_no_create_product'):
            return False
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        res = super(ProductTemplate, self).check_access_rights(operation, raise_exception=False)
        if operation == 'create' and self._name == 'product.template' and self.env.user.has_group('pw_user_restrict.group_no_create_product'):
            return False
        return res
