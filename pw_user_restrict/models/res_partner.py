# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        res = super(ResPartner, self).check_access_rights(operation, raise_exception=False)
        if operation == 'create' and self._name == 'res.partner' and self.env.user.has_group('pw_user_restrict.group_no_create_partner'):
            return False
        return res
