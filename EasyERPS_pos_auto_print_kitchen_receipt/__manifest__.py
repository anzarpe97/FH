# -*- coding: utf-8 -*-
{
    'name': "POS auto print kitchen receipt",
    'support': "support@easyerps.com",
    'license': "LGPL-3",
    'summary': """
        Auto print kitchen receipt after validate
        """,
    'author': "EasyERPS",
    'website': "https://easyerps.com",
    'category': 'Point of Sale',
    'version': '16.0.1',
    'depends': ['base', 'point_of_sale', 'pos_restaurant'],
    'data': [
        # 'views/templates.xml',  # Cargar las plantillas necesarias
    ],
    'assets': {
        'point_of_sale.assets': [
            'EasyERPS_pos_auto_print_kitchen_receipt/static/src/js/Models.js',
            'EasyERPS_pos_auto_print_kitchen_receipt/static/src/js/ReceiptScreen.js',
            'EasyERPS_pos_auto_print_kitchen_receipt/static/src/css/style.css',  # Incluir el CSS
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
