odoo.define('pos_features_in_one.PosCustomerMandatory', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var _t = core._t;

    const PosPaymentScreen = PaymentScreen => class extends PaymentScreen {
        async validateOrder(isForceValidate) {
            var order = this.env.pos.get_order();
            if(this.env.pos.config.customer_required && !order.get_partner()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Customer Required'),
                    body: this.env._t('Please Choose customer before validating order!'),
                });
                return;
            }
            else {
                super.validateOrder(...arguments);
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosPaymentScreen);

    return PaymentScreen;
});
