from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"
    pos_conf_id = fields.Many2one('pos.config', string="Inicio de Sesión Directo en POS",
                                  help='Seleccione inicio de sesión directo para este usuario')