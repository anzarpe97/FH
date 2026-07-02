odoo.define("pos_customer_required.PaymentScreen", function (require) {
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");
    const core = require("web.core");
    const _t = core._t;

    const PosRequiredCustomerPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async _isOrderValid(isForceValidate) {
                const order = this.env.pos.get_order();
                if (
                    this.env.pos.config.require_customer === "payment" &&
                    (!order.get_partner || !order.get_partner())
                ) {
                    const result = await this.showPopup("ConfirmPopup", {
                        title: _t("An anonymous order cannot be confirmed"),
                        body: _t("Please select a customer for this order."),
                    });
                    if (result.confirmed) {
                        this.selectClient();
                    }
                    return false;
                }
                return super._isOrderValid(isForceValidate);
            }
        };

    Registries.Component.extend(PaymentScreen, PosRequiredCustomerPaymentScreen);

    return PosRequiredCustomerPaymentScreen;
});