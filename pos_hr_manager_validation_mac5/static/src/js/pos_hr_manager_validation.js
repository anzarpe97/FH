odoo.define('pos_hr_manager_validation.pos_hr_manager_validation', function (require) {
"use strict";

const HeaderButton = require('point_of_sale.HeaderButton');
const NumberBuffer = require('point_of_sale.NumberBuffer');
const NumpadWidget = require('point_of_sale.NumpadWidget');
const ProductScreen = require('point_of_sale.ProductScreen');
const Registries = require('point_of_sale.Registries');
const TicketScreen = require('point_of_sale.TicketScreen');


const PosEmpValidHeaderButton = (HeaderButton) =>
    class extends HeaderButton {
        onClick() {
            if (this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_close) {
                var managerEmployeeIDs = this.env.pos.config.manager_employee_ids;
                var cashier = this.env.pos.get_cashier();
                if( cashier && managerEmployeeIDs.indexOf(cashier.id) > -1 ){
                    return super.onClick();
                }

                this.showPopup('ManagerValidationPopup').then(({ confirmed, payload }) => {
                    var password = payload ? payload.toString() : ''

                    if (confirmed) {
                        this.env.pos.managerEmployee = false;
                        var employees = this.env.pos.employees;
                        for (var i = 0; i < employees.length; i++) {
                            if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].pin
                                    && Sha1.hash(password) === employees[i].pin) {
                                this.env.pos.managerEmployee = employees[i];
                            } else if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].barcode
                                    && Sha1.hash(password) === employees[i].barcode) {
                                this.env.pos.managerEmployee = employees[i];
                            }
                        }
                        if (this.env.pos.managerEmployee) {
                            super.onClick();
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Access Denied'),
                                body: this.env._t('Incorrect password!'),
                            });
                        }
                    }
                });
            } else {
                super.onClick();
            }
        }
    };


const PosEmpValidNumpadWidget = (NumpadWidget) =>
    class extends NumpadWidget {
        changeMode(mode) {
            if ((mode === 'discount' && this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_discount)
                    || (mode === 'price' && this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_price)) {
                var managerEmployeeIDs = this.env.pos.config.manager_employee_ids;
                var cashier = this.env.pos.get_cashier();
                if( cashier && managerEmployeeIDs.indexOf(cashier.id) > -1 ){
                    return super.changeMode(mode);
                }

                this.showPopup('ManagerValidationPopup').then(({ confirmed, payload }) => {
                    var password = payload ? payload.toString() : ''

                    if (confirmed) {
                        this.env.pos.managerEmployee = false;
                        var employees = this.env.pos.employees;
                        for (var i = 0; i < employees.length; i++) {
                            if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].pin
                                    && Sha1.hash(password) === employees[i].pin) {
                                this.env.pos.managerEmployee = employees[i];
                            } else if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].barcode
                                    && Sha1.hash(password) === employees[i].barcode) {
                                this.env.pos.managerEmployee = employees[i];
                            }
                        }
                        if (this.env.pos.managerEmployee) {
                            super.changeMode(mode);
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Access Denied'),
                                body: this.env._t('Incorrect password!'),
                            });
                        }
                    }
                });
            } else {
                super.changeMode(mode);
            }
        }
    };


const PosEmpValidProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        _setValue(val) {
            var newQty = NumberBuffer.get() ? parseFloat(NumberBuffer.get()) : 0;
            var orderLines = this.currentOrder.get_orderlines();
            if (orderLines !== undefined && orderLines.length > 0) {
                var currentOrderLine = this.currentOrder.get_selected_orderline();
                var currentQty = this.currentOrder.get_selected_orderline().get_quantity();
                if (currentOrderLine && this.env.pos.numpadMode === 'quantity'
                        && ((newQty < currentQty && this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_decrease_quantity)
                            || (val === 'remove' && this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_delete_orderline))) {
                    var managerEmployeeIDs = this.env.pos.config.manager_employee_ids;
                    var cashier = this.env.pos.get_cashier();
                    if( cashier && managerEmployeeIDs.indexOf(cashier.id) > -1 ){
                        return super._setValue(val);
                    }

                    this.showPopup('ManagerValidationPopup').then(({ confirmed, payload }) => {
                        var password = payload ? payload.toString() : ''

                        if (confirmed) {
                            this.env.pos.managerEmployee = false;
                            var employees = this.env.pos.employees;
                            for (var i = 0; i < employees.length; i++) {
                                if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                        && !!employees[i].pin
                                        && Sha1.hash(password) === employees[i].pin) {
                                    this.env.pos.managerEmployee = employees[i];
                                } else if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                        && !!employees[i].barcode
                                        && Sha1.hash(password) === employees[i].barcode) {
                                    this.env.pos.managerEmployee = employees[i];
                                }
                            }
                            if (this.env.pos.managerEmployee) {
                                super._setValue(val);
                            } else {
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t('Access Denied'),
                                    body: this.env._t('Incorrect password!'),
                                });
                            }
                        }
                    });
                } else {
                    super._setValue(val);
                }
            } else {
                super._setValue(val)
            }
        }

        _onClickPay() {
            if (this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_payment) {
                var managerEmployeeIDs = this.env.pos.config.manager_employee_ids;
                var cashier = this.env.pos.get_cashier();
                if( cashier && managerEmployeeIDs.indexOf(cashier.id) > -1 ){
                    return super._onClickPay();
                }

                this.showPopup('ManagerValidationPopup').then(({ confirmed, payload }) => {
                    var password = payload ? payload.toString() : ''

                    if (confirmed) {
                        this.env.pos.managerEmployee = false;
                        var employees = this.env.pos.employees;
                        for (var i = 0; i < employees.length; i++) {
                            if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].pin
                                    && Sha1.hash(password) === employees[i].pin) {
                                this.env.pos.managerEmployee = employees[i];
                            } else if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                    && !!employees[i].barcode
                                    && Sha1.hash(password) === employees[i].barcode) {
                                this.env.pos.managerEmployee = employees[i];
                            }
                        }
                        if (this.env.pos.managerEmployee) {
                            super._onClickPay();
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Access Denied'),
                                body: this.env._t('Incorrect password!'),
                            });
                        }
                    }
                });
            } else {
                super._onClickPay();
            }
        }

    };


const PosEmpValidTicketScreen = (TicketScreen) =>
    class extends TicketScreen {
        async _onDeleteOrder({ detail: order }) {
            if (this.env.pos.config.module_pos_hr && this.env.pos.config.iface_employee_validate_delete_order) {
                var managerEmployeeIDs = this.env.pos.config.manager_employee_ids;
                var cashier = this.env.pos.get_cashier();
                if( cashier && managerEmployeeIDs.indexOf(cashier.id) > -1 ){
                    return await super._onDeleteOrder({ detail: order });
                }

                const { confirmed, payload } = await this.showPopup('ManagerValidationPopup');
                var password = payload ? payload.toString() : ''

                if (confirmed) {
                    this.env.pos.managerEmployee = false;
                    var employees = this.env.pos.employees;
                    for (var i = 0; i < employees.length; i++) {
                        if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                && !!employees[i].pin
                                && Sha1.hash(password) === employees[i].pin) {
                            this.env.pos.managerEmployee = employees[i];
                        } else if (managerEmployeeIDs.indexOf(employees[i].id) > -1
                                && !!employees[i].barcode
                                && Sha1.hash(password) === employees[i].barcode) {
                            this.env.pos.managerEmployee = employees[i];
                        }
                    }
                    if (this.env.pos.managerEmployee) {
                        await super._onDeleteOrder({ detail: order });
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Access Denied'),
                            body: this.env._t('Incorrect password!'),
                        });
                    }
                }
            } else {
                await super._onDeleteOrder({ detail: order });
            }
        }
    };


Registries.Component.extend(HeaderButton, PosEmpValidHeaderButton);
Registries.Component.extend(NumpadWidget, PosEmpValidNumpadWidget);
Registries.Component.extend(ProductScreen, PosEmpValidProductScreen);
Registries.Component.extend(TicketScreen, PosEmpValidTicketScreen);


});
