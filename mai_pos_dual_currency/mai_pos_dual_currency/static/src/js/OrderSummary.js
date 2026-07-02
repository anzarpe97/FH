odoo.define('mai_pos_dual_currency.OrderSummary', function (require) {
	'use strict';

	const OrderSummary = require('point_of_sale.OrderSummary');
	const Registries = require('point_of_sale.Registries');
	const { useState } = owl;
	
	const CurrencyOrderWidget = (OrderSummary) =>
		class extends OrderSummary {
			setup() {
				super.setup();
				this.total = 0; 
				this.tax = 0; 
				this.subtotal = 0;
				this.total_amt = 0;
				this.tax_amt = 0;
				this.total_currency_text = '';
				this.taxes_currency_text = '';
				this.total_currency = 0;
				this.taxes_currency = 0;
				this.subtotal_currency_text = '';
				this._updateSummary();
			}

			_updateSummary(){
				let self = this;
				let order = self.env.pos.get_order();
				if(order){
					let total = order.get_total_with_tax();
					let tax = order.get_total_with_tax() - order.get_total_without_tax() ;
					if(this.env.pos.config.show_dual_currency){
						let total_currency = 0;
						let taxes_currency = 0;
						let rate_company = parseFloat(this.env.pos.config.rate_company);
						let show_currency_rate = parseFloat(this.env.pos.config.show_currency_rate);
						
						total_currency =  show_currency_rate * total / rate_company;
						taxes_currency =  show_currency_rate * tax / rate_company; 

						let total_currency_text = '';
						let taxes_currency_text = '';
						if(this.env.pos.config.show_currency_position=='before'){
							total_currency_text = this.env.pos.config.show_currency_symbol+' '+total_currency.toFixed(2);
							taxes_currency_text = this.env.pos.config.show_currency_symbol+' '+taxes_currency.toFixed(2);
						}else{
							total_currency_text = total_currency.toFixed(2) +' '+this.env.pos.config.show_currency_symbol;
							taxes_currency_text = taxes_currency.toFixed(2) +' '+this.env.pos.config.show_currency_symbol;
						}

						this.total_currency = total_currency ;
						this.taxes_currency = taxes_currency ;

						this.total_amt = total ;
						this.tax_amt = tax ;
						this.subtotal = this.env.pos.format_currency(total-tax);

						this.total = this.env.pos.format_currency(total);
						this.total_currency_text = total_currency_text;
						this.tax = this.env.pos.format_currency(tax);
						this.taxes_currency_text = taxes_currency_text;
						this.subtotal_currency_text = this.env.pos.config.show_currency_symbol  +' '+ (total_currency-taxes_currency).toFixed(2);
					}else{
						this.total_amt = total ;
						this.tax_amt = tax ;
						this.subtotal = this.env.pos.format_currency(total-tax);
						this.total = this.env.pos.format_currency(total);
						this.tax = this.env.pos.format_currency(tax);
					}
				}
			}

			getSubtotal_currency_text(){
				this._updateSummary();
				return this.subtotal_currency_text;
			}

			getTaxes_currency_text(){
				return this.taxes_currency_text;
			}

			getTotal_currency_text(){
				return this.total_currency_text;
			}

			getSubtotal(){
				return this.subtotal;
			}

			getTax(){
				return this.tax;
			}

			getTotal(){
				return this.total;
			}



		}
	Registries.Component.extend(OrderSummary, CurrencyOrderWidget);

	return OrderSummary;
});



