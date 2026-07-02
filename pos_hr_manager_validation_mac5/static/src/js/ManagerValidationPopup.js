odoo.define('pos_hr_manager_validation_mac5.ManagerValidationPopup', function(require) {
'use strict';

var core = require('web.core');
var _t = core._t;

const NumberPopup = require('point_of_sale.NumberPopup');
const Registries = require('point_of_sale.Registries');


class ManagerValidationPopup extends NumberPopup {}
ManagerValidationPopup.template = 'NumberPopup';
ManagerValidationPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Manager Validation'),
    body: '',
    cheap: false,
    startingValue: null,
    isPassword: true,
};


Registries.Component.add(ManagerValidationPopup);

return ManagerValidationPopup;

});
