odoo.define('pos_features_in_one.PosDefaultCustomer', function(require){
    'use strict';
    const { PosGlobalState, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var _t = core._t;

    const POSOderDefaultCuatomer = (Order) => class POSOderDefaultCuatomer extends Order {
        constructor(obj, options) {
            super(...arguments);
            if (this.pos.config.pos_customer_id) {
                var default_customer = this.pos.config.pos_customer_id[0];
                var partner = this.pos.db.get_partner_by_id(default_customer);
                this.set_partner(partner);
            }
        }
    }
    Registries.Model.extend(Order, POSOderDefaultCuatomer);
});