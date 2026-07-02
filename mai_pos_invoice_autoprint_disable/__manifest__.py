{
	"name": "POS Invoice Auto Check | POS Default Invoicing | POS Auto invoice and Disable auto print | Restrict POS Invoice Download",
    "version": "16.3.2.1",
	"category" : "Point of Sale",
	"summary": "POS Auto Invoice Check - Using this module : 1> You can print POS auto invoice and 2> Using this module you and make auto invoice trust 			and disable Invoice print ",
	'description': """POS Auto Invoice Check - Using this module : 1> You can print POS auto invoice and 2> Using this module you and make auto invoice trust 			and disable Invoice print
	""",
	'price': 6.5,
	'sequence': 1,    
	'currency': 'USD',
	"author" : "MAISOLUTIONSLLC",
	"email": 'apps@maisolutionsllc.com',
	"website":'http://maisolutionsllc.com/',
	'license': 'OPL-1',
	"depends": ["base","point_of_sale",],
	"data": [
		'views/pos_config_view.xml',
	],
	'assets': {
		'point_of_sale.assets': [
			# "mai_pos_invoice_autoprint_disable/static/src/js/models.js",
			"mai_pos_invoice_autoprint_disable/static/src/js/PaymentScreen.js", 
		],
	},
	"images": ['static/description/main_screenshot.gif'],
	"live_test_url" : "https://youtu.be/QVHfnvg93vU",      
	"installable": True,
	"application": False,
	"auto_install": False,	
}
