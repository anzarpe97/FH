from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_sale_sync_remote_url = fields.Char(string='Remote Odoo URL', config_parameter='pos_sale_sync.remote_url')
    pos_sale_sync_remote_db = fields.Char(string='Remote DB name', config_parameter='pos_sale_sync.remote_db')
    pos_sale_sync_remote_user = fields.Char(string='Remote user', config_parameter='pos_sale_sync.remote_user')
    pos_sale_sync_remote_password = fields.Char(string='Remote password', config_parameter='pos_sale_sync.remote_password')
