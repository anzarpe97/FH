odoo.define('mai_pos_dual_currency.CustomPaymentScreen', function(require) {
	'use strict';

	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const Registries = require('point_of_sale.Registries');
	const NumberBuffer = require('point_of_sale.NumberBuffer');
	
	const CustomPaymentScreen = PaymentScreen => 
		class extends PaymentScreen {

			get _getNumberBufferConfig() {
	            let config = {
	                // The numberBuffer listens to this event to update its state.
	                // Basically means 'update the buffer when this event is triggered'
	                nonKeyboardInputEvent: 'input-from-numpad',
	                // When the buffer is updated, trigger this event.
	                // Note that the component listens to it.
	                triggerAtInput: 'update-selected-paymentline',
	            };
	            // Check if pos has a cash payment method
	            const hasCashPaymentMethod = this.payment_methods_from_config.some(
	                (method) => method.type === 'cash'
	            );

	            const pagoUsdMethod = this.payment_methods_from_config.some(
	                (method) => method.pago_usd === true
	            );

	            if (!hasCashPaymentMethod && !pagoUsdMethod) {
	                config['maxValue'] = this.currentOrder.get_due();
	                config['maxValueReached'] = this.showMaxValueError.bind(this);
	            }

	            return config;
	        }
			
			_updateSelectedPaymentline() {
				let self = this;
				let rate_company = this.env.pos.config.rate_company;
				let show_currency_rate = this.env.pos.config.show_currency_rate;
						
				if (this.paymentLines.every((line) => line.paid)) {
					this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
				}
				if (!this.selectedPaymentLine) return; // do nothing if no selected payment line
				// disable changing amount on paymentlines with running or done payments on a payment terminal
				const payment_terminal = this.selectedPaymentLine.payment_method.payment_terminal;
				if (
					payment_terminal &&
					!['pending', 'retry'].includes(this.selectedPaymentLine.get_payment_status())
				) {
					return;
				}
				if (NumberBuffer.get() === null) {
					this.deletePaymentLine({ detail: { cid: this.selectedPaymentLine.cid } });
				} else {
					let	price_other_currency = NumberBuffer.getFloat();
					if(this.selectedPaymentLine.payment_method.pago_usd){
						price_other_currency = (price_other_currency * rate_company)/show_currency_rate;
						this.selectedPaymentLine.set_usd_amt(NumberBuffer.getFloat());

					}
					this.selectedPaymentLine.set_amount(price_other_currency);
					
					// let	price_other_currency = NumberBuffer.getFloat();
					// if(this.selectedPaymentLine.payment_method.pago_usd){
					// 	if(rate_company > show_currency_rate){
					// 		price_other_currency = (price_other_currency * rate_company)/show_currency_rate;
					// 	}
					// 	else if(rate_company < show_currency_rate){
					// 		price_other_currency = price_other_currency * rate_company;
					// 	}
					// 	this.selectedPaymentLine.set_usd_amt(NumberBuffer.getFloat());

					// }
					// this.selectedPaymentLine.set_amount(price_other_currency);
					
				}
			}


		}
	Registries.Component.extend(PaymentScreen, CustomPaymentScreen);
	return PaymentScreen;

});