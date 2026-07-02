odoo.define('pos_access_rights_app.pos', function(require){
	'use strict';

	const NumpadWidget = require('point_of_sale.NumpadWidget');
	const ActionpadWidget = require('point_of_sale.ActionpadWidget');
	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const PaymentScreenNumpad = require('point_of_sale.PaymentScreenNumpad');
	const MobileOrderWidget = require('point_of_sale.MobileOrderWidget');
	var session = require('web.session');
	const Registries = require('point_of_sale.Registries');
    const {onMounted} = owl;

	var discount = false;
	var plus_minus = false;
	var payment = false;
	var numpad = false;
	var price = false;
	var partner = false;
	var quantity = false;

	session.user_has_group('pos_access_rights_app.group_discount_button').then(function (has_create_group) {
		discount = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_plus_minus_button').then(function (has_create_group) {
		plus_minus = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_payment_button').then(function (has_create_group) {
		payment = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_quantity_button').then(function (has_create_group) {
		quantity = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_numpad_button').then(function (has_create_group) {
		numpad = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_price_button').then(function (has_create_group) {
		price = has_create_group
	});
	session.user_has_group('pos_access_rights_app.group_customer_button').then(function (has_create_group) {
		partner = has_create_group
	});


	const POSNumpadWidget = (NumpadWidget) =>
		class extends NumpadWidget{

			setup() {
				super.setup();
				let self = this;
				onMounted(() => {
	               self.mounted();
	            });
			}

			mounted() {
				$('.mode-button').each(function(idx,el){
					if (discount == true){
						if ($(el).text() == '% Disc'){
							$(el).addClass('disabled-mode');
							$(el).css('background-color', 'lightgrey');
						}
					}
					if (quantity == true){
						if ($(el).text() == 'Qty'){
							$(el).addClass('disabled-mode');
							$(el).removeClass('selected-mode');
							$(el).css({'background-color':'lightgrey', 'color':'#555555'});
						};
					}
					if (price == true){
						if ($(el).text() == 'Price'){
							$(el).addClass('disabled-mode');
							$(el).css('background-color', 'lightgrey');
						}
					}
				});
				if (numpad == true){
					$('.number-char').prop('disabled', true);
					$('.number-char').css('background-color', 'lightgrey');
				}
				if (plus_minus == true){
					$('.numpad-minus').prop('disabled', true);
					$('.numpad-minus').css('background-color', 'lightgrey');
				}
			}
		};
	Registries.Component.extend(NumpadWidget, POSNumpadWidget);

	const POSActionpadWidget = (ActionpadWidget) =>
		class extends ActionpadWidget{

			setup() {
				super.setup();
				let self = this;
				onMounted(() => {
	               self.mounted();
	            });
			}

			mounted() {
				if (partner == true){
					$('.set-partner').prop('disabled', true);
					$('.set-partner').css('background-color', 'lightgrey');
				}
				if (payment == true){
					$('.pay').prop('disabled', true);
					$('.pay').css('background-color', 'lightgrey');
				}
			}
		};
	Registries.Component.extend(ActionpadWidget, POSActionpadWidget);

    const POSMobileOrderWidget = (MobileOrderWidget) =>
		class extends MobileOrderWidget{

			setup() {
				super.setup();
				let self = this;
				onMounted(() => {
	               self.mounted();
	            });
			}

			mounted() {
				if (payment == true){
                    $('.disabledpane').prop('disabled', true);
					$('.disabledpane').css('background-color', 'lightgrey');
				}
			}
		};
	Registries.Component.extend(MobileOrderWidget, POSMobileOrderWidget);

	const POSPaymentScreen = (PaymentScreen) =>
		class extends PaymentScreen{

			setup() {
				super.setup();
				let self = this;
				onMounted(() => {
	               self.mounted();
	            });
			}

			mounted() {
				if (partner == true){
					$('.partner-button').find('.button').prop('disabled', true);
					$('.partner-button').css('background-color', 'lightgrey');
					$('.partner-button').find('.button').css('background-color', 'lightgrey');
				}
				
			}

			async selectPartner() {
	            // IMPROVEMENT: This code snippet is repeated multiple times.
	            // Maybe it's better to create a function for it.
	            if (partner == false){
		            const currentPartner = this.currentOrder.get_partner();
		            const { confirmed, payload: newPartner } = await this.showTempScreen(
		                'PartnerListScreen',
		                { partner: currentPartner }
		            );
		            if (confirmed) {
		                this.currentOrder.set_partner(newPartner);
		                this.currentOrder.updatePricelist(newPartner);
		            }
		        }
	        }

		};
	Registries.Component.extend(PaymentScreen, POSPaymentScreen);

	const POSPaymentScreenNumpad = (PaymentScreenNumpad) =>
		class extends PaymentScreenNumpad{

			setup() {
				super.setup();
				let self = this;
				onMounted(() => {
	               self.mounted();
	            });
			}

			mounted() {
				$('.number-char').each(function(idx,el){
					if (plus_minus == true){
						if ($(el).text() == "+/-"){
							$(el).prop('disabled', true);
							$(el).css('background-color', 'lightgrey');
						}
					}
					if (numpad == true){
						if ($(el).text() == "1" || $(el).text() == "2" || $(el).text() == "3" || $(el).text() == "4" || $(el).text() == "5" || $(el).text() == "6" || 
							$(el).text() == "7" || $(el).text() == "8" || $(el).text() == "9" || $(el).text() == "0" || $(el).text() == "."){
							$(el).prop('disabled', true);
							$(el).css('background-color', 'lightgrey');
						}
					}
				});
				if (numpad == true){
					$('.mode-button').prop('disabled', true);
					$('.mode-button').css('background-color', 'lightgrey');
				}
			}
		};
	Registries.Component.extend(PaymentScreenNumpad, POSPaymentScreenNumpad);

	return {
		POSNumpadWidget,
		POSActionpadWidget,
		POSPaymentScreen,
		POSPaymentScreenNumpad
	}
});
