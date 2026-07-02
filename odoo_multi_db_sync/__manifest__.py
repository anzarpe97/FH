{
    "name": "Odoo Multi DB Sync (XML-RPC)",
    "version": "1.0.0",
    "summary": "Enviar contactos desde una instancia A hacia otra B via XML-RPC",
    "author": "Disprocar",
    "category": "Tools",
    "depends": ["base", "contacts"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "data/ir_cron.xml",
        "security/ir.model.access.csv"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
