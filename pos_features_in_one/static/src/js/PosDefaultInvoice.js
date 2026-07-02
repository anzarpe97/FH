odoo.define("pos_features_in_one.PosDefaultInvoice", function (require) {
    "use strict";

    const Registries = require("point_of_sale.Registries");
    const PaymentScreen = require("point_of_sale.PaymentScreen");

    const PosResPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
                if (this.env.pos.config.pos_default_invoice) {
                    this.currentOrder.set_to_invoice(true)
                }
            }
        };
    Registries.Component.extend(PaymentScreen, PosResPaymentScreen);
});