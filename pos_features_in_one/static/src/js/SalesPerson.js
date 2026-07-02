odoo.define('pos_features_in_one.Salesperson', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class SalespersonButton extends PosComponent {
        setup() {
           super.setup();
           useListener('click', this.onClick);
        }
        async onClick() {
            this.showPopup('SalespersonPopup', {
                title: this.env._t('Select Salesperson'),
                type: 'order',
            });
        }
    }
    SalespersonButton.template = 'SalespersonButton';
    ProductScreen.addControlButton({
        component: SalespersonButton,
        condition: function() {
            return this.env.pos.config.pos_allow_salesperson;;
        },
    });
    Registries.Component.add(SalespersonButton);
    return SalespersonButton;
});
