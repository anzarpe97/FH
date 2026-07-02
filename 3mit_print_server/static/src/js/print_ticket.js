odoo.define("3mit_print_server.print_ticket", function (require) {
	"use strict";
  
	const ReceiptScreen = require("point_of_sale.ReceiptScreen");
	const PaymentScreen = require("point_of_sale.PaymentScreen");
	const Registries = require("point_of_sale.Registries");
	var { Order, Orderline, PosGlobalState } = require('point_of_sale.models');
	const core = require("web.core");
	const _t = core._t;
  
	const POSOrderMit = (PosGlobalState) => class POSOrderMit extends PosGlobalState {
	  async _processData(loadedData) {
		await super._processData(...arguments);
		this.pos_order = loadedData['pos_order'] || [];
	  }
	}
  
	Registries.Model.extend(PosGlobalState, POSOrderMit);
  
	var utils = require("web.utils");
	var round_di = utils.round_decimals;
	var round_pr = utils.round_precision;
  
	var fixMoney = (window.fixMoney = function fixMoney(n) {
	  return Math.round(n * 100) / 100;
	});
  
	const ExtendReceiptScreen = (ReceiptScreen) =>
	  class extends ReceiptScreen {
		mounted() {
		  super.mounted(...arguments);
		  $(".button.next", this.el).hide();
		}
  
		_shouldCloseImmediately() {
		  const ret = super._shouldCloseImmediately();
		  if (ret != undefined) {
			return ret;
		  }
		  var invoiced_finalized = this.currentOrder.is_to_invoice()
			? this.currentOrder.finalized
			: true;
		  return (
			this.env.pos.config.iface_print_skip_screen && invoiced_finalized
		  );
		}
  
		// Devuelve data reportada por la impresora
		async print_3mit(order) {
		  const json = this._3mit_prepare_json(order);
		  const printer_host = this.env.pos.config.printer_host;
  
		  try {
			const rs = await $.post({
			  url: `http://${printer_host}/api/imprimir/factura`,
			  data: JSON.stringify(json),
			  contentType: "application/json",
			  dataType: "json",
			  timeout: 40000, //20 segundos para imprimir
			});
			console.log("3mit_send_to_printer:", rs);
			if (rs.status == "OK") {
			  return rs.data;
			} else {
			  return rs.status + ":" + rs.message;
			}
		  } catch (err) {
			await this.showPopup("ErrorPopup", {
			  title: "Ticket Fiscal",
			  body: err.statusText,
			});
			console.log("3mit_send_to_printer: Error", err);
			return err.statusText;
		  }
		}
  
		_3mit_prepare_json(order) {
		  var json = order.export_for_printing();
		  if (!json.client) json.client = {};
		  var receipt = {
			backendRef: json.name || null,
			idFiscal: json.client.vat ||
			  json.client.identification_id ||
			  null,
			razonSocial: json.client.name || null,
			direccion: json.client.street || null,
			telefono: json.client.phone || null,
		  };
		  receipt.items = json.orderlines.map((r) => {
			return {
			  nombre: r.product_name,
			  cantidad: r.quantity,
			  precio: r.price * order.rate_order,
			  impuesto: r.iva_rate,
			  descuento: r.discount,
			  tipoDescuento: "p",
			};
		  });
  
		  const bi_igtf = order.bi_igtf || 0;
		  receipt.pagos = [];
		  const pagos = json.paymentlines.map((r) => {
			return {
			  codigo: r.fiscal_print_code || (r.dolar_active ? "20" : "01"),
			  nombre: r.fiscal_print_name || r.payment_method,
			  monto: fixMoney(r.amount * order.rate_order),
			};
		  });
		  pagos.forEach((r) => {
			const p = receipt.pagos.find((f) => f.codigo == r.codigo);
			if (!p) {
			  receipt.pagos.push(r);
			} else {
			  p.monto += r.monto;
			}
		  });
  
		  return receipt;
		}
  
		async handleAutoPrint() {
		  if (this._shouldAutoPrint()) {
			await this.printReceipt();
			if (this.currentOrder._printed && this._shouldCloseImmediately()) {
			  this.orderDone();
			}
		  }
		}
  
		async printNewButtonFiscal() {
		  const bfiscal = await this.validate_3mitServer();
		  if (!bfiscal) {
			return;
		  }
  
		  $(".button.next", this.el).hide();
  
		  const isPrinted = await this._printNewButtonFiscal();
  
		  if (isPrinted) {
			this.currentOrder._printed_fiscal = true;
			$(".button.next", this.el).show();
		  } else {
			$(".button.next", this.el).hide();
		  }
		}
  
		async _printNewButtonFiscal() {
		  const order = this.currentOrder;
  
		  if (order._printed_fiscal) {
			await this.showPopup("ErrorPopup", {
			  title: "Ticket Fiscal",
			  body: "El ticket ya fue enviado a la impresora.",
			});
			return true;
		  }
  
		  var json = order.export_for_printing();
		  var rate_order = await this.rpc({
			model: "pos.order",
			method: "get_rate_order",
			args: [false, json.name]
		  });
		  order.rate_order = rate_order
		  const dataFiscal = await this.print_3mit(order);
  
		  if (!dataFiscal || !dataFiscal.nroFiscal) {
			await this.showPopup("ErrorPopup", {
			  title: "Error imprimiendo",
			  body: "Revise la impresora y reintente imprimir para continuar\n\n" + dataFiscal,
			});
			return false;
		  }
		  order._printed_fiscal = true;
  
		  try {
			await this.rpc({
			  model: "pos.order",
			  method: "setTicket",
			  args: [
				false,
				{
				  orderUID: order.uid,
				  nroFiscal: dataFiscal.nroFiscal,
				  fecha: dataFiscal.fecha,
				  serial: dataFiscal.serial,
				},
			  ],
			});
		  } catch (err) {
			await this.showPopup("ErrorPopup", {
			  title: "Error de backend",
			  body: "No se pudo guardar la información fiscal",
			});
		  } finally {
			return true;
		  }
		}
  
		async validate_3mitServer() {
		  return true; // Omitiendo la validación del servidor de impresión
		}
	  };
  
	Registries.Component.extend(ReceiptScreen, ExtendReceiptScreen);
  
	const ExtendPaymentScreen = (PaymentScreen) =>
	  class extends PaymentScreen {
		async _isOrderValid(isForceValidate) {
		  const ret = await super._isOrderValid(isForceValidate);
		  const isPrintServerOnline = await this.validate_3mitServer();
  
		  this.currentOrder.ticket_fiscal = null;
		  this.to_invoice = true;
  
		  return ret && isPrintServerOnline;
		}
  
		validate_3mitServer() {
		  return true; // Omitiendo la validación del servidor de impresión
		}
	  };
  
	Registries.Component.extend(PaymentScreen, ExtendPaymentScreen);
  
	const MitCustomOrder = (Order) => class MitCustomOrder extends Order {
	  constructor(obj, options) {
		super(...arguments);
		this.ticket_fiscal = null;
		this.serial_fiscal = null;
		this.fecha_fiscal = null;
	  }
  
	  init_from_JSON(json) {
		this.ticket_fiscal = json.ticket_fiscal;
		this.serial_fiscal = json.serial_fiscal;
		this.fecha_fiscal = json.fecha_fiscal;
		super.init_from_JSON(...arguments);
	  }
  
	  export_as_JSON() {
		var data = super.export_as_JSON(...arguments);
		data.ticket_fiscal = this.ticket_fiscal;
		data.serial_fiscal = this.serial_fiscal;
		data.fecha_fiscal = this.fecha_fiscal;
		return data;
	  }
  
	  export_for_printing() {
		var receipt = super.export_for_printing(...arguments);
		receipt.client = this.get_partner();
		return receipt;
	  }
	};
  
	Registries.Model.extend(Order, MitCustomOrder);
  
	const CustomOrderLine = (Orderline) => class CustomOrderLine extends Orderline {
	  export_for_printing() {
		var line = super.export_for_printing(...arguments);
		var taxes = this.get_taxes();
		if (taxes.length === 0) {
		  line.iva_rate = 0;
		} else {
		  line.iva_rate = taxes[0].amount;
		}
		return line;
	  }
	};
  
	Registries.Model.extend(Orderline, CustomOrderLine);
  });
  