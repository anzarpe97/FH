odoo.define('mai_pos_invoice_autoprint_disable.models', function(require) {
	"use strict";

	var models = require('point_of_sale.models');
	var core = require('web.core');
	var rpc = require('web.rpc');
	var utils = require('web.utils');
	var _t = core._t;
	var pos_pricelist;
	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;

	var posmodel_super = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({

		push_and_invoice_order: function (order) {
			var self = this;
			var stop_invoice_print = self.config.stop_invoice_print;
			return new Promise((resolve, reject) => {
				if (!order.get_client()) {
					reject({ code: 400, message: 'Missing Customer', data: {} });
				} else {
					var order_id = self.db.add_order(order.export_as_JSON());
					self.flush_mutex.exec(async () => {
						try {
							const server_ids = await self._flush_orders([self.db.get_order(order_id)], {
								timeout: 30000,
								to_invoice: true,
							});
							if (server_ids.length) {
								if(stop_invoice_print){
									resolve(server_ids);
								}else{
									const [orderWithInvoice] = await self.rpc({
										method: 'read',
										model: 'pos.order',
										args: [server_ids, ['account_move']],
										kwargs: { load: false },
									});
									await self.do_action('account.account_invoices', {
										additional_context: {
											active_ids: [orderWithInvoice.account_move],
										},
									}).catch(() => {
										reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
									});
								}
							} else {
								reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
							}
							resolve(server_ids);
						} catch (error) {
							reject(error);
						}
					});
				}
			});
		},
		

	});
	
});
