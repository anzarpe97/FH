odoo.define('mai_pos_igtf_de_venezuela.pos', function(require) {
	"use strict";

	const { PosGlobalState, Order, Orderline, Payment } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	var utils = require('web.utils');
	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;

	const PosRestaurantOrder = (Order) => class PosRestaurantOrder extends Order {
		constructor(obj, options) {
			super(...arguments);
			this.igtf_charge = this.igtf_charge || 0;
			this.set_igtf_charge(this.igtf_charge);
		}
		
		set_igtf_charge(entered_charge){
			this.igtf_charge = entered_charge;
		}

		get_igtf_charge(){
			var self = this;
			return this.igtf_charge || 0;
		}

		get_change(paymentline) {
			if (!paymentline) {
				var change = this.get_total_paid() - (this.get_total_with_tax() + this.get_igtf_charge()) - this.get_rounding_applied();
			} else {
				var change = -(this.get_total_with_tax() + this.get_igtf_charge()); 
				var lines  = this.paymentlines.models;
				for (var i = 0; i < lines.length; i++) {
					change += lines[i].get_amount();
					if (lines[i] === paymentline) {
						break;
					}
				}
			}
			return round_pr(Math.max(0,change), this.pos.currency.rounding);
		}

		get_total_with_igtf() {
			return this.get_total_with_tax() + this.get_igtf_charge();
		}

		add_paymentline(payment_method) {
			this.assert_editable();
			if (this.electronic_payment_in_progress()) {
				return false;
			} else {
            	var newPaymentline = Payment.create({},{order: this, payment_method:payment_method, pos: this.pos});
				// var due = this.get_due()
				
				if(this.get_igtf_charge() > 0){
					if (this.get_due() == 0){
						due = this.get_igtf_charge()
					}else{
						if(payment_method.is_igtf == false){
							due = this.get_due() + this.get_igtf_charge()
						}else{
							due = this.get_due()
						}
					}
				}else{
					due = this.get_due()
				}

				newPaymentline.set_amount(due);
				this.paymentlines.add(newPaymentline);
				this.select_paymentline(newPaymentline);
				if(this.pos.config.cash_rounding){
				  this.selected_paymentline.set_amount(0);
				  this.selected_paymentline.set_amount(due);
				}

				if (payment_method.payment_terminal) {
					newPaymentline.set_payment_status('pending');
				}
				return newPaymentline;
			}
		}


		is_paid(){
	        return (this.get_due()+this.get_igtf_charge()).toFixed(2) <= 0 && this.check_paymentlines_rounding();
	    }

		export_as_JSON() {
			const json = super.export_as_JSON(...arguments);
			json.igtf_charge = this.get_igtf_charge() || 0;
			json.amount_total = this.get_igtf_charge() + this.get_total_with_tax();
			return json;
		}

		init_from_JSON(json) {
			super.init_from_JSON(...arguments);
			this.igtf_charge = json.igtf_charge || 0.0;
			this.amount_total = json.amount_total || 0.0;
		}

		export_for_printing() {
			const json = super.export_for_printing(...arguments);
			json.igtf_charge = this.get_igtf_charge() || 0;
			json.amount_total = this.get_igtf_charge() + this.get_total_with_tax();
			return json;
		}
		
	}
	Registries.Model.extend(Order, PosRestaurantOrder);


});
