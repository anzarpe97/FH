odoo.define('pos_features_in_one.ButtonQuickyPay', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
//    const {useListener} = require('web.custom_hooks');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class ButtonQuickPay extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get isHighlighted() {
            return true
        }

        get getCount() {
            return this.count;
        }

        get selectedOrderline() {
            return this.env.pos.get_order().get_selected_orderline();
        }

        async onClick() {
            let selectedOrder = this.env.pos.get_order();
            if (selectedOrder.is_to_invoice() && !selectedOrder.get_partner()) {
                await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Order will process to Invoice, please select one Customer for set to current Order'),
                    disableCancelButton: true,
                })
                const {confirmed, payload: newPartner} = await this.showTempScreen(
                    'PartnerListScreen',
                    {partner: null}
                );
                if (confirmed) {
                    selectedOrder.set_partner(newPartner);
                } else {
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Order will processing to Invoice, required set a Customer')
                    })
                }
            }
            if (selectedOrder.get_total_with_tax() <= 0 || selectedOrder.orderlines.length == 0) {
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Error'),
                    body: this.env._t('It not possible with empty cart or Amount Total order smaller than or equal 0')
                })
            }
            let quickly_payment_method = this.env.pos.payment_methods.find(m => m.id == this.env.pos.config.quickly_payment_method_id[0])
            if (!quickly_payment_method) {
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Error'),
                    body: this.env._t('You POS Config active Quickly Paid but not set add Payment Method: ') + this.env.pos.config.quickly_payment_method_id[1] + this.env._t('Payments/ Payment Methods')
                })
            }
            let paymentLines = selectedOrder.paymentlines
            paymentLines.forEach(function (p) {
                selectedOrder.remove_paymentline(p)
            })
            selectedOrder.add_paymentline(quickly_payment_method);
            var paymentline = selectedOrder.selected_paymentline;
            paymentline.set_amount(selectedOrder.get_total_with_tax());
            let order_ids = this.env.pos.push_single_order(selectedOrder, {})
            console.log('{ButtonQuickPay.js} pushed succeed order_ids: ' + order_ids)
            const iface_print_auto = this.env.pos.config.iface_print_auto;
            this.env.pos.config.iface_print_auto = true
            this.showScreen('ReceiptScreen');
            this.env.pos.config.iface_print_auto = iface_print_auto
        }
    }

    ButtonQuickPay.template = 'ButtonQuickPay';

    ProductScreen.addControlButton({
        component: ButtonQuickPay,
        condition: function () {
            return this.env.pos.config.quickly_payment_full;
        },
    });

    Registries.Component.add(ButtonQuickPay);

    return ButtonQuickPay;
});
