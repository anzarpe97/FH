odoo.define('custom_pos_receipt.CustomPaymentScreen', function(require) {

	const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const {onMounted} = owl;

	const CustomPaymentScreen = PaymentScreen => class extends PaymentScreen {

		setup() {
			super.setup();
		}

		addNewPaymentLine({ detail: paymentMethod }) {
            // original function: click_paymentmethods

            let result = this.currentOrder.add_paymentline(paymentMethod);

            let selected_paymentline = this.currentOrder.selected_paymentline;
            let currency = this.env.pos.allcurrency;


            for(var i=0;i<currency.length;i++){
                if(paymentMethod.currency_id == false){
                    selected_paymentline.set_currency_symbol(currency[i].symbol);
                }
            }



            if (result){
                NumberBuffer.reset();
                return true;
            }
            else{
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Error'),
                    body: this.env._t('There is already an electronic payment in progress.'),
                });
                return false;
            }
        }
	}

	Registries.Component.extend(PaymentScreen, CustomPaymentScreen);
	return PaymentScreen;
});