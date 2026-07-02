odoo.define("pos_features_in_one.PosReceiptLogo", function (require) {
    "use strict";

    var { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosLogo = (Order) => class PosLogo extends Order {
        export_for_printing() {
            var receipt = super.export_for_printing(...arguments);
            receipt.receipt_logo_url = "/web/image?model=pos.config&amp;field=header_logo&amp;id= " + this.pos.config.id
            return receipt;
        }
    }

    Registries.Model.extend(Order, PosLogo);
})
