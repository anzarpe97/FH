odoo.define('sh_pos_product_variant.variant_pos', function (require, factory) {
    'use strict';

    const Registries = require("point_of_sale.Registries");
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const { useListener } = require("@web/core/utils/hooks");
     const { onMounted, useState } = owl 

    class variantPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup()
            useListener('click-product', this._clickProduct1);
            useListener('custom-update-search', this._updatepopupSearch);
            this.state = useState({ searchWord: '' });
            this.productFilter = []
            onMounted(() => {
                if (this.env.pos.config.sh_pos_variants_group_by_attribute && !this.env.pos.config.sh_pos_display_alternative_products) {
                    $('.main').addClass('sh_product_attr_no_alternative')
                     $('.sh_product_variants_popup').addClass('sh_attr_no_alternative_popup')
                }
                if (this.Attribute_names && this.Attribute_names.length > 0 && this.AlternativeProducts && this.AlternativeProducts < 1) {
                    $('.main').addClass('sh_only_attributes')
                }
             })
        }
        _updatepopupSearch(event){
            this.state.searchWord = event.detail;
        }
        get searchWord(){
            return this.state.searchWord.trim();
        }
        updateSearch(event) {
            var val = event.target.value || ""
            var searched = this.env.pos.db.search_variants(this.props.product_variants, val);
            if (searched && searched.length > 0 ){
                this.productFilter = searched
            }else{
                this.productFilter = []
            }
            this.render()
        }
        _clickProduct1(event) {
            var product = event.detail
            var currentOrder = this.env.pos.get_order()
            currentOrder.add_product(product)
            if (this.env.pos.config.sh_close_popup_after_single_selection) {
                this.cancel()
            }
        }
        cancel() {
            super.cancel()
        }
        Confirm() {
            var self = this
            var lst = []
            var currentOrder = this.env.pos.get_order()
            if ($('#attribute_value.highlight')) {
                _.each($('#attribute_value.highlight'), function (each) {
                    lst.push(parseInt($(each).attr('data-id')))
                })
            }
            _.each(self.env.pos.db.product_by_id, function (product) {
                if (product.product_template_attribute_value_ids.length > 0 && JSON.stringify(product.product_template_attribute_value_ids) === JSON.stringify(lst)) {
                    currentOrder.add_product(product)
                }
            })
            if (this.props.attributes_name.length > $('.highlight').length) {
                self.showPopup('ErrorPopup', {
                    title: 'Variants ! ',
                    body: 'Please Select Variant !'
                })
            } else {
                if (self.env.pos.config.sh_close_popup_after_single_selection) {
                    this.cancel()
                } else {
                    $('.sh_group_by_attribute').find('.highlight').removeClass('highlight')
                }
            }
        } 
        get VariantProductToDisplay() {
            if (this.productFilter  && this.productFilter.length > 0) {                
                return this.productFilter
            } else {
                return this.props.product_variants;
            }
        }
        get Attribute_names() {
            return this.props.attributes_name
        }
        get AlternativeProducts() {
            return this.props.alternative_products
        }
        Select_attribute_value(event) {

            _.each($('.' + $(event.currentTarget).attr('class')), function (each) {
                $(each).removeClass('highlight')
            })

            if ($('.sh_attribute_value').hasClass('highlight')) {
                $('.sh_attribute_value').removeClass('highlight')
            }
            if ($(event.currentTarget).hasClass('highlight')) {
                $(event.currentTarget).removeClass('highlight')

            } else {
                $(event.currentTarget).addClass('highlight')
            }
        }
    }
    variantPopup.template = "variantPopup";

    Registries.Component.add(variantPopup);

    return variantPopup
});
