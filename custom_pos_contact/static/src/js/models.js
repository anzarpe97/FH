odoo.define('custom_pos_contact.models', function (require) {
    "use strict";
    
    var { Order, PosGlobalState, Payment, models } = require('point_of_sale.models');
    var Registries = require('point_of_sale.Registries');

    // Aquí va el código de la primera extensión (PosHomePosGlobalState)
    const PosHomePosGlobalState = (PosGlobalState) => class PosHomePosGlobalState extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.allcurrency = loadedData['allcurrency'];
        }
    }
    Registries.Model.extend(PosGlobalState, PosHomePosGlobalState);

    // Aquí va el código de la segunda extensión (CustomOrder)
    const CustomOrder = (Order) => class CustomOrder extends Order {
        export_for_printing() {
            var result = super.export_for_printing(...arguments);
            result.client = this.get_partner();
            return result;
        }
    }
    Registries.Model.extend(Order, CustomOrder);

    // Aquí va el código de la tercera extensión (PaymentLine)
    const PaymentLine = (Payment) => class PaymentLine extends Payment {
        constructor(obj, options) {
            super(...arguments);
            this.currency_symbol = this.currency_symbol || this.pos.currency.symbol;
        }

        set_currency_symbol(currency_symbol){
            this.currency_symbol = currency_symbol;
        }

        init_from_JSON(json){
            super.init_from_JSON(...arguments);
            this.currency_symbol = json.currency_symbol || this.pos.currency.symbol;
        }

        export_as_JSON(){
            const json = super.export_as_JSON(...arguments);
            json.currency_symbol = this.currency_symbol || this.pos.currency.symbol;
            return json;
        }

        export_for_printing() {
            const json = super.export_for_printing(...arguments);
            json.currency_symbol = this.currency_symbol || this.pos.currency.symbol;
            return json;
        }
    }

    Registries.Model.extend(Payment, PaymentLine);

});
