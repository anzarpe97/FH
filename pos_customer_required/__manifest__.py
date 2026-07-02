# Copyright 2004 apertoso NV - Jos DE GRAEVE <Jos.DeGraeve@apertoso.be>
# Copyright 2016 La Louve - Sylvain LE GAL <https://twitter.com/legalsylvain>
# Copyright 2019 Druidoo - (https://www.druidoo.io)
# Copyright 2022 NuoBiT - Eric Antones <eantones@nuobit.com>
# Copyright 2022 NuoBiT - Kilian Niubo <kniubo@nuobit.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Point of Sale Require Customer2",
    "version": "16.0.2.0.0",
    "category": "Point Of Sale",
    "summary": "Point of Sale Require Customer",
    "author": "Apertoso NV, La Louve, NuoBiT, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/pos",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_view.xml",
        "views/pos_order_view.xml",
    ],
    'assets': {
        'point_of_sale.assets': [
            # 'pos_customer_required/static/src/js/PaymentScreen.js',
            'pos_customer_required/static/src/js/ProductScreen.js',
        ],
    }, 
    "installable": True,
}
