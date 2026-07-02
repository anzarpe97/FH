odoo.define("pos_customer_required.ProductScreen", function (require) {
    "use strict";

    const ProductScreen = require("point_of_sale.ProductScreen");
    const Registries = require("point_of_sale.Registries");
    const PartnerListScreen = require("point_of_sale.PartnerListScreen"); 
    const { useListener } = require("@web/core/utils/hooks");

    const { onMounted, onRendered ,onWillUnmount , onWillPatch , useState } = owl;

    const PosRequiredCustomerProductScreen = (ProductScreen) =>
        class extends ProductScreen {
          setup() {
            super.setup();
            onWillPatch((async) => {
                if (
                  this.env.pos.config.require_customer === "order" && 
                  !this.env.pos.get_order().get_partner()) {
                  this.onClickPartner();
                };
            
              });
            

          }

        };


  

    Registries.Component.extend(ProductScreen, PosRequiredCustomerProductScreen);

    return PosRequiredCustomerProductScreen;
});