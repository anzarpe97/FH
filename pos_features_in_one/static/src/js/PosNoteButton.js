odoo.define("pos_features_in_one.PosNoteButton", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require("point_of_sale.Registries");
    const ProductScreen = require("point_of_sale.ProductScreen");

    class PosNoteButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        onClick() {
        	let { confirmed, payload } = this.showPopup("PosOrderNoteWidget");
            if (confirmed) {
            } else {
                return;
            }
        }
    }
    PosNoteButton.template = "PosNoteButton";
    ProductScreen.addControlButton({
        component: PosNoteButton,
        condition: function () {
            return this.env.pos.config.pos_order_note;
        },
    });
    Registries.Component.add(PosNoteButton);
    return PosNoteButton
});
