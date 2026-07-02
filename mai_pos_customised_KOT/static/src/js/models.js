odoo.define('mai_pos_customised_KOT.models', function(require) {
	"use strict";

	const { PosGlobalState, Order, Orderline, Payment } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	var core = require('web.core');
	var QWeb = core.qweb;

	const PosRestaurantOrder = (Order) => class PosRestaurantOrder extends Order {
		constructor() {
			super(...arguments);
			this.printSequence = 0;
			this.lastPrintedDate = null;
		}
		async printChanges() {
			let isPrintSuccessful = true;
			let client = false;
			let cashier = this.pos.get_cashier().name;
			const d = new Date();
			let day = '' + d.getDate();
			day = day.length < 2 ? ('0' + day) : day;
			let month = '' + (d.getMonth() + 1);
			month = month.length < 2 ? ('0' + month) : month;
			let year = '' + d.getFullYear();
			year = year.length < 4 ? ('0' + year) : year;
			let hours = '' + d.getHours();
			hours = hours.length < 2 ? ('0' + hours) : hours;
			let minutes = '' + d.getMinutes();
			minutes = minutes.length < 2 ? ('0' + minutes) : minutes;
	
			if (this.get_partner()) {
				client = this.get_partner().name;
			} else {
				throw new Error('No se ha seleccionado un cliente. Por favor, seleccione un cliente para imprimir el recibo.');
			}
	
			for (const printer of this.pos.unwatched.printers) {
				const changes = this._getPrintingCategoriesChanges(printer.config.product_categories_ids);
				changes['client'] = client;
				changes['cashier'] = cashier;
				if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
					this.printSequence += 1; // Incrementa la secuencia
					this.lastPrintedDate = d; // Actualiza la fecha de impresión
	
					const printingChanges = {
						new: changes['new'],
						cancelled: changes['cancelled'],
						table_name: this.pos.config.iface_floorplan ? this.getTable().name : false,
						floor_name: this.pos.config.iface_floorplan ? this.getTable().floor.name : false,
						name: this.name || 'unknown order',
						time: {
							day,
							month,
							year,
							hours,
							minutes,
						},
						client: client,
						cashier: cashier,
						sequence: this.printSequence, // Agrega la secuencia al objeto de cambios
					};
	
					const receipt = QWeb.render('OrderChangeReceipt', { changes: printingChanges });
					const result = await printer.print_receipt(receipt);
					if (!result.successful) {
						isPrintSuccessful = false;
					}
				}
			}
			return isPrintSuccessful;
		}
	};
	
	Registries.Model.extend(Order, PosRestaurantOrder);

 
});
