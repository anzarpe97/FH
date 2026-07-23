{
    "name": "Odoo Remote DB Connector",
    "summary": "Conexión y prueba de acceso a bases de datos Odoo remotas",
    "version": "16.0.1.0.0",
    "author": "Custom",
    "license": "AGPL-3",
    "category": "Tools",
    "depends": ["base", "point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/odoo_remote_connection_data.xml",
        "views/odoo_remote_connection_views.xml",
        "views/pos_session_views.xml",
    ],
    "application": True,
    "installable": True,
}
