{
    'name': "POS IGTF workflow | POS IGTF de Venezuela",
    "version": "16.4.3.2",
    "description": """
        Using this module you can add IGTF for Venezuela.
    """,
    "summary": """Using this module you can add IGTF for Venezuela.""",
    'category': 'Point of Sale',
    'price': 149,
    'currency': 'EUR',
    'license': 'OPL-1',
    "author" : "MAISOLUTIONSLLC",
    'sequence': 1,
    "email": 'apps@maisolutionsllc.com',
    "website":'http://maisolutionsllc.com/',
    "depends" : ['base', 'point_of_sale', 'mai_igtf_de_venezuela'],
	"data": [
        'views/pos_view.xml',
	],
    

    'assets': {
        'point_of_sale.assets': [
            'mai_pos_igtf_de_venezuela/static/src/js/pos.js',
            'mai_pos_igtf_de_venezuela/static/src/js/PaymentScreenStatus.js',
            'mai_pos_igtf_de_venezuela/static/src/js/PaymentScreen.js',
            'mai_pos_igtf_de_venezuela/static/src/xml/**/*',
        ],
    },
    "images": ['static/description/main_screenshot.png'],
    "live_test_url" : "",
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
