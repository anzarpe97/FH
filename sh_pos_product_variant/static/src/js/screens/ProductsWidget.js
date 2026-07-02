odoo.define('sh_pos_product_variant.ProductsWidget', function (require) {
    'use strict';

    const ProductsWidget = require("point_of_sale.ProductsWidget");
    const Registries = require("point_of_sale.Registries");

    const PosProductsWidget = (ProductsWidget) =>
        class extends ProductsWidget {
            setup() {
                super.setup()
            }
            _switchCategory(event) {
                var self = this;
                this.env.pos.db.sh_show_total_products = []
                super._switchCategory(event)
            }
            get productsToDisplay() {
                var self = this;
                var products = []
                var tmpl_ids = []
                let list = [];
                if (this.searchWord !== '') {
                    list = this.env.pos.db.search_product_in_category(
                        this.selectedCategoryId,
                        this.searchWord
                    );
                    if (self.env.pos.config.sh_pos_enable_product_variants) {
                        _.each(list, function (each_product, i) {
                            if (each_product.attribute_line_ids.length > 0) {
                                if (!tmpl_ids.includes(each_product.product_tmpl_id)) {
                                    products.push(each_product)
                                }
                                tmpl_ids.push(each_product.product_tmpl_id)
                            } else {
                                products.push(each_product)
                            }

                        })
                        return products
                    }else{

                        return list
                    }
                } else {
                    if (self.env.pos.config.sh_pos_enable_product_variants) {
                        if (this.env.pos.db.sh_show_total_products && this.env.pos.db.sh_show_total_products.length > 0){
                            var Products = this.env.pos.db.sh_show_total_products
                        }else{
                            var Products = this.env.pos.db.get_sh_product_by_category(this.selectedCategoryId);
                            this.env.pos.db.sh_show_total_products = Products.slice(0, 100)
                        }
                        return Products.slice(0, 100).sort(function (a, b) { return a.display_name.localeCompare(b.display_name) });
                    }else{
                        list = this.env.pos.db.get_product_by_category(this.selectedCategoryId);

                        return list.sort(function (a, b) { return a.display_name.localeCompare(b.display_name) });
                    }
                    
                }
            }

        }

    Registries.Component.extend(ProductsWidget, PosProductsWidget);


});
