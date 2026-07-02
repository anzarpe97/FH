{
    'name': 'Recibo Personalizado',
    'category': 'Sales/Point of Sale',
    'summary': 'This module is used to customized receipt of point of sale when a user adds a product in the cart and validates payment and print receipt, then the user can see the client name on POS Receipt. | Custom Receipt | POS Reciept | Payment | POS Custom Receipt',
    'description': "Customized our point of sale receipt",
    'version': '16.0.3.0',
    'website': '',
    'author': 'Aecas by Contables',
    'images': [''],
    'depends': ['base', 'point_of_sale'],
    'assets': {
        'point_of_sale.assets': [
            "custom_pos_receipt2/static/src/js/models.js",
            "custom_pos_receipt2/static/src/xml/pos.xml",
        ],
    },
    'installable': True,
}
