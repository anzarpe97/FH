odoo.define('ob_pos_customer_required.PaymentScreen', function(require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var _t = core._t;
    const {Gui} = require('point_of_sale.Gui');

    const PaymentPaymentRef = (PaymentScreen) => {
        class PaymentPaymentRef extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            async validateOrder(isForceValidate) {
                if (await this._isOrderValid(isForceValidate)) {
                    const order = this.currentOrder;
                    let call_super = true;
                    var flag = 0;
                    if (this.env.pos.config.customer_required && !order.partner) {
                    flag = flag + 1;
                    }
                    if (flag > 0) {
                        call_super = false;
                        Gui.showPopup('ErrorPopup', {
                            'title': _t('Se requiere el cliente'),
                            'body': _t('Por favor, selecciona un cliente para poder facturar el pedido'),
                        });
                    }
                    if (call_super) {
                        await super.validateOrder(...arguments);
                    }
                }
            }
        }
        return PaymentPaymentRef;
    };
    Registries.Component.extend(PaymentScreen, PaymentPaymentRef);

});