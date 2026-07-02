odoo.define('pos_feature_in_one.PosSyncOrder', function(require) {
'use strict';
  const PosComponent = require('point_of_sale.PosComponent');
  const { useListener } = require("@web/core/utils/hooks");
  const Registries = require('point_of_sale.Registries');
  class PosSyncOrder extends PosComponent {
      setup() {
          super.setup();
          useListener('click', this.onClick);
      }
      async onClick() {
           const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: ('Sync All'),
                body:('Are You Want to Sync all confirmed orders?'),
                });
                if (confirmed){
                     await this.env.pos.push_orders();
                }
           }
      }
  PosSyncOrder.template = 'PosSyncOrder';
  Registries.Component.add(PosSyncOrder);
  return PosSyncOrder;
});