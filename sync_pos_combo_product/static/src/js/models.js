odoo.define('sync_pos_combo_product.models', function (require) {
    "use strict";

    const { PosGlobalState, Order, Orderline } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const { batched } = require('point_of_sale.utils');

    const PosComboProductPosGlobalState = (PosGlobalState) => class PosComboProductPosGlobalState extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            let new_var = JSON.parse(JSON.stringify(loadedData['product.combo']))
            this.combo = new_var
            this.combo_products_by_id = {}
            for (let i = 0; i < new_var.length; i++) {
                this.combo_products_by_id[new_var[i].id] = new_var[i];
            }
        }
       createReactiveOrder(json) {
            let reactiveOrder = super.createReactiveOrder(...arguments);
            if (this.config.module_pos_restaurant) {
                const updateOrderChanges = () => {
                    if (reactiveOrder.get_screen_data().name === 'ProductScreen') {
                        reactiveOrder.updateChangesToCombo();
                    }
                }
                reactiveOrder = owl.reactive(reactiveOrder, batched(updateOrderChanges));
                reactiveOrder.updateChangesToCombo();
            }
            return reactiveOrder;
        }
    }
    Registries.Model.extend(PosGlobalState, PosComboProductPosGlobalState);

    const PosRestaurantComboOrder = (Order) => class PosRestaurantcomboOrder extends Order {
        constructor(obj, options) {
            super(...arguments);
            if (this.pos.config.module_pos_restaurant) {
                this.comboResume = owl.markRaw(this.comboResume || {});
                if (!this.comboChanges) {
                    this._resetComboChanges();
                }
            }
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            if (this.pos.config.module_pos_restaurant) {
                json.combo_resume = JSON.stringify(this.comboResume);
                json.combo_changes = JSON.stringify(this.comboChanges);
            }
            return json;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            if (this.pos.config.module_pos_restaurant) {
                this.comboResume = json.combo_resume && JSON.parse(json.combo_resume);
                this.comboChanges = json.combo_changes && JSON.parse(json.combo_changes);
            }
        }
        _resetComboChanges() {
            this.comboChanges = { new:[], cancelled:[] };
        }
        _computeChanges() {
            const changes = {};

            // If there's a new orderline, we add it otherwise we add the change if there's one
            this.orderlines.forEach(line => {
                if (!line.mp_skip) {
                    const productId = line.get_product().id;
                    const note = line.get_note();
                    const productKey = `${productId} - ${line.get_full_product_name()} - ${note}`;
                    const lineKey = `${line.uuid} - ${note}`;
                    const quantityDiff = line.get_quantity() - (this.comboResume[lineKey] ? this.comboResume[lineKey]['quantity'] : 0);
                    if (quantityDiff) {
                        if (!changes[productKey]) {
                            changes[productKey] = {
                                product_id: productId,
                                name: line.get_full_product_name(),
                                note: note,
                                quantity: quantityDiff,
                                req_product_ids: line.req_product_ids || false,
                                unreq_product_ids: line.unreq_product_ids || false,
                                product_attributes_values: line.product_attributes_values || false,
                                is_combo_line: line.is_combo_line || false,
                            }
                        } else {
                            changes[productKey]['quantity'] += quantityDiff;
                        }
                        line.set_dirty(true);
                    } else {
                        line.set_dirty(false);
                    }
                }
            })

            // If there's an orderline that's not present anymore, we consider it as removed (even if note changed)
            for (const [lineKey, lineResume] of Object.entries(this.comboResume)) {
                if (!this._getComboLine(lineKey)) {
                    const productKey = `${lineResume['product_id']} - ${lineResume['name']} - ${lineResume['note']}`;
                    if (!changes[productKey]) {
                        changes[productKey] = {
                            product_id: lineResume['product_id'],
                            name: lineResume['name'],
                            note: lineResume['note'],
                            quantity: -lineResume['quantity'],
                            req_product_ids: lineResume['req_product_ids'],
                            unreq_product_ids: lineResume['unreq_product_ids'],
                            product_attributes_values: lineResume['product_attributes_values'],
                            is_combo_line: lineResume['is_combo_line'],
                        }
                    } else {
                        changes[productKey]['quantity'] -= lineResume['quantity'];
                    }
                }
            }

            return changes;
        }
        _getComboCategoriesChanges(categories) {
            return {
                new: this.comboChanges['new'].filter(change => this.pos.db.is_product_in_category(categories, change['product_id'])),
                cancelled: this.comboChanges['cancelled'].filter(change => this.pos.db.is_product_in_category(categories, change['product_id'])),
            }
        }
        _getComboLine(lineKey) {
            return this.orderlines.find(line => line.uuid === this.comboResume[lineKey]['line_uuid'] &&
                line.note === this.comboResume[lineKey]['note']);
        }
        updateComboResume(){
            // we first remove the removed orderlines
            for (const lineKey in this.comboResume) {
                if (!this._getComboLine(lineKey)) {
                    delete this.comboResume[lineKey];
                }
            }
            // we then update the added orderline or product quantity change
            this.orderlines.forEach(line => {
                if (!line.mp_skip) {
                    const note = line.get_note();
                    const lineKey = `${line.uuid} - ${note}`;
                    if (this.comboResume[lineKey]) {
                        this.comboResume[lineKey]['quantity'] = line.get_quantity();
                    } else {
                        this.comboResume[lineKey] = {
                            line_uuid: line.uuid,
                            product_id: line.get_product().id,
                            name: line.get_full_product_name(),
                            note: note,
                            quantity: line.get_quantity(),
                            req_product_ids: line.req_product_ids || false,
                            unreq_product_ids: line.unreq_product_ids || false,
                            product_attributes_values: line.product_attributes_values || false,
                            is_combo_line: line.is_combo_line || false,
                        }
                    }
                    line.set_dirty(false);
                }
            });
            this._resetComboChanges();
        }
        updateChangesToCombo() {
            const changes = this._computeChanges(); // it's possible to have a change's quantity of 0
            // we thoroughly parse the changes we just computed to properly separate them into two
            const toAdd = [];
            const toRemove = [];

            for (const lineChange of Object.values(changes)) {
                if (lineChange['quantity'] > 0) {
                    toAdd.push(lineChange);
                } else if (lineChange['quantity'] < 0) {
                    lineChange['quantity'] *= -1; // we change the sign because that's how it is
                    toRemove.push(lineChange);
                }
            }

            this.comboChanges = { new: toAdd, cancelled: toRemove };
        }

        manage_combo_products_selected(checked_req_dom, checked_un_req_dom) {
            let self = this;
            let product_ids_req = [];
            let product_ids_unreq = [];
            let product_attribute_ids = {};
            let product_attributes_values = [];
            let order = self.pos.get_order();
            let orderline = order.get_selected_orderline();
            product_ids_req = _.map(checked_req_dom, function(value){
                return $(value).attr('id');
            });
            product_ids_unreq = _.map(checked_un_req_dom, function(value){
                return $(value).attr('id');
            });
            _.each(checked_req_dom, function(value) {
                let full_name = self.pos.db.get_product_by_id(Number($(value).attr('id').split('id')[0])).display_name;
                if($(value).attr('attributes')) {
                    product_attribute_ids[$(value).attr('id').split('id')[0]] = {'attributes': $(value).attr('attributes'), 'full_name_product': full_name += ` (${$(value).attr('attributes')})`}
                } else {
                    product_attribute_ids[$(value).attr('id').split('id')[0]] = {'attributes': $(value).attr('attributes'), 'full_name_product': full_name}
                }
            });
            _.each(checked_un_req_dom, function(value) {
                let full_name = self.pos.db.get_product_by_id(Number($(value).attr('id').split('id')[0])).display_name;
                if($(value).attr('attributes')) {
                    product_attribute_ids[$(value).attr('id').split('id')[0]] = {'attributes': $(value).attr('attributes'), 'full_name_product': full_name += ` (${$(value).attr('attributes')})`}
                } else {
                    product_attribute_ids[$(value).attr('id').split('id')[0]] = {'attributes': $(value).attr('attributes'), 'full_name_product': full_name}
                }
            });
            product_attributes_values.push(product_attribute_ids);
            orderline.set_combo_product_attributes(product_attributes_values);
            orderline.set_require_product(_.map(product_ids_req, function(value){
                return Number(value.split('id')[0]);
            }));
            orderline.set_unrequire_product(_.map(product_ids_unreq, function(value){
                return Number(value.split('id')[0]);
            }));
            orderline.set_all_sub_product_selected_id(_.union(product_ids_req, product_ids_unreq));
            orderline.set_select_combo_id(
                _.uniq(_.union(_.map(product_ids_req, function(value){return Number(value.split('id')[1])}),
                    _.map(product_ids_unreq, function(value){return Number(value.split('id')[1])})
                )));
        }
        get_product_data(category, product_temp_id) {
            // Filter combo product data as a category wise
            let self = this;
            let result = {};
            let result_required = {};
            let result_unrequired = {};
            _.each(self.pos.combo_products_by_id, function(value) {
                if(!_.isEmpty(value.product_template_id) && category && value.product_template_id[0] === product_temp_id && category == value.category_id[0]) {
                    if (value.is_required_product) {
                        result_required = {
                            'no_of_items': value.no_of_items,
                            'is_require': value.is_required_product,
                            'req_products_ids': value.product_ids,
                            'combo_id': value.id,
                        }
                    }
                    else {
                        result_unrequired = {
                            'no_of_items': value.no_of_items,
                            'is_require': value.is_required_product,
                            'unreq_products_ids': value.product_ids,
                            'combo_id': value.id,
                        }
                    }
                }
                result = {
                    'id': category,
                    'req_product': result_required,
                    'unreq_product': result_unrequired,
                    'category_id': self.pos.db.get_category_by_id(category),
                }
            });

            return result;
        }
        set_pricelist(pricelist) {
            let self = this;
            this.pricelist = pricelist;
            let lines_to_recompute = _.filter(this.get_orderlines(), function (line) {
                if (line.is_combo_line === true) {
                    return !line.price_manually_set || line.is_combo_line;
                }
                return !line.price_manually_set;
            });
            _.each(lines_to_recompute, function (line) {
                if (line && line.is_combo_line) {
                    let combo_price = line.get_combo_price();
                    line.set_unit_price(combo_price.full_combo_price);
                } else {
                    line.set_unit_price(line.product.get_price(self.pricelist, line.get_quantity()));
                    self.fix_tax_included_price(line);
                }
            });
        }
    }
    Registries.Model.extend(Order,PosRestaurantComboOrder);

    const PosRestaurantcomboOrderline = (Orderline) => class PosRestaurantcomboOrderline extends Orderline {
        constructor() {
            super(...arguments);
            this.unreq_product = this.unreq_product || [];
            this.select_combo_id = this.select_combo_id || [];
            this.req_product = this.req_product || [];
            this.extra_price = this.extra_price || 0.0;
            this.edit_product = this.edit_product || [];
            this.all_selected_product_id = this.all_selected_product_id || [];
            this.qty = this.get_quantity();
            this.is_combo_line = this.is_combo_line || false;
            this.final_combo_price = this.final_combo_price || 0.0;
            this.combo_product_attribute_values = this.combo_product_attribute_values || [];
            this.sub_product_line = this.sub_product_line || false;
            this.unreq_product_without_draft = this.unreq_product_without_draft || [];
            this.req_product_ids_without_draft = this.req_product_ids_without_draft || [];
        }
        set_combo_product_attributes(product_configurator) {
            this.combo_product_attribute_values = product_configurator;
        }
        get_combo_product_attributes() {
            return this.combo_product_attribute_values;
        }
        set_unrequire_product(unreq_product) {
            this.unreq_product = unreq_product;
            this.unreq_product_without_draft = unreq_product;
            this.is_combo_line = true;
        }
        get_unrequire_product() {
            return this.unreq_product;
        }
        set_final_combo_price(final_combo_price) {
            this.final_combo_price = final_combo_price;
        }
        get_final_combo_price() {
            return this.final_combo_price;
        }
        set_extra_price_combo(extra_price) {
            this.extra_price = extra_price;
            this.get_combo_price();
        }
        get_extra_price_combo() {
            return this.extra_price;
        }
        set_all_sub_product_selected_id(all_selected_product_id) {
            this.all_selected_product_id = all_selected_product_id;
        }
        get_all_sub_product_selected_id() {
            return this.all_selected_product_id;
        }
        get_combo_price() {
            let self = this;
            let list_product_price = [];
            let combo_amount_dict = {};
            if (this.is_combo_line) {
                _.each(_.map(this.get_unrequire_product(), function(id){return self.pos.db.get_product_by_id(id)}), function(value){
                    list_product_price.push(value.get_price(self.order.pricelist, self.get_quantity()))
                })
                let combo_data = _.map(self.select_combo_id, function(id){return self.pos.combo_products_by_id[id]});
                _.each(combo_data, function(comboData){
                    if(comboData && comboData.is_required_product && !comboData.is_include_in_main_product_price) {
                        let req_product_ids = _.intersection(comboData.product_ids, self.get_require_product());
                        if(!_.isEmpty(req_product_ids)) {
                            _.each(req_product_ids, function(product_id){
                                list_product_price.push(self.pos.db.get_product_by_id(product_id).get_price(self.order.pricelist, self.get_quantity()));
                            });
                        }
                    }
                });
                let combo_price = _.reduce(list_product_price, function(price, number) {
                    return price + number;
                }, 0);
                let total_price = self.qty * combo_price;
                let product_price = self.product.get_price(self.order.pricelist, self.get_quantity());
                let final_price = product_price * this.qty + total_price;
                combo_amount_dict = {
                    'total_additional_amount': total_price,
                    'main_product_price': product_price,
                    'full_combo_price': final_price,
                }
                self.set_final_combo_price(final_price);
                return combo_amount_dict;
            }
        }
        set_require_product(req_product) {
            this.req_product = req_product;
            this.req_product_ids_without_draft = req_product;
            this.is_combo_line = true;
        }
        get_require_product() {
            return this.req_product;
        }
        set_select_combo_id(select_combo_id) {
            this.select_combo_id = select_combo_id;
        }
        get_select_combo_id() {
            return this.select_combo_id;
        }
        can_be_merged_with(orderline){
            if (this.is_combo_line) {
                return false;
            } else {
                return (!this.mp_skip) && (!orderline.mp_skip) && super.can_be_merged_with(...arguments);
            }
        }
        set_edit_combo_id(edit_product){
            this.edit_product = edit_product;
        }
        get_edit_combo_id(edit_product){
            return this.edit_product;
        }
        get_line_diff_hash(){
            if(this.is_combo_line){
                return this.id + '|' + _.map(this.unreq_product, 'id') + '|' + _.map(this.req_product, 'id');
            } else {
                return '' + this.id;
            }
        }
        clone(){
            const orderline = super.clone(...arguments);
            orderline.req_product = this.req_product;
            return orderline;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            let self = this;
            if (self.pos.config.module_pos_restaurant && json.is_combo_line) {
                var unreq_ids = [];
                var req_ids = [];
                this.req_product_ids_without_draft = json.req_product_ids_without_draft;
                this.unreq_product_without_draft = json.unreq_product_without_draft;
                if (!_.isEmpty(this.req_product_ids_without_draft)) {
                    this.req_product = this.req_product_ids_without_draft;
                } else {
                    _.each(json.req_product_ids, function(product_id) {
                        if(!_.isUndefined(product_id)){
                            var req_product = self.pos.db.get_product_by_id(Number(product_id));
                            req_ids.push(product_id);
                        }
                    });
                    this.req_product = req_ids;
                }
                if (!_.isEmpty(this.unreq_product_without_draft)) {
                    this.unreq_product = this.unreq_product_without_draft;
                } else {
                    _.each(json.unreq_product_ids, function(product_id) {
                        var unreq_product = self.pos.db.get_product_by_id(Number(product_id));
                        unreq_ids.push(product_id);
                    });
                    this.unreq_product = unreq_ids;
                }
                this.is_combo_line = json.is_combo_line;
                this.select_combo_id = json.select_combo_id;
                this.extra_price = json.extra_price || 0.0;
                this.price_manually_set = json.is_combo_line && true || false;
                this.edit_product = json.edit_combo_id || [];
                this.all_selected_product_id = json.all_selected_product_id || [];
                this.combo_product_attribute_values = json.combo_product_attribute_values || [];
                this.final_combo_price = json.final_combo_price || 0.0;
                if (this.is_combo_line) {
                    this.set_unit_price(this.final_combo_price);
                }
            } else {
                this.unreq_product = json.unreq_product_ids;
                this.is_combo_line = json.is_combo_line;
                this.select_combo_id = json.select_combo_id;
                this.req_product = json.req_product_ids;
                this.extra_price = json.extra_price || 0.0;
                this.price_manually_set = json.is_combo_line && true || false;
                this.all_selected_product_id = json.all_selected_product_id || [];
                this.combo_product_attribute_values = json.combo_product_attribute_values || [];
            }
        }
        export_as_JSON() {
            var self = this;
            let json = super.export_as_JSON(...arguments);
            if (self.pos.config.module_pos_restaurant && this.is_combo_line) {
                json.req_product = this.req_product || false;
                var req_ids = [];
                var unreq_ids = [];
                if (!_.isEmpty(this.req_product_ids_without_draft)) {
                    json.req_product_ids = this.req_product_ids_without_draft;
                } else {
                    _.each(this.req_product, function(product_id) {
                        if(!_.isUndefined(product_id)){
                            var req_product = self.pos.db.get_product_by_id(Number(product_id));
                            req_ids.push(req_product.id);
                        }
                    });
                    json.req_product_ids = req_ids;
                }
                if (!_.isEmpty(this.unreq_product_without_draft)) {
                    json.unreq_product_ids = this.unreq_product_without_draft;
                } else {
                    _.each(this.unreq_product, function(product_id) {
                        if(!_.isUndefined(product_id)){
                            var unreq_product = self.pos.db.get_product_by_id(Number(product_id));
                            unreq_ids.push(unreq_product.id);
                        }
                    });
                    json.unreq_product_ids = unreq_ids;
                }
                json.is_combo_line = this.is_combo_line;
                json.select_combo_id = _.uniq(this.select_combo_id) || false;
                json.edit_combo_id = this.get_edit_combo_id() || false;
                json.extra_price = this.extra_price || 0.0;
                json.all_selected_product_id = this.all_selected_product_id || [];
                json.final_combo_price = this.final_combo_price || 0.0;
                json.combo_product_attribute_values = this.combo_product_attribute_values || []
            } else {
                json.req_product = this.req_product || false;
                json.unreq_product_ids = this.unreq_product || false;
                json.req_product_ids = this.req_product || false;
                json.is_combo_line = this.is_combo_line;
                json.select_combo_id = this.select_combo_id || false;
                json.extra_price = this.extra_price || 0.0;
                json.all_selected_product_id = this.all_selected_product_id || [];
                json.combo_product_attribute_values = this.combo_product_attribute_values || []
            }
            return json;
        }

        export_for_printing() {
            var receipt = super.export_for_printing(...arguments);
           let self = this;
            receipt.req_product = this.get_require_product()
            receipt.unreq_product = this.get_unrequire_product()
            receipt.req_product = _.map(this.get_require_product(), function(id){return self.pos.db.get_product_by_id(id)});
            receipt.unreq_product = _.map(this.get_unrequire_product(), function(id){return self.pos.db.get_product_by_id(id)});
            receipt.is_combo_line = this.is_combo_line;
            receipt.combo_price = this.get_combo_price();
            receipt.select_combo_id = this.get_select_combo_id();
            receipt.combo_product_attribute_values = this.get_combo_product_attributes();
            return receipt;
        }
    }
    Registries.Model.extend(Orderline, PosRestaurantcomboOrderline);
});
