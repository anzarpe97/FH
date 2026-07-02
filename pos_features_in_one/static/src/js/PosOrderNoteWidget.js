odoo.define("pos_features_in_one.PosOrderNoteWidget", function (require) {
    "use strict";

    const Registries = require("point_of_sale.Registries");
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");

    class PosOrderNoteWidget extends AbstractAwaitablePopup {
        async confirm() {
            var self = this;
            this.props.resolve({ confirmed: true, payload: await this.getPayload() });
            this.cancel()
            var value = $("#textarea_note").val();
            this.env.pos.get_order().set_order_order_note(value);
        }
    }

    PosOrderNoteWidget.template = "PosOrderNoteWidget";
    Registries.Component.add(PosOrderNoteWidget);

    return PosOrderNoteWidget
});
