odoo.define('sh_pos_product_variant.db', function (require) {
    'use strict';

    var DB = require('point_of_sale.DB');
    var utils = require('web.utils');

    DB.include({
        init: function (options) {
            this._super.apply(this, arguments);
            this.product_temlate_attribute_line_by_id = {};
            this.product_temlate_attribute_by_id = {};
            this.sh_show_total_products = [];
            this.product_tmpl_by_id = {}
        },
        has_variant: function (id) {
            var tmpls = []
            _.each(this.product_by_id, function (each_product) {
                if (each_product.product_tmpl_id == id && each_product.active) {
                    tmpls.push(each_product)
                }
            })
            if (tmpls.length > 1) {
                return tmpls
            } else {
                return false
            }
        },
        add_products: function(products){
            this._super(products);
            var self = this;
            
            for(var i = 0, len = products.length; i < len; i++){
                var each_product = products[i];
                if (self.product_tmpl_by_id[each_product.product_tmpl_id] && each_product.attribute_line_ids.length > 0) {
                    if (self.product_tmpl_by_id[each_product.product_tmpl_id] && !self.product_tmpl_by_id[each_product.product_tmpl_id].includes(each_product.id)) {
                        self.product_tmpl_by_id[each_product.product_tmpl_id].push(each_product.id)
                    }
                } else {
                    if (each_product.attribute_line_ids.length > 0) {
                        self.product_tmpl_by_id[each_product.product_tmpl_id] = [each_product.id]
                    }
                }
            }
        },
        get_sh_product_by_category: function(category_id){
            var product_ids  = this.product_by_category_id[category_id];
            var list = [];
            if (product_ids) {
                if (category_id == 0){
                    var sh_product_count = 0
                    var tmpl_ids = []
                    for (var i = 0, len = Math.min(product_ids.length, 500); i < len; i++) {
                        const product = this.product_by_id[product_ids[i]];
                        if (!(product.active && product.available_in_pos)) continue;
                        var total_product = this.product_tmpl_by_id[product.product_tmpl_id]
                        if (total_product && total_product.includes(product.id)){
                            if (!tmpl_ids.includes(product.product_tmpl_id)) {
                                list.push(product);
                                tmpl_ids.push(product.product_tmpl_id)
                            }
                            sh_product_count = 1
                        }else{
                            sh_product_count = 0
                            if (!tmpl_ids.includes(product.product_tmpl_id)) {
                                list.push(product);
                            }
                            tmpl_ids.push(product.product_tmpl_id)
                        }    
                    }
                }else{
                    var sh_product_count = 0
                    var tmpl_ids = []
                    var product_length = 0;
                    if (product_ids && product_ids.length > 2000 ){
                        product_length = 2000
                    }else{
                        product_length = product_ids.length
                    }
                    for (var i = 0, len = Math.min(product_ids.length, product_length); i < len; i++) {
                        const product = this.product_by_id[product_ids[i]];
                        if (!(product.active && product.available_in_pos)) continue;
                        var total_product = this.product_tmpl_by_id[product.product_tmpl_id]
                        if (total_product && total_product.includes(product.id)){
                            if (!tmpl_ids.includes(product.product_tmpl_id)) {
                                list.push(product);
                                tmpl_ids.push(product.product_tmpl_id)
                            }
                            sh_product_count = 1
                        }else{
                            sh_product_count = 0
                            if (!tmpl_ids.includes(product.product_tmpl_id)) {
                                list.push(product);
                            }
                            tmpl_ids.push(product.product_tmpl_id)
                        }    
                    }
                }
            }
            return list;
        },
        search_variants: function (variants, query) {
            var self = this;
            this.variant_search_string = ""
            for (var i = 0; i < variants.length; i++) {
                var variant = variants[i]
                var search_variant = utils.unaccent(self.variant_product_search_string(variant))
                self.variant_search_string += search_variant
            }
            try {
                query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
                query = query.replace(/ /g, '.+');
                var re = RegExp("([0-9]+):.*?" + utils.unaccent(query), "gi");
            } catch (e) {
                return [];
            }

            var results = [];
            for (var i = 0; i < this.limit; i++) {
                var pariant_pro = re.exec(this.variant_search_string)
                if (pariant_pro) {
                    var id = Number(pariant_pro[1]);
                    var product_var = this.get_product_by_id(id)

                    results.push(product_var)

                } else {
                    break;
                }
            }
            return results;
        },
        variant_product_search_string: function (product) {

            var str = product.display_name;
            if (product.id) {
                str += '|' + product.id;
            }
            if (product.default_code) {
                str += '|' + product.default_code;
            }
            if (product.description) {
                str += '|' + product.description;
            }
            if (product.description_sale) {
                str += '|' + product.description_sale;
            }
            str = product.id + ':' + str.replace(/:/g, '') + '\n';
            return str;
        }
    })

})
