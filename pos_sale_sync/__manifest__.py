{
    'name': 'POS to Sale Sync',
    'version': '14.0.1.0.0',
    'summary': 'Enviar pedidos POS a otra base de Odoo como presupuestos (sale.order)',
    'category': 'Point Of Sale',
    'author': 'Automático',
    'license': 'LGPL-3',
    'depends': ['base', 'point_of_sale', 'sale'],
    'data': [
        'views/pos_order_views.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
