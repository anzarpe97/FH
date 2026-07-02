odoo.define('customer_validation_pos.PartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');

    const PosNewCustomerValidation = (PartnerListScreen) =>
        class extends PartnerListScreen {
            async saveChanges(event) {
                var name_list = [];
                var vat_list = [];
                var phone_list = [];
                var street_list = [];
                var email_list = [];

                var partners = this.env.pos.db.get_partners_sorted()
                var fields = event.detail.processedChanges
                for (var i = 0; i < partners.length; i++) {
                    if (partners[i].phone) {
                        name_list.push(partners[i].name);
                        vat_list.push(partners[i].vat);
                        phone_list.push(partners[i].phone);
                        street_list.push(partners[i].street);
                        email_list.push(partners[i].email);
                    }
                }
                if (this.env.pos.config.required_name && ((fields.id === false && !fields.name) || (fields.id && fields.name === ""))) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡Se requiere el nombre del cliente!'),
                    });
                }
                // Validar que el campo name solo contenga letras y numeros
                if (fields.name && !/^[\w\sñáéíóúÁÉÍÓÚüÜ]+$/.test(fields.name)) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡El nombre del cliente debe contener solo letras y números!'),
                    });
                }
                if (this.env.pos.config.unique_name && fields.name && name_list.indexOf(fields.name) > -1) {
                    return this.showPopup('ErrorPopup', {
                        title: _('El nombre '+fields.name+' ya existe!'),
                    });
                }
                if (this.env.pos.config.required_vat && ((fields.id === false && !fields.vat) || (fields.id && fields.vat === ""))) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡Se requiere C.I / R.I.F del cliente!'),
                    });
                }
                if (this.env.pos.config.unique_vat && fields.vat && vat_list.indexOf(fields.vat) > -1) {
                    // Muestra una alerta de duplicado
                    const confirmation = await this.showPopup('ConfirmPopup', {
                        title: _('¿Desea aplicar la actualización de los datos del cliente?'),
                        confirmText: _('Actualizar'),
                        cancelText: _('Cancelar'),
                    });
                
                    // Verifica la respuesta del usuario
                    if (!confirmation) {
                        // El usuario canceló la actualización, puedes salir de la función o realizar alguna otra acción.
                        return;
                    }
                }
                
                // Si llegamos aquí, significa que el usuario confirmó la actualización o no hay duplicados
                // Continúa con la lógica de actualización de datos aquí
                // ...
                if (this.env.pos.config.required_phone && ((fields.id === false && !fields.phone) || (fields.id && fields.phone === ""))) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡Se requiere el número de teléfono del cliente!'),
                    });
                }
                // Validar que el campo phone solo contenga números
                if (fields.phone && !/^[0-9]+$/.test(fields.phone)) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡El número de teléfono del cliente debe contener solo números!'),
                    });
                }
                if (this.env.pos.config.unique_phone && fields.phone && phone_list.indexOf(fields.phone) > -1) {
                    return this.showPopup('ErrorPopup', {
                        title: _('El telefono '+fields.phone+' ya existe!'),
                    });
                }
                if (this.env.pos.config.required_street && ((fields.id === false && !fields.street) || (fields.id && fields.street === ""))) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡Se requiere la dirección del cliente!'),
                    });
                }
                if (this.env.pos.config.unique_street && fields.street && street_list.indexOf(fields.street) > -1) {
                    return this.showPopup('ErrorPopup', {
                        title: _('La direccion '+fields.street+' ya existe!'),
                    });
                }
                if (this.env.pos.config.required_email && ((fields.id === false && !fields.email) || (fields.id && fields.email === ""))) {
                    return this.showPopup('ErrorPopup', {
                        title: _('¡Se requiere el correo del cliente!'),
                    });
                }
                if (this.env.pos.config.unique_email && fields.email && email_list.indexOf(fields.email) > -1) {
                    return this.showPopup('ErrorPopup', {
                        title: _('Correo '+fields.email+' ya existe!'),
                    });
                }
                super.saveChanges(...arguments);
            }
        };
    Registries.Component.extend(PartnerListScreen, PosNewCustomerValidation);
    return PosNewCustomerValidation;
});
