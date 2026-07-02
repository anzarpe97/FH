odoo.define('sync_pos_combo_product.ComboApplyPopup', function (require) {
"use strict";

    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const _t = core._t;

    const { onMounted } = owl;

    class ComboApplyPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.product_price = this.props.product ? this.props.product.get_price(this.props.pricelists, 1): 0.0;
            this.combo_product = this.props.combo_product_info || [];
            onMounted(this.onMounted);
        }
        onMounted() {
            let self = this;
            if(this.props.call_to_edit) {
                let final_price = 0.0;
                let ext = 0.0;
                _.each(this.props.orderline.get_all_sub_product_selected_id(), function(id){
                    let $check_box = $(self.el).find('#' + id);
                    if(! self.env.pos.combo_products_by_id[Number(id.split('id')[1])].is_include_in_main_product_price) {
                        ext = parseFloat($check_box.attr('price')) + parseFloat(ext);
                        final_price = parseFloat(ext).toFixed(2);
                    }
                    let attribute = self.props.orderline.get_combo_product_attributes()[0][Number(id.split('id')[0])]['attributes'];
                    $check_box.attr("attributes", attribute)
                    $check_box.prop("checked", true);
                    $check_box.addClass('highlight_popup_combo');
                });
                let $extAmtDom = $(self.el).find('.extra_amount');
                if ($extAmtDom.length && final_price > 0) {
                    $extAmtDom.attr('data-price', final_price);
                    $extAmtDom.text(final_price);
                }
            }
        }
        getPayload() {
            let extra = 0.0;
            let $extAmtDom = $(this.el).find('.extra_amount');
            let check_req_product = false;
            let message_req_product = '';
            let i = 0;
            let combo_id_dict = {};
            let product_ids_req = _.map($("input[name='product']:checked"), function(value){
                return Number($(value).attr('id').split('id')[0]);
            });
            _.each(this.combo_product, function(combo_line) {
                if (combo_line.is_required_product) {
                    // Check required product if not selected then show error.
                    let filter_data = _.filter(product_ids_req, function(product_id){
                        return _.contains(combo_line['product_ids'], product_id);
                    });
                    combo_id_dict[combo_line.id] = {
                        'filter_id': filter_data,
                        'no_of_items': combo_line.no_of_items,
                        'category_name': combo_line.category_id[1] || 'Other',
                    };
                    if (combo_id_dict[combo_line.id].no_of_items > combo_id_dict[combo_line.id].filter_id.length) {
                        i += 1;
                        message_req_product += _t("\n[" + i + "] " + combo_id_dict[combo_line.id].category_name);
                        check_req_product = true;
                    };
                };
            });
            if (check_req_product) {
                return this.showPopup('ErrorPopup', {
                    title: _t('Oops! Failed to Select Products.'),
                    body: _t("Please select proper required products in this categories :- ") + message_req_product,
                });
                extra = -1;
            } else {
                if($extAmtDom) {
                    extra = Number($extAmtDom.attr('data-price'));
                }
            }
            return extra;
        }
    }
    ComboApplyPopup.template = 'ComboApplyPopup';
    Registries.Component.add(ComboApplyPopup);

    class ComboProduct extends PosComponent {
        setup(){
            super.setup();
            this.combo_product_info = this.props.product_info;
            this.pricelists = this.props.pricelists;
            this.product_id = this.props.product_id;
            this.extra_price = this.extra_price || 0.0;
        }
        async manage_req_combo_product({ detail: product_value }) {
            let self = this;
            self.manage_all_combo_products($("input[name='product']:checked"), product_value);
        }
        manage_un_req_combo_product({ detail: product_value }){
            let self = this;
            self.manage_all_combo_products($("input[name='un_req_products']:checked"), product_value);
        }
        manage_all_combo_products(all_product_checked, product_value) {
            let self = this;
            let combo_product_values = [];
            let $check_box = $('#' + product_value.product_id +'id'+product_value.combo_id);
            let combo_info = self.env.pos.combo_products_by_id[product_value.combo_id];
            let product = self.env.pos.db.get_product_by_id(product_value.product_id);
            let product_attribute_values = [];
            this.extra_price = 0.0;
            combo_product_values.push({'combo_ids': _.map(all_product_checked, function(value){
                return Number($(value).attr('id').split('id')[1]);
            })});
            if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id]).filter((attr) => attr !== undefined);
                product_attribute_values = _.map(_.map(attributes, function(attribute){
                    return  attribute['values'];
                }), function(data){
                    return ' ' + data[0]['name'];
                });
                $check_box.attr('attributes', product_attribute_values);
            }
            let selected_size = _.size(_.filter(combo_product_values[0]['combo_ids'], function(value) {
                return product_value.combo_id == value;
            }));
            let $extAmtDom = $('.extra_amount');
            if( combo_info.no_of_items >= selected_size ) {
                if($check_box.is(":checked")) {
                    $check_box.addClass("highlight_popup_combo");
                    if (combo_info && !combo_info.is_include_in_main_product_price) {
                        let product_price = parseFloat(product_value.price);
                        if ($extAmtDom.length) {
                            let ext = product_price + parseFloat($extAmtDom.attr('data-price'));
                            let final_price = parseFloat(ext).toFixed(2);
                            $extAmtDom.attr('data-price', final_price);
                            $extAmtDom.text(self.env.pos.format_currency(final_price));
                            self.extra_price = Number(final_price);
                        };
                    }
                } else {
                    $check_box.removeClass("highlight_popup_combo");
                    if (combo_info && !combo_info.is_include_in_main_product_price) {
                        let product_price = parseFloat(product_value.price);
                        if ($extAmtDom.length) {
                            let ext = parseFloat($extAmtDom.attr('data-price')) - product_price;
                            let final_price = parseFloat(ext).toFixed(2);
                            $extAmtDom.attr('data-price', final_price);
                            $extAmtDom.text(self.env.pos.format_currency(final_price));
                            self.extra_price = Number(final_price);
                        };
                    }
                }
            } else {
                $check_box.prop("checked", false);
                let $value = '';
                combo_product_values.push({'combo_ids': _.map(all_product_checked, function(value){
                    return Number($(value).attr('id').split('id')[1]);
                })});
            }
        }
    }

    class RequireProductAttribute extends ComboProduct {}
    RequireProductAttribute.template = 'RequireProductAttribute';
    Registries.Component.add(RequireProductAttribute);

    class UnRequireProductAttribute extends ComboProduct {}
    UnRequireProductAttribute.template = 'UnRequireProductAttribute';
    Registries.Component.add(UnRequireProductAttribute);

    return {
        ComboApplyPopup,
        RequireProductAttribute,
        UnRequireProductAttribute,
    }
});
