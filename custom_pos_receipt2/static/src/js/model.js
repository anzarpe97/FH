odoo.define('custom_pos_receipt.model', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var OrderlineSuper = models.Orderline;
    models.Orderline = models.Orderline.extend({
        export_for_printing: function () {
            var data = OrderlineSuper.prototype.export_for_printing.apply(this, arguments);
            data.product_default_code = this.get_product().default_code;
            return data;
        }
    });
});