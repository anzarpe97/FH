odoo.define('mai_pos_igtf_de_venezuela.IgtfPaymentScreen', function(require) {
	'use strict';

	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const Registries = require('point_of_sale.Registries');
	const NumberBuffer = require('point_of_sale.NumberBuffer');

	const IgtfPaymentScreen = PaymentScreen => 
		class extends PaymentScreen {
			
			addNewPaymentLine({ detail: paymentMethod }) {
				var self = this;
				if (this.currentOrder.electronic_payment_in_progress()) {
					this.showPopup('ErrorPopup', {
						title: this.env._t('Error'),
						body: this.env._t('There is already an electronic payment in progress.'),
					});
					return false;
				}else{
					var payment_method = null;
					var igtf_pay = null;
					for (var i = 0; i < this.env.pos.payment_methods.length; i++ ) {
						if (this.env.pos.payment_methods[i].id === paymentMethod.id ){
							if(this.env.pos.payment_methods[i]['is_igtf'] === true){
								payment_method = this.env.pos.payment_methods[i];
								igtf_pay = true;
								break;
							}else{
								payment_method = this.env.pos.payment_methods[i];
								break;
							}   
						}
					}
					if(igtf_pay == true){
						var order = this.env.pos.get_order();
						var due = order.get_due();
						var total  = self.env.pos.company.igtf_percentage * 0.01 * due;


						this.env.pos.get_order().set_igtf_charge(total + order.get_igtf_charge());
						this.currentOrder.add_paymentline(payment_method);
						NumberBuffer.reset();
						this.payment_interface = payment_method.payment_terminal;
						if (this.payment_interface) {
							this.currentOrder.selected_paymentline.set_payment_status('pending');
						}
					}else{
						this.currentOrder.add_paymentline(paymentMethod);
						NumberBuffer.reset();
						this.payment_interface = paymentMethod.payment_terminal;
						if (this.payment_interface) {
							this.currentOrder.selected_paymentline.set_payment_status('pending');
						}
					}
					return true;
				}
			}

			

			deletePaymentLine(event) {
				var self = this;
				const { cid } = event.detail;
				const line = this.paymentLines.find((line) => line.cid === cid);
				// If a paymentline with a payment terminal linked to
				// it is removed, the terminal should get a cancel
				// request.
				if (['waiting', 'waitingCard', 'timeout'].includes(line.get_payment_status())) {
					line.set_payment_status('waitingCancel');
					line.payment_method.payment_terminal.send_payment_cancel(this.currentOrder, cid).then(function() {
						self.currentOrder.remove_paymentline(line);
						NumberBuffer.reset();
						self.render();
					})
				}
				else if (line.get_payment_status() !== 'waitingCancel') {
					this.currentOrder.remove_paymentline(line);
					NumberBuffer.reset();
					this.render();
				}

				if(line.payment_method.is_igtf){
					// var due = this.env.pos.get_order().get_due();
					var total  = self.env.pos.company.igtf_percentage * 0.01 * line.amount;
					if (this.env.pos.get_order().get_igtf_charge() > 0){
						let igtf = this.env.pos.get_order().get_igtf_charge() - total
						if (igtf > 0){
							this.env.pos.get_order().set_igtf_charge(igtf);
						}else{
							this.env.pos.get_order().set_igtf_charge(0)
						}
					}else{
						this.env.pos.get_order().set_igtf_charge(0)
					}
				}
			}

			_updateSelectedPaymentline() {
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
					if(this.selectedPaymentLine.payment_method.is_igtf){
						var due = NumberBuffer.getFloat();
						let total = 0

						for (var i = 0; i < this.paymentLines.length; i++ ) {
							if (this.paymentLines[i].selected == false && this.paymentLines[i].payment_method.is_igtf){
								total  += this.env.pos.company.igtf_percentage * 0.01 * this.paymentLines[i].amount;
							}
						}
						// let	price_other_currency = due+total;
						total  += this.env.pos.company.igtf_percentage * 0.01 * due;
						this.env.pos.get_order().set_igtf_charge(total);
						this.selectedPaymentLine.set_amount(due);
					}else{
						this.selectedPaymentLine.set_amount(NumberBuffer.getFloat());
					}
				}
			}


		}
	Registries.Component.extend(PaymentScreen, IgtfPaymentScreen);
	return PaymentScreen;

});