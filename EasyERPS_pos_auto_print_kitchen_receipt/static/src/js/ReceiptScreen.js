odoo.define('EasyERPS_pos_auto_print_kitchen_receipt.ReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const customReceiptScreen = ReceiptScreen => class extends ReceiptScreen {

        // Sobreescribimos el método para evitar que se imprima cuando se use otro botón
        async _printKitchenReceipt() {
            // Deshabilitar la impresión del "Kitchen Receipt"
            console.log("Comandar/Imprimir pedido ha sido deshabilitado.");
            return;  // No realizar ninguna acción
        }

        async printReceipt() {
            var order = this.env.pos.get_order();
            const isPrinted = await this._printReceipt();
            if (isPrinted) {
                order.printChanges();
                order._printed = true;  // Odoo 16 usa _ para indicar variables internas
            }
        }
    };

    Registries.Component.extend(ReceiptScreen, customReceiptScreen);

    return ReceiptScreen;
});
