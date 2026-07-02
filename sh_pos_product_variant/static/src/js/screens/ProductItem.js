odoo.define('sh_pos_product_variant.ProductItem', function (require) {
    'use strict';

    const ProductItem = require("point_of_sale.ProductItem");
    const Registries = require("point_of_sale.Registries");

    const { onMounted } = owl
    
    const PosProductItem = (ProductItem) =>
        class extends ProductItem {
            setup(){
                super.setup()
                onMounted(() => {
                    var self = this;
                    if (self.env.pos.config.sh_pos_enable_product_variants) {
                        var product = this.props.product
                        var variants = self.env.pos.db.has_variant(product.product_tmpl_id)
                        _.each($('.product'), function (each) {
                            if (product.id == each.dataset.productId && product.attribute_line_ids) {
                                if (product.attribute_line_ids.length > 0) {
                                    $(each).find('.price-tag').addClass('sh_has_variant');
                                    $(each).find('.price-tag').text(variants.length + ' variants');
                                }
                            }
                        })
                    }
                });
            }
        }

    Registries.Component.extend(ProductItem, PosProductItem);

})
