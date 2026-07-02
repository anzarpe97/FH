odoo.define('sync_pos_combo_product.ProductScreen', function (require) {
"use strict";

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Orderline = require('point_of_sale.Orderline')
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const _t = core._t;

    const PosComboProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            async _clickProduct(event) {
                const product = event.detail;
                let price_extra = 0.0;
                let draftPackLotLines, weight, description, packLotLinesToEdit;
                let self = this;
                const pos = self.env.pos;
                if (!this.currentOrder) {
                    this.env.pos.add_new_order();
                }
                const order = this.currentOrder;

                if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                    let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                      .filter((attr) => attr !== undefined);
                    let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                        product: product,
                        attributes: attributes,
                    });

                    if (confirmed) {
                        description = payload.selected_attributes.join(', ');
                        price_extra += payload.price_extra;
                    } else {
                        return;
                    }
                }

                // Gather lot information if required.
                if (['serial', 'lot'].includes(product.tracking)) {
                    const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                    if (isAllowOnlyOneLot) {
                        packLotLinesToEdit = [];
                    } else {
                        const orderline = this.currentOrder
                            .get_orderlines()
                            .filter(line => !line.get_discount())
                            .find(line => line.product.id === product.id);
                        if (orderline) {
                            packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                        } else {
                            packLotLinesToEdit = [];
                        }
                    }
                    const { confirmed, payload } = await this.showPopup('EditListPopup', {
                        title: this.env._t('Lot/Serial Number(s) Required'),
                        isSingleItem: isAllowOnlyOneLot,
                        array: packLotLinesToEdit,
                    });
                    if (confirmed) {
                        // Segregate the old and new packlot lines
                        const modifiedPackLotLines = Object.fromEntries(
                            payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                        );
                        const newPackLotLines = payload.newArray
                            .filter(item => !item.id)
                            .map(item => ({ lot_name: item.text }));

                        draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                    } else {
                        // We don't proceed on adding product.
                        return;
                    }
                }

                // Take the weight if necessary.
                if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                    // Show the ScaleScreen to weigh the product.
                    if (this.isScaleAvailable) {
                        const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                            product,
                        });
                        if (confirmed) {
                            weight = payload.weight;
                        } else {
                            // do not add the product;
                            return;
                        }
                    } else {
                        await this._onScaleNotAvailable();
                    }
                }

                // Add the product after having the extra information.
                // COMBO PRODUCT CODE
                let combo_product = _.filter(pos.combo, function(value){
                    return order && value.product_template_id[0] === product.product_tmpl_id;
                });
                if (product.is_combo && !_.isEmpty(combo_product)) {
                    let category_id_list = [];
                    _.each(_.map(combo_product, 'category_id'), function(category_id){
                        category_id_list.push(category_id[0]);
                    });
                    // in this list get filtered data category wise & show in combo popup xml
                    let filter_combo_list = [];
                    _.each(_.uniq(category_id_list), function(category){
                        let filter_combo_data = order.get_product_data(category, product.product_tmpl_id);
                        filter_combo_list.push(filter_combo_data);
                    });
                    let set_unreq_product = [];
                    let set_req_products = [];
                    const { confirmed, payload } = await this.showPopup('ComboApplyPopup', {
                        pricelists: order.pricelist,
                        product: product,
                        combo_product_info: combo_product,
                        filter_combo_list: filter_combo_list,
                        call_to_edit: false,
                    });
                    if (confirmed) {
                        if(payload >= 0) {
                            price_extra += Number(payload);
                            order.add_product(product, {
                                draftPackLotLines,
                                description: description,
                                price_extra: price_extra,
                                quantity: weight,
                            });
                            let orderline = order.get_selected_orderline();
                            let checked_req_dom = $("input[name='product']:checked");
                            let checked_un_req_dom = $("input[name='un_req_products']:checked")
                            order.manage_combo_products_selected(checked_req_dom, checked_un_req_dom);
                            orderline.set_extra_price_combo(Number(payload));
                            orderline.price_manually_set = true;
                            NumberBuffer.reset();
                        } else {
                            return ;
                        }
                    } else {
                        return ;
                    }
                } else {
                    await super._clickProduct(event);
                }
            }
        }

    Registries.Component.extend(ProductScreen, PosComboProductScreen);

    const PosComboOrderline = (Orderline) =>
        class extends Orderline {
            constructor() {
                super(...arguments);
            }
            async manage_edit_combo_popup({ detail: orderline}) {
                let order = this.env.pos.get_order();
                let category_id_list = [];
                let combo_product = _.filter(this.env.pos.combo, function(value){
                    return orderline.is_combo_line && value.product_template_id[0] === orderline.get_product().product_tmpl_id;
                });
                if(!_.isEmpty(combo_product)) {
                    _.each(_.map(combo_product, 'category_id'), function(category_id){
                        category_id_list.push(category_id[0]);
                    });
                    let filter_combo_list = [];
                    _.each(_.uniq(category_id_list), function(category){
                        let filter_combo_data = order.get_product_data(category, orderline.get_product().product_tmpl_id);
                        filter_combo_list.push(filter_combo_data);
                    });
                    const { confirmed, payload } = await this.showPopup('ComboApplyPopup', {
                        pricelists: order.pricelist,
                        product: orderline.get_product(),
                        combo_product_info: combo_product,
                        filter_combo_list: filter_combo_list,
                        call_to_edit: true,
                        orderline: orderline,
                    });
                    if (confirmed) {
                        if(payload >= 0) {
                            let checked_req_dom = $("input[name='product']:checked");
                            let checked_un_req_dom = $("input[name='un_req_products']:checked")
                            let orderline = order.get_selected_orderline();
                            order.manage_combo_products_selected(checked_req_dom, checked_un_req_dom);
                            if(payload > 0) {
                                orderline.set_unit_price((orderline.get_product().get_price(order.pricelist, orderline.get_quantity()) + payload));
                                orderline.set_extra_price_combo(payload);
                            } else {
                                orderline.set_unit_price((orderline.get_product().get_price(order.pricelist, orderline.get_quantity()) + Number(payload)));
                            }
                        }
                    }
                }
            }
        }
    Registries.Component.extend(Orderline, PosComboOrderline);
    return [ProductScreen, Orderline];
});
