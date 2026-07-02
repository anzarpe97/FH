odoo.define("pos_customer_required.ReceiptScreen", function (require) {
    "use strict";


    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require("point_of_sale.Registries");
    const { onMounted, onRendered ,onWillUnmount , onWillPatch , useState } = owl;

    const PosRequiredCustomerReceiptScreen= (ReceiptScreen) =>
        class  extends ReceiptScreen {

            setup() {
                super.setup();
            }


            //@override
            async orderDone() {
                this.env.pos.removeOrder(this.currentOrder);
                this._addNewOrder();
                if (this.env.pos.config.require_customer === "order"){
                        const currentPartner = this.env.pos.get_order().get_partner() ;
                        const { confirmed, payload: newPartner } = await this.showTempScreen(
                            'PartnerListScreen',
                            { partner: currentPartner}
                        );
                        if (confirmed) {
                            this.env.pos.get_order().set_partner(newPartner);
                            this.env.pos.get_order().updatePricelist(newPartner);
                            const { name, props } = this.nextScreen;
                            this.showScreen(name, props);
                        };
                }else{
                    //Comportamiento nativo de odoo 
                    const { name, props } = this.nextScreen;
                    this.showScreen(name, props)
                    if (this.env.pos.config.iface_customer_facing_display) {
                        this.env.pos.send_current_order_to_customer_facing_display();
                    }

                }
               

            }
    };
    
    Registries.Component.extend(ReceiptScreen, PosRequiredCustomerReceiptScreen);
   
    return ReceiptScreen;
});