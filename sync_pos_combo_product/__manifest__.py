# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'POS Product Combo',
    'version': '1.0',
    'summary': 'Product can be sold as a Combo in POS',
    'description': """
        Product can be sold as a Combo in POS.
        Combo Product
        product
        point of sale
        sales
        Bundle
        Sales
        sale
    """,
    'category': 'Point Of Sale',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'www.synconics.com',
    'depends': ['pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/pos_config_view.xml',
        'report/combo_invoice_report.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'sync_pos_combo_product/static/src/css/product_combo.css',
            'sync_pos_combo_product/static/src/js/models.js',
            'sync_pos_combo_product/static/src/js/Popups/ComboApplyPopup.js',
            'sync_pos_combo_product/static/src/js/Screens/ProductScreen/ProductScreen.js',
            'sync_pos_combo_product/static/src/xml/Screens/ProductScreen/Orderline.xml',
            'sync_pos_combo_product/static/src/xml/Screens/ProductScreen/ProductItem.xml',
            'sync_pos_combo_product/static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml',
            'sync_pos_combo_product/static/src/xml/Popups/ComboApplyPopup.xml',
        ],
    },
    'images': [
        'static/description/main_screen.png'
    ],
    'price': 69.0,
    'currency': 'EUR',
    'license': 'OPL-1',
    'auto_install': False,
    'application': True,
    'installable': True,
}
