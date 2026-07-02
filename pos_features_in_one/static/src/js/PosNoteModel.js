odoo.define("pos_features_in_one.PosNoteModel", function (require) {
    "use strict";

    const {Order} = require('point_of_sale.models');
    const Registries = require("point_of_sale.Registries");

    const PosOrderNote = (Order) => class PosOrderNote extends Order {
        constructor() {
            super(...arguments);
            this.order_note = false;
        }
        set_order_order_note(order_note){
        	this.order_note = order_note
        }
        get_order_order_note(){
        	return this.order_note;
        }
        export_as_JSON() {
            var json = super.export_as_JSON()
            json.order_note = this.get_order_order_note() || null;

            return json;
        }
        export_for_printing() {
            var self = this;
            var orders = super.export_for_printing()
            var new_val = {
            	order_note: this.get_order_order_note() || false,
            };
            $.extend(orders, new_val);
            return orders;
        }
    };
    Registries.Model.extend(Order, PosOrderNote);

});
