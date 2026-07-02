
odoo.define('mai_pos_igtf_de_venezuela.PaymentScreenStatusExtended', function(require){
	'use strict';

	const PaymentScreenStatus = require('point_of_sale.PaymentScreenStatus');
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const { Component } = owl;

	const PaymentScreenStatusExtended = (PaymentScreenStatus) =>
		class extends PaymentScreenStatus {
			
			get total_with_igtf(){
				let order = this.env.pos.get_order();
				let igtf_charge = order.get_igtf_charge();
				let total = igtf_charge + order.get_total_with_tax() ;
				return total;
			}

			get remainingText() {
				let order = this.env.pos.get_order();
	            return this.env.pos.format_currency(
	                order.get_due() > 0 ? order.get_due() + order.get_igtf_charge() : 0
	            );
	        }

	};

	Registries.Component.extend(PaymentScreenStatus, PaymentScreenStatusExtended);

	return PaymentScreenStatus;

});